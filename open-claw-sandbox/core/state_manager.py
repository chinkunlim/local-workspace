# -*- coding: utf-8 -*-
import os
import json
import hashlib
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

from .atomic_writer import AtomicWriter

class StateManager:
    # Default phases for audio-transcriber
    PHASES_VOICE = ["p1", "p2", "p3", "p4", "p5"]
    # Phase set for doc-parser
    PHASES_PDF   = ["p1a", "p1b", "p1c", "p1d", "p2a", "p2b"]
    # Phase labels for checklist rendering
    PHASE_LABELS_VOICE = {"p1": "P1 (轉錄)", "p2": "P2 (校對)", "p3": "P3 (合併)",
                          "p4": "P4 (標記)", "p5": "P5 (Notion)" }
    PHASE_LABELS_PDF   = {"p1a": "P1a (診斷)", "p1b": "P1b (提取)", "p1c": "P1c (向量圖)",
                          "p1d": "P1d (OCR)",  "p2a": "P2a (VLM)",  "p2b": "P2b (合成)" }

    def __init__(self, base_dir: str, skill_name: str = "audio-transcriber"):
        self.base_dir   = base_dir
        self.skill_name = skill_name
        self.PHASES     = self.PHASES_PDF if skill_name == "doc-parser" else self.PHASES_VOICE
        self._phase_labels = self.PHASE_LABELS_PDF if skill_name == "doc-parser" else self.PHASE_LABELS_VOICE
        self.file_ext   = "*.pdf" if skill_name == "doc-parser" else "*.m4a"
        canonical_state_dir = os.path.join(base_dir, "state")
        legacy_state_file = os.path.join(base_dir, ".pipeline_state.json")
        legacy_checklist_file = os.path.join(base_dir, "checklist.md")
        canonical_state_file = os.path.join(canonical_state_dir, ".pipeline_state.json")
        canonical_checklist_file = os.path.join(canonical_state_dir, "checklist.md")

        self.state_file = canonical_state_file if os.path.exists(canonical_state_file) or not os.path.exists(legacy_state_file) else legacy_state_file
        self.checklist_file = canonical_checklist_file if os.path.exists(canonical_checklist_file) or not os.path.exists(legacy_checklist_file) else legacy_checklist_file

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
        """Load internal state from JSON or return empty structure."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    self._checkpoint = raw.get("_checkpoint")
                    if isinstance(raw.get("_state"), dict):
                        return raw.get("_state", {})
                    return {k: v for k, v in raw.items() if not str(k).startswith("_")}
            except Exception:
                pass
        return {}

    def _save_state(self):
        """Persist state to JSON and re-render checklist.md view."""
        with self._lock:
            payload = self._serialize_state()
            AtomicWriter.write_json(self.state_file, payload)
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
            
            subjects = [d for d in os.listdir(self.raw_dir) if os.path.isdir(os.path.join(self.raw_dir, d))]
            for subj in subjects:
                if subj not in self.state:
                    self.state[subj] = {}
                
                subj_audio = os.path.join(self.raw_dir, subj)
                import glob
                physical_files = glob.glob(os.path.join(subj_audio, self.file_ext))
                
                for pf in physical_files:
                    fname = os.path.basename(pf)
                    fhash = self.get_file_hash(pf)
                    mtime = datetime.fromtimestamp(os.path.getmtime(pf)).strftime('%Y-%m-%d')
                    
                    if fname not in self.state[subj]:
                        self.state[subj][fname] = {
                            **{p: "⏳" for p in self.PHASES},
                            "hash": fhash,
                            "date": mtime,
                            "note": "更新/新增",
                            "output_hashes": {},
                            "char_count": {}
                        }
                    else:
                        # If raw audio changed, negate everything
                        if self.state[subj][fname].get("hash") != fhash:
                            self.state[subj][fname].update({
                                **{p: "⏳" for p in self.PHASES},
                                "hash": fhash,
                                "date": mtime,
                                "note": "原始檔已變更"
                            })
            self._save_state()

    def cascade_invalidate(self, subject: str, filename: str, changed_phase: str):
        """Invalidate dependent phases. E.g. if p1 output changes, p2-p5 become ⏳."""
        with self._lock:
            if subject not in self.state or filename not in self.state[subject]: return
            
            idx = self.PHASES.index(changed_phase)
            record = self.state[subject][filename]
            
            # All subsequent phases are invalidated
            invalidated_any = False
            for p in self.PHASES[idx+1:]:
                if record.get(p) == "✅":
                    record[p] = "⏳"
                    invalidated_any = True
                    
            if invalidated_any:
                record["note"] = f"{changed_phase.upper()} 被手動修改 (DAG 重啟)"
                self._save_state()

    def update_task(self, subject: str, filename: str, phase_key: str, status: str = "✅", 
                    char_count: int = None, output_hash: str = None, note_tag: str = None):
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
                            if not expected_hash: continue
                            
                            target_dir = phase_dirs.get(p)
                            if not target_dir: continue
                            
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
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                with open(self.state_file, "r", encoding="utf-8") as f:
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

    def _render_checklist(self):
        """Render read-only checklist.md — supports any skill's phase set."""
        phase_keys   = self.PHASES
        phase_labels = self._phase_labels

        header_cols = " | ".join(phase_labels.get(p, p.upper()) for p in phase_keys)
        sep_cols    = " | ".join(":---:" for _ in phase_keys)

        with open(self.checklist_file, "w", encoding="utf-8") as f:
            skill_display = {"audio-transcriber": "學習進度", "doc-parser": "知識庫處理進度"}.get(self.skill_name, "進度")
            f.write(f"# {skill_display} (總表)\n\n")
            f.write("> 🚨 本檔案由系統 `.pipeline_state.json` 自動映射生成，請勿手動修改。\n")
            f.write("> 更改輸出目錄下的 `.md` 檔案將被系統偵測並觸發自動重新運算 (DAG Cascade)。\n\n")

            for subj in sorted(self.state.keys()):
                f.write(f"## {subj}\n\n")
                f.write(f"| 檔案/ID | {header_cols} | 狀態備註 |\n")
                f.write(f"| :--- | {sep_cols} | :--- |\n")

                for fname in sorted(self.state[subj].keys()):
                    v     = self.state[subj][fname]
                    cells = " | ".join(v.get(p, "⏳") for p in phase_keys)

                    parts = []
                    if "note" in v and v["note"] and v["note"] != "更新/新增":
                        parts.append(v["note"])
                    cc = v.get("char_count", {})
                    if cc:
                        parts.append(f"chars:{json.dumps(cc, separators=(',', ':'))}")
                    note_str = " | ".join(parts) if parts else (v.get("note") or "—")

                    f.write(f"| {fname} | {cells} | {note_str} |\n")
                f.write("\n")
