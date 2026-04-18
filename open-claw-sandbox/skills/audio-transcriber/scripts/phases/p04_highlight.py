# -*- coding: utf-8 -*-
"""
Phase 4: Highlight Marking (Anti-Tampering)
Refactored to V7.0 OOP Architecture
"""

# Group 1 — stdlib
import os
import sys
import re

# Group 2 — Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

# Group 3 — Core imports
from core import PipelineBase, AtomicWriter

# Delegate to standalone skill
from skills.smart_highlighter.scripts.highlight import SmartHighlighter

class Phase4Highlight(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p4", phase_name="重點標記", logger=None)
        
    def _get_lecture_base(self, fname: str):
        stem = os.path.splitext(fname)[0]
        m = re.match(r'^(.+)-(\d+)$', stem)
        if m: return m.group(1), int(m.group(2))
        return stem, None

    def _group_tasks(self, tasks):
        groups = {}
        for task in tasks:
            base, _seg = self._get_lecture_base(task["filename"])
            key = (task["subject"], base)
            groups.setdefault(key, []).append(task)
        for key in groups:
            groups[key].sort(key=lambda t: self._get_lecture_base(t["filename"])[1] or 0)
        return groups

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log(f"🧠 啟動 Phase 4：動態上色與重點標記模式 (Anti-Tampering)")
        
        tasks = self.get_tasks(prev_phase_key="p3", force=force, subject_filter=subject, file_filter=file_filter, single_mode=single_mode, resume_from=resume_from)
        if not tasks:
            self.log("📋 Phase 4 沒有待處理的檔案。")
            return
            
        groups = self._group_tasks(tasks)
        self.log(f"📋 共有 {len(tasks)} 個檔案，歸屬於 {len(groups)} 個標記群組。")
        idx = 1
        for (subj, base_name), tasks_in_group in groups.items():
            if self.check_system_health(): break
            
            self.log(f"📦 [{idx}/{len(groups)}] 正在標記：[{subj}] {base_name}.md")
            idx += 1
            
            source_path = os.path.join(self.dirs["p3"], subj, f"{base_name}.md")
            if not os.path.exists(source_path):
                self.log(f"⚠️ 找不到合併檔：{source_path}", "warn")
                continue
                
            with open(source_path, "r", encoding="utf-8") as f:
                full_text = f.read()

            p3_log_tail = ""
            if "## 📋 Phase 3 修改日誌" in full_text:
                body, p3_log_tail = full_text.split("## 📋 Phase 3 修改日誌", 1)
                full_text = body.rstrip().rstrip("-").strip()
                p3_log_tail = "## 📋 Phase 3 修改日誌" + p3_log_tail

            # Delegate to SmartHighlighter standalone skill
            # It inherently knows how to chunk, prompt, and protect content (verbatim_threshold)
            highlighter = SmartHighlighter(profile="strict")
            highlighter.logger = self.logger  # Share logger
            
            annotated_doc = highlighter.run(markdown_text=full_text, subject=subj)
            
            final_doc = annotated_doc
            if p3_log_tail: final_doc += f"\n\n---\n\n{p3_log_tail}"
            
            out_path = os.path.join(self.dirs["p4"], subj, f"{base_name}.md")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            AtomicWriter.write_text(out_path, final_doc)
                
            out_hash = self.state_manager.get_file_hash(out_path)
            for task in tasks_in_group:
                self.state_manager.update_task(subj, task["filename"], "p4", status="✅", 
                                               char_count=len(final_doc), output_hash=out_hash)
            self.log(f"✅ 重點上色完成：{base_name}.md")

            # 暫停機制：每個群組完成後檢查是否要 checkpoint
            if self.stop_requested:
                remaining_groups = list(groups.items())[idx - 1:]  # idx 已遞增，指向下一個群組
                if self.pause_requested and remaining_groups:
                    (next_subj, next_base), next_tasks = remaining_groups[0]
                    self.save_checkpoint(next_tasks[0]["subject"], next_tasks[0]["filename"])
                break

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase4Highlight().run(force=args.force, subject=args.subject)
