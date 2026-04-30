from datetime import datetime
import fcntl
import hashlib
import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

from core.atomic_writer import AtomicWriter
from core.state_backend import get_state_backend

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
    # Default phases for audio-transcriber
    PHASES_VOICE = ["p1", "p2", "p3"]
    # Phase set for doc-parser
    PHASES_PDF = ["p0a", "p1a", "p1b", "p1c", "p1d"]
    # Phase set for knowledge-compiler
    PHASES_COMPILER = ["p1"]
    # Phase set for interactive-reader
    PHASES_READER = ["p1"]
    # Phase set for telegram-kb-agent
    PHASES_AGENT = ["p1"]
    # Phase set for academic-edu-assistant
    PHASES_ACADEMIC = ["p1", "p2"]

    # Phase labels for checklist rendering
    PHASE_LABELS_VOICE = {"p1": "P1 (轉錄)", "p2": "P2 (校對)", "p3": "P3 (合併)"}
    PHASE_LABELS_PDF = {
        "p0a": "P0a (診斷)",
        "p1a": "P1a (提取)",
        "p1b": "P1b (向量圖)",
        "p1c": "P1c (OCR評估)",
        "p1d": "P1d (VLM視覺)",
    }
    PHASE_LABELS_COMPILER = {"p1": "P1 (編譯與雙向連結)"}
    PHASE_LABELS_READER = {"p1": "P1 (互動標籤處理)"}
    PHASE_LABELS_AGENT = {"p1": "P1 (向量庫服務)"}
    PHASE_LABELS_ACADEMIC = {"p1": "P1 (RAG 交叉比對)", "p2": "P2 (Anki 生成)"}

    def __init__(self, base_dir: str, skill_name: str = "audio-transcriber"):
        self.base_dir = base_dir
        self.skill_name = skill_name
        if skill_name == "doc-parser":
            self.PHASES = self.PHASES_PDF
            self._phase_labels = self.PHASE_LABELS_PDF
            self.file_ext = "*.pdf"
        elif skill_name == "knowledge-compiler":
            self.PHASES = self.PHASES_COMPILER
            self._phase_labels = self.PHASE_LABELS_COMPILER
            self.file_ext = "*.md"
        elif skill_name == "interactive-reader":
            self.PHASES = self.PHASES_READER
            self._phase_labels = self.PHASE_LABELS_READER
            self.file_ext = "*.md"
        elif skill_name == "telegram-kb-agent":
            self.PHASES = self.PHASES_AGENT
            self._phase_labels = self.PHASE_LABELS_AGENT
            self.file_ext = "*.md"
        elif skill_name == "academic-edu-assistant":
            self.PHASES = self.PHASES_ACADEMIC
            self._phase_labels = self.PHASE_LABELS_ACADEMIC
            self.file_ext = "*.md"
        else:
            self.PHASES = self.PHASES_VOICE
            self._phase_labels = self.PHASE_LABELS_VOICE
            self.file_ext = "*.m4a"
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

        if skill_name == "interactive-reader":
            # Interactive reader directly monitors and mutates the wiki
            self.raw_dir = os.path.abspath(os.path.join(base_dir, "..", "wiki"))
        else:
            self.raw_dir = os.path.join(base_dir, "input")

        self._lock = threading.RLock()
        self._checkpoint: Optional[Dict[str, Any]] = None
        self.state: Dict[str, Dict[str, Any]] = self._load_state()

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

            if self.skill_name == "interactive-reader":
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

                physical_files = glob.glob(os.path.join(subj_path, self.file_ext))

                for pf in physical_files:
                    fname = os.path.basename(pf)
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

    def get_dashboard_text(self) -> str:
        """根據當前狀態與 Phase 定義，產生對齊的進度追蹤儀表板字串。"""
        with self._lock:
            counters = {p: {"done": 0, "total": 0} for p in self.PHASES}
            for subj_data in self.state.values():
                for _fname, record in subj_data.items():
                    for key in counters:
                        counters[key]["total"] += 1
                        if record.get(key) == "✅":
                            counters[key]["done"] += 1

        lines = []
        skill_display = {
            "audio-transcriber": "語音轉錄狀態與 DAG 追蹤面板",
            "doc-parser": "文件解析狀態與 DAG 追蹤面板",
            "academic-edu-assistant": "學術教育助手狀態與 DAG 追蹤面板",
            "inbox-manager": "收件匣管理狀態與 DAG 追蹤面板",
            "interactive-reader": "互動式閱讀狀態與 DAG 追蹤面板",
            "knowledge-compiler": "知識編譯狀態與 DAG 追蹤面板",
            "note_generator": "筆記生成狀態與 DAG 追蹤面板",
            "smart_highlighter": "智能高亮狀態與 DAG 追蹤面板",
            "telegram-kb-agent": "Telegram 知識庫代理狀態與 DAG 追蹤面板",
        }.get(self.skill_name, f"{self.skill_name} 狀態與 DAG 追蹤面板")

        lines.append("=" * 36)
        lines.append(f"     📊 {skill_display}")
        lines.append("=" * 36)

        for p in self.PHASES:
            label = self._phase_labels.get(p, p.upper())
            done = counters[p]["done"]
            total = counters[p]["total"]
            if done == total and total > 0:
                icon = "✅"
            elif done > 0:
                icon = "⏳"
            else:
                icon = "❌"
            lines.append(f"  [{label}]: {icon} {done}/{total}")
        lines.append("=" * 36 + "\n")
        return "\n".join(lines)

    def print_dashboard(self):
        """直接在終端機印出儀表板。"""
        print("\n" + self.get_dashboard_text())

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

        header_cols = " | ".join(phase_labels.get(p, p.upper()) for p in phase_keys)
        sep_cols = " | ".join(":---:" for _ in phase_keys)

        lines: List[str] = []
        skill_display = {
            "audio-transcriber": "學習進度",
            "doc-parser": "知識庫處理進度",
            "knowledge-compiler": "知識庫編譯進度",
            "interactive-reader": "互動閱讀處理進度",
            "telegram-kb-agent": "行動知識庫進度",
            "academic-edu-assistant": "學術助手進度",
        }.get(self.skill_name, "進度")

        lines.append(f"# {skill_display} (總表)\n")
        lines.append("> 🚨 本檔案由系統 `.pipeline_state.json` 自動映射生成，請勿手動修改。")
        lines.append(
            "> 更改輸出目錄下的 `.md` 檔案將被系統偵測並觸發自動重新運算 (DAG Cascade)。\n"
        )

        for subj in sorted(self.state.keys()):
            lines.append(f"## {subj}\n")
            lines.append(f"| 檔案/ID | {header_cols} | 狀態備註 |")
            lines.append(f"| :--- | {sep_cols} | :--- |")

            for fname in sorted(self.state[subj].keys()):
                v = self.state[subj][fname]
                cells = " | ".join(v.get(p, "⏳") for p in phase_keys)

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
