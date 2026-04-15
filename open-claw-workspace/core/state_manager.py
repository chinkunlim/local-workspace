# -*- coding: utf-8 -*-
import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

class StateManager:
    PHASES = ["p1", "p2", "p3", "p4", "p5"]

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.state_file = os.path.join(base_dir, ".pipeline_state.json")
        self.checklist_file = os.path.join(base_dir, "checklist.md")
        self.raw_dir = os.path.join(base_dir, "raw_data")
        self.state: Dict[str, Dict[str, Any]] = self._load_state()

    def _load_state(self) -> Dict[str, Dict[str, Any]]:
        """Load internal state from JSON or return empty structure."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_state(self):
        """Persist state to JSON and re-render checklist.md view."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
        self._render_checklist()

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
        if not os.path.exists(self.raw_dir):
            return
            
        subjects = [d for d in os.listdir(self.raw_dir) if os.path.isdir(os.path.join(self.raw_dir, d))]
        for subj in subjects:
            if subj not in self.state:
                self.state[subj] = {}
            
            subj_audio = os.path.join(self.raw_dir, subj)
            import glob
            physical_files = glob.glob(os.path.join(subj_audio, "*.m4a"))
            
            for pf in physical_files:
                fname = os.path.basename(pf)
                fhash = self.get_file_hash(pf)
                mtime = datetime.fromtimestamp(os.path.getmtime(pf)).strftime('%Y-%m-%d')
                
                if fname not in self.state[subj]:
                    self.state[subj][fname] = {
                        "p1": "⏳", "p2": "⏳", "p3": "⏳", "p4": "⏳", "p5": "⏳",
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
                            "p1": "⏳", "p2": "⏳", "p3": "⏳", "p4": "⏳", "p5": "⏳",
                            "hash": fhash,
                            "date": mtime,
                            "note": "音檔已變更"
                        })
        self._save_state()

    def cascade_invalidate(self, subject: str, filename: str, changed_phase: str):
        """Invalidate dependent phases. E.g. if p1 output changes, p2-p5 become ⏳."""
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
        raw: Dict = {}
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except Exception:
                raw = {"_state": self.state}
        raw["_checkpoint"] = {
            "subject": subject,
            "filename": filename,
            "phase_key": phase_key,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)

    def load_checkpoint(self) -> Optional[Dict[str, str]]:
        """
        從 state file 讀取 checkpoint。
        若不存在，回傳 None；存在則回傳 {subject, filename, phase_key, saved_at}。
        """
        if not os.path.exists(self.state_file):
            return None
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw.get("_checkpoint", None)
        except Exception:
            return None

    def clear_checkpoint(self):
        """清除 checkpoint（正常完成或使用者選擇全新開始時呼叫）。"""
        if not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            raw.pop("_checkpoint", None)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _render_checklist(self):
        """Render read-only checklist.md"""
        with open(self.checklist_file, "w", encoding="utf-8") as f:
            f.write("# 學習進度 (總表)\n\n")
            f.write("> 🚨 本檔案由系統 `.pipeline_state.json` 自動映射生成，請勿手動修改。\n")
            f.write("> 更改 P1 到 P4 目錄下的 `.md` 檔案將會被系統偵測並觸發自動重新運算 (DAG Cascade)。\n\n")
            for subj in sorted(self.state.keys()):
                f.write(f"## {subj}\n\n")
                f.write("| 檔案名稱 | P1 (轉錄) | P2 (校對) | P3 (合併) | P4 (標記) | P5 (Notion) | 狀態備註 |\n")
                f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |\n")
                for fname in sorted(self.state[subj].keys()):
                    v = self.state[subj][fname]
                    
                    parts = []
                    if "note" in v and v["note"] and v["note"] != "更新/新增":
                        parts.append(v["note"])
                    
                    cc = v.get("char_count", {})
                    if cc:
                        parts.append(f"chars:{json.dumps(cc, separators=(',', ':'))}")
                        
                    note_str = " | ".join(parts) if parts else v.get("note", "更新/新增")
                    f.write(f"| {fname} | {v.get('p1','⏳')} | {v.get('p2','⏳')} | {v.get('p3','⏳')} | {v.get('p4','⏳')} | {v.get('p5','⏳')} | {note_str} |\n")
                f.write("\n")
