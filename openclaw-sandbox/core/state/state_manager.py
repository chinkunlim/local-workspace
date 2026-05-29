from datetime import datetime
import fcntl
import hashlib
import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

from rich import print

from core.state.state_backend import get_state_backend
from core.utils.atomic_writer import AtomicWriter

_logger = logging.getLogger("OpenClaw.StateManager")


class MemoryPool:
    """Global key-value store for cross-skill memory and user preferences (P4.1-1).

    Uses the StateBackend interface to persist data either locally in a
    `_global_` namespace or in a shared Redis instance.
    """

    def __init__(self, workspace_root: str, backend_cfg: Optional[Dict[str, Any]] = None):
        self.workspace_root = workspace_root
        backend_cfg = backend_cfg or {}
        # Default local persistence to data/_global_/state/
        base_dir = os.path.join(workspace_root, "data", "_global_", "state")
        self.backend = get_state_backend(backend_cfg, base_dir=base_dir)
        self._pool_key = "memory_pool"
        self._lock = threading.RLock()

        # Initialize if empty
        if not self.backend.exists(self._pool_key):
            self.backend.set(self._pool_key, {})

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a global user preference."""
        with self._lock:
            data = self.backend.get(self._pool_key) or {}
            return data.get("preferences", {}).get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        """Save a global user preference."""
        with self._lock:
            data = self.backend.get(self._pool_key) or {}
            if "preferences" not in data:
                data["preferences"] = {}
            data["preferences"][key] = value
            self.backend.set(self._pool_key, data)

    def get_memory(self, key: str) -> Optional[Any]:
        """Retrieve a raw global memory variable."""
        with self._lock:
            data = self.backend.get(self._pool_key) or {}
            return data.get(key)

    def set_memory(self, key: str, value: Any) -> None:
        """Save a raw global memory variable."""
        with self._lock:
            data = self.backend.get(self._pool_key) or {}
            data[key] = value
            self.backend.set(self._pool_key, data)


class StateManager:
    def __init__(
        self, base_dir: str, skill_name: str = "audio_transcriber", raw_dir: str | None = None
    ):
        self.base_dir = base_dir
        self.skill_name = skill_name
        self.file_ext: str | tuple[str, ...] = "*.md"
        self.PHASES: List[str] = ["p1"]
        self._phase_labels: Dict[str, str] = {"p1": "P1 (處理)"}

        # Dynamically load configuration from SkillRegistry
        from core.orchestration.skill_registry import SkillRegistry

        registry = SkillRegistry()
        registry.discover()
        manifest = registry.get(skill_name)
        if manifest:
            self.PHASES = manifest.phases or ["p1"]
            self._phase_labels = manifest.phase_labels or {p: p.upper() for p in self.PHASES}

            # Map file extensions
            if len(manifest.file_types) == 1:
                self.file_ext = manifest.file_types[0]
            elif len(manifest.file_types) > 1:
                self.file_ext = tuple(manifest.file_types)
            else:
                self.file_ext = "*.md"
        canonical_state_dir = os.path.join(base_dir, "state")
        legacy_state_file = os.path.join(base_dir, ".pipeline_state.json")
        legacy_checklist_file = os.path.join(base_dir, "checklist.md")
        canonical_state_file = os.path.join(canonical_state_dir, ".pipeline_state.json")
        canonical_checklist_file = os.path.join(canonical_state_dir, "checklist.md")

        self.state_file = (
            canonical_state_file
            if os.path.exists(canonical_state_file) or not os.path.exists(legacy_state_file)
            else legacy_state_file
        )
        self.checklist_file = (
            canonical_checklist_file
            if os.path.exists(canonical_checklist_file) or not os.path.exists(legacy_checklist_file)
            else legacy_checklist_file
        )

        if raw_dir is not None:
            # Caller-supplied override (e.g. note_generator/smart_highlighter
            # read from proofreader output, not from their own input/ dir)
            self.raw_dir = raw_dir
        elif skill_name == "interactive_reader":
            # Interactive reader directly monitors and mutates the wiki
            self.raw_dir = os.path.abspath(os.path.join(base_dir, "..", "wiki"))
        else:
            self.raw_dir = os.path.join(base_dir, "input")

        self._lock = threading.RLock()
        self._checkpoint: Optional[Dict[str, Any]] = None
        self.state: Dict[str, Dict[str, Any]] = self._load_state()

        # If manifest was not found or has no explicit phases, try to infer them from existing state
        if not manifest or not getattr(manifest, "phases", None):
            inferred_phases = set()
            for subj, files in self.state.items():
                if isinstance(files, dict):
                    for fname, record in files.items():
                        if isinstance(record, dict):
                            for k in record:
                                if k.startswith("p") and k[1:].isdigit():
                                    inferred_phases.add(k)
            if inferred_phases:
                self.PHASES = sorted(inferred_phases)
                self._phase_labels = {p: f"{p.upper()} (處理)" for p in self.PHASES}

    @staticmethod
    def _dir_has_files(path: str) -> bool:
        try:
            if not os.path.isdir(path):
                return False
            with os.scandir(path) as entries:
                return any(entry.is_file() for entry in entries)
        except OSError:
            return False

    def _load_state(self) -> Dict[str, Dict[str, Any]]:
        """Load internal state from JSON with shared (read) file lock."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    fcntl.flock(f, fcntl.LOCK_SH)  # Shared read lock
                    try:
                        raw = json.load(f)
                    finally:
                        fcntl.flock(f, fcntl.LOCK_UN)
                if isinstance(raw, dict):
                    self._checkpoint = raw.get("_checkpoint")
                    if isinstance(raw.get("_state"), dict):
                        return raw.get("_state", {})
                    return {k: v for k, v in raw.items() if not str(k).startswith("_")}
            except json.JSONDecodeError as exc:
                _logger.error(
                    "狀態檔案 JSON 損毀，將以空狀態啟動 (%s): %s",
                    self.state_file,
                    exc,
                    exc_info=True,
                )
            except OSError as exc:
                _logger.error("無法讀取狀態檔案 (%s): %s", self.state_file, exc, exc_info=True)
            except Exception as exc:
                _logger.error(
                    "讀取狀態檔案時發生未預期錯誤 (%s): %s", self.state_file, exc, exc_info=True
                )
        return {}

    def _save_state(self):
        """Persist state to JSON with exclusive write lock, then re-render checklist."""
        with self._lock:
            payload = self._serialize_state()
            # Acquire an exclusive process-level lock before writing
            lock_path = self.state_file + ".lock"
            os.makedirs(os.path.dirname(lock_path), exist_ok=True)
            with open(lock_path, "w") as lock_fd:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)  # Exclusive write lock
                try:
                    AtomicWriter.write_json(self.state_file, payload)
                finally:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
        self._render_checklist()

    def _serialize_state(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {subject: files for subject, files in self.state.items()}
        if self._checkpoint:
            payload["_checkpoint"] = self._checkpoint
        return payload

    def get_file_hash(self, filepath: str) -> str:
        """Return SHA-256 hash of a file."""
        if not os.path.exists(filepath):
            return ""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.hexdigest()

    def sync_physical_files(self):
        """Scans raw_data/ for .m4a files and updates internal state."""
        with self._lock:
            if not os.path.exists(self.raw_dir):
                return

            if self.skill_name == "interactive_reader":
                # Flat directory in data/wiki
                subjects_dirs = [("Wiki", self.raw_dir)]
            else:
                subjects_dirs = [
                    (d, os.path.join(self.raw_dir, d))
                    for d in os.listdir(self.raw_dir)
                    if os.path.isdir(os.path.join(self.raw_dir, d))
                ]

            for subj, subj_path in subjects_dirs:
                if subj not in self.state:
                    self.state[subj] = {}

                import glob

                physical_files = []
                if isinstance(self.file_ext, (tuple, list)):
                    for ext in self.file_ext:
                        glob_ext = f"*{ext}" if ext.startswith(".") else ext
                        physical_files.extend(glob.glob(os.path.join(subj_path, glob_ext)))
                else:
                    glob_ext = (
                        f"*{self.file_ext}" if self.file_ext.startswith(".") else self.file_ext
                    )
                    physical_files = glob.glob(os.path.join(subj_path, glob_ext))

                for pf in physical_files:
                    fname = os.path.basename(pf)
                    if fname == "correction_log.md":
                        continue
                    fhash = self.get_file_hash(pf)
                    mtime = datetime.fromtimestamp(os.path.getmtime(pf)).strftime("%Y-%m-%d")

                    if fname not in self.state[subj]:
                        self.state[subj][fname] = {
                            **dict.fromkeys(self.PHASES, "⏳"),
                            "hash": fhash,
                            "date": mtime,
                            "note": "更新/新增",
                            "output_hashes": {},
                            "char_count": {},
                        }
                    else:
                        # If raw audio changed, negate everything
                        if self.state[subj][fname].get("hash") != fhash:
                            self.state[subj][fname].update(
                                {
                                    **dict.fromkeys(self.PHASES, "⏳"),
                                    "hash": fhash,
                                    "date": mtime,
                                    "note": "原始檔已變更",
                                }
                            )
            self._save_state()

    def cascade_invalidate(self, subject: str, filename: str, changed_phase: str):
        """Invalidate dependent phases. E.g. if p1 output changes, p2-p5 become ⏳."""
        with self._lock:
            if subject not in self.state or filename not in self.state[subject]:
                return

            idx = self.PHASES.index(changed_phase)
            record = self.state[subject][filename]

            # All subsequent phases are invalidated
            invalidated_any = False
            for p in self.PHASES[idx + 1 :]:
                if record.get(p) == "✅":
                    record[p] = "⏳"
                    invalidated_any = True

            if invalidated_any:
                record["note"] = f"{changed_phase.upper()} 被手動修改 (DAG 重啟)"
                self._save_state()

    def update_task(
        self,
        subject: str,
        filename: str,
        phase_key: str,
        status: str = "✅",
        char_count: int = None,
        output_hash: str = None,
        note_tag: str = None,
        lang: str = None,
    ):
        with self._lock:
            if subject not in self.state or filename not in self.state[subject]:
                return

            record = self.state[subject][filename]
            record[phase_key] = status

            if char_count is not None:
                record.setdefault("char_count", {})[phase_key] = char_count

            if output_hash is not None:
                record.setdefault("output_hashes", {})[phase_key] = output_hash

            if note_tag is not None:
                record["note"] = note_tag

            if lang is not None:
                record["lang"] = lang

            self._save_state()

    def is_completed(self, phase_key: str, state_key: str) -> bool:
        """Convenience method for skills that use a simple phase/key model.

        Checks whether the given state_key has been marked complete under
        a flat '_simple_' namespace.  Used by skills like feynman_simulator
        that do not have subject/filename triplets.
        """
        with self._lock:
            return self.state.get("_simple_", {}).get(state_key, {}).get(phase_key) == "✅"

    def mark_completed(self, phase_key: str, state_key: str) -> None:
        """Convenience method: mark a simple phase/key pair as completed.

        Mirrors is_completed() for skills that use a flat tracking model.
        """
        with self._lock:
            self.state.setdefault("_simple_", {}).setdefault(state_key, {})[phase_key] = "✅"
            self._save_state()

    def check_output_hashes(self, phase_dirs: Dict[str, str]):
        """
        Check if physical outputs of completed phases have been manually edited.
        phase_dirs is a dict mapping phase_key like 'p1' to its base directory path.
        """
        with self._lock:
            changed = False
            for subj, files in self.state.items():
                for fname, record in files.items():
                    for i, p in enumerate(self.PHASES):
                        if record.get(p) == "✅":
                            expected_hash = record.get("output_hashes", {}).get(p)
                            if not expected_hash:
                                continue

                            target_dir = phase_dirs.get(p)
                            if not target_dir:
                                continue

                            base_name = os.path.splitext(fname)[0]
                            out_path = os.path.join(target_dir, subj, f"{base_name}.md")
                            current_hash = self.get_file_hash(out_path)

                            if current_hash and current_hash != expected_hash:
                                self.cascade_invalidate(subj, fname, p)
                                # Update to the new human-edited hash so it stops invalidating
                                record.setdefault("output_hashes", {})[p] = current_hash
                                changed = True
            if changed:
                self._save_state()

    # ------------------------------------------------------------------ #
    #  Dashboard 儀表板                                                    #
    # ------------------------------------------------------------------ #

    def get_dashboard_text(self) -> Optional[str]:
        """根據當前狀態與 Phase 定義，產生對齊的進度追蹤儀表板字串。"""
        with self._lock:
            counters = {p: {"done": 0, "total": 0} for p in self.PHASES}
            for subj_data in self.state.values():
                for _fname, record in subj_data.items():
                    for key in counters:
                        val = record.get(key)
                        if val == "⏭️":
                            continue
                        counters[key]["total"] += 1
                        if val == "✅":
                            counters[key]["done"] += 1

        # Check if there are any pending tasks
        has_pending = False
        for p in self.PHASES:
            if counters[p]["total"] > 0 and counters[p]["done"] < counters[p]["total"]:
                has_pending = True
                break

        if not has_pending:
            return None

        lines = []
        skill_display = {
            "audio_transcriber": "[Inbox Daemon 排程] 語音轉錄",
            "doc_parser": "[Inbox Daemon 排程] 文件解析",
            "academic_edu_assistant": "學術教育助手",
            "inbox_manager": "收件匣管理",
            "interactive_reader": "互動式閱讀",
            "knowledge_compiler": "知識編譯",
            "note_generator": "筆記生成",
            "smart_highlighter": "智能高亮",
            "telegram_kb_agent": "Telegram 知識庫代理",
            "proofreader": "Proofreader",
        }.get(self.skill_name, f"{self.skill_name}")

        lines.append(f"🔹 **{skill_display}**")

        for p in self.PHASES:
            label = self._phase_labels.get(p, p.upper())
            done = counters[p]["done"]
            total = counters[p]["total"]
            if total == 0:
                continue
            if done == total:
                icon = "✅"
            elif done > 0:
                icon = "⏳"
            else:
                icon = "❌"
            lines.append(f"   ├─ [{label}]: {icon} {done}/{total}")
        lines.append("")
        return "\n".join(lines)

    def print_dashboard(self):
        """直接在終端機印出儀表板。"""
        text = self.get_dashboard_text()
        if text:
            print("\n" + text)

    # ------------------------------------------------------------------ #
    #  Checkpoint 管理 — 斷點續傳                                          #
    # ------------------------------------------------------------------ #

    def save_checkpoint(self, subject: str, filename: str, phase_key: str):
        """
        將暫停位置寫入 state file 的 _checkpoint 欄位。
        記錄下一個「尚未完成」的任務起點，而非剛完成的那個，
        讓 resume 時能直接從這裡繼續，避免重跑已完成項目。
        """
        with self._lock:
            self._checkpoint = {
                "subject": subject,
                "filename": filename,
                "phase_key": phase_key,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._save_state()

    def load_checkpoint(self) -> Optional[Dict[str, str]]:
        """
        從 state file 讀取 checkpoint。
        若不存在，回傳 None；存在則回傳 {subject, filename, phase_key, saved_at}。
        """
        with self._lock:
            if self._checkpoint is not None:
                return self._checkpoint
            if not os.path.exists(self.state_file):
                return None
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    raw = json.load(f)
                self._checkpoint = raw.get("_checkpoint", None)
                return self._checkpoint
            except Exception:
                return None

    def clear_checkpoint(self):
        """清除 checkpoint（正常完成或使用者選擇全新開始時呼叫）。"""
        with self._lock:
            self._checkpoint = None
            self._save_state()

    def clear_progress(self) -> None:
        """清除所有任務的進度記錄，將所有 phase 重設為 ⏳，並清除 checkpoint 和備注。

        --clear CLI 旗標的後端實作。呼叫後：
        - 所有任務的 phase 狀態恢復為 ⏳
        - output_hashes 和 char_count 清空
        - note 清空
        - checkpoint 清除
        - checklist.md 重新渲染
        """
        with self._lock:
            for subj in self.state:
                for fname, record in self.state[subj].items():
                    # Reset all phase keys
                    for phase in self.PHASES:
                        if phase in record:
                            record[phase] = "⏳"
                    # Clear auxiliary tracking fields
                    record.pop("output_hashes", None)
                    record.pop("char_count", None)
                    record.pop("note", None)
            self._checkpoint = None
            self._save_state()

    # ------------------------------------------------------------------ #
    #  Granular Chunk-Level Checkpointing (#6)                            #
    # ------------------------------------------------------------------ #

    def save_chunk_checkpoint(
        self,
        subject: str,
        filename: str,
        phase_key: str,
        chunk_index: int,
        partial_output: Optional[str] = None,
    ) -> None:
        """Persist a chunk-level mid-file checkpoint for precise mid-phase resumption.

        Extends the standard file-level _checkpoint with a chunk_index so that
        a long proofreading or compilation job interrupted mid-file can resume
        from the exact chunk, not from the start of the file.

        Args:
            subject:        Subject/directory name (e.g. "math").
            filename:       Source filename (e.g. "lecture-01.m4a").
            phase_key:      The phase being checkpointed (e.g. "p2").
            chunk_index:    0-based index of the last *completed* chunk.
            partial_output: Optional serialised partial output written so far
                            (stored as a plain string; Phase scripts should
                            use AtomicWriter to persist the actual file).
        """
        with self._lock:
            self._checkpoint = {
                "subject": subject,
                "filename": filename,
                "phase_key": phase_key,
                "chunk_index": chunk_index,
                "partial_output_len": len(partial_output) if partial_output else 0,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "granularity": "chunk",
            }
            self._save_state()

    def load_chunk_checkpoint(self, subject: str, filename: str, phase_key: str) -> Optional[int]:
        """Load the last saved chunk index for a specific file+phase combination.

        Returns the 0-based index of the last completed chunk so the caller
        can skip `chunks[:chunk_index+1]` and resume from `chunk_index+1`.

        Returns:
            int  — last completed chunk index (resume from chunk_index + 1).
            None — no chunk checkpoint exists for this file (start from 0).
        """
        with self._lock:
            cp = self._checkpoint
            if cp is None:
                return None
            if (
                cp.get("granularity") == "chunk"
                and cp.get("subject") == subject
                and cp.get("filename") == filename
                and cp.get("phase_key") == phase_key
            ):
                return cp.get("chunk_index")
            return None

    def clear_chunk_checkpoint(self, subject: str, filename: str, phase_key: str) -> None:
        """Clear the chunk checkpoint for a file once processing completes normally.

        Leaves file-level checkpoints intact if they exist for a different file.
        """
        with self._lock:
            cp = self._checkpoint
            if (
                cp is not None
                and cp.get("granularity") == "chunk"
                and cp.get("subject") == subject
                and cp.get("filename") == filename
                and cp.get("phase_key") == phase_key
            ):
                self._checkpoint = None
                self._save_state()

    def _render_checklist(self) -> None:
        """Render read-only checklist.md — supports any skill's phase set."""
        phase_keys = self.PHASES
        phase_labels = self._phase_labels

        # audio_transcriber 額外顯示語言欄位
        show_lang = self.skill_name == "audio_transcriber"

        header_cols = " | ".join(phase_labels.get(p, p.upper()) for p in phase_keys)
        sep_cols = " | ".join(":---:" for _ in phase_keys)

        if show_lang:
            header_cols += " | 語言"
            sep_cols += " | :---:"

        lines: List[str] = []
        skill_display = {
            "audio_transcriber": "學習進度",
            "doc_parser": "知識庫處理進度",
            "knowledge_compiler": "知識庫編譯進度",
            "interactive_reader": "互動閱讀處理進度",
            "telegram_kb_agent": "行動知識庫進度",
            "academic_edu_assistant": "學術助手進度",
        }.get(self.skill_name, "進度")

        lines.append(f"# {skill_display} (總表)\n")
        lines.append("> 🚨 本檔案由系統 `.pipeline_state.json` 自動映射生成，請勿手動修改。")
        lines.append("> 更改輸出目錄下的 `.md` 檔案將被系統偵測並觸發自動重新運算 (DAG Cascade).\n")

        for subj in sorted(self.state.keys()):
            lines.append(f"## {subj}\n")
            lines.append(f"| 檔案/ID | {header_cols} | 狀態備註 |")
            lines.append(f"| :--- | {sep_cols} | :--- |")

            for fname in sorted(self.state[subj].keys()):
                v = self.state[subj][fname]
                cells = " | ".join(v.get(p, "⏳") for p in phase_keys)

                if show_lang:
                    lang_val = v.get("lang", "—")
                    cells += f" | {lang_val}"

                parts = []
                if "note" in v and v["note"] and v["note"] != "更新/新增":
                    parts.append(v["note"])
                cc = v.get("char_count", {})
                if cc:
                    parts.append(f"chars:{json.dumps(cc, separators=(',', ':'))}")
                note_str = " | ".join(parts) if parts else (v.get("note") or "—")

                lines.append(f"| {fname} | {cells} | {note_str} |")
            lines.append("")

        # A-4 Fix: use AtomicWriter so a crash during checklist render
        # never produces a half-written markdown table.
        AtomicWriter.write_text(self.checklist_file, "\n".join(lines))
