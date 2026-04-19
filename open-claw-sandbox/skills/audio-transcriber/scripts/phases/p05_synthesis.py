# -*- coding: utf-8 -*-
"""
Phase 5: Notion Knowledge Synthesis
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
from skills.note_generator.scripts.synthesize import NoteGenerator

class Phase5NotionSynthesis(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p5", phase_name="Notion 知識合成", logger=None)
        
    def _clean_content(self, content: str) -> str:
        if "## 📋 Phase 3 修改日誌" in content:
            content = content.split("## 📋 Phase 3 修改日誌", 1)[0].rstrip().rstrip("-").strip()
        return re.sub(r'==(.+?)==', r'\1', content, flags=re.DOTALL)

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log(f"✨ 啟動 Phase 5：Notion 知識合成")

        tasks = self.get_tasks(prev_phase_key="p4", force=force, subject_filter=subject, file_filter=file_filter, single_mode=single_mode, resume_from=resume_from)
        if not tasks:
            return

        self.log(f"📋 共有 {len(tasks)} 個檔案待合成。")

        for idx, task in enumerate(tasks, 1):
            if self.check_system_health():
                break

            subj, fname = task["subject"], task["filename"]
            base_name = os.path.splitext(fname)[0]
            m = re.match(r'^(.+)-(\d+)$', base_name)
            lecture_base = m.group(1) if m else base_name

            in_path = os.path.join(self.dirs["p4"], subj, f"{lecture_base}.md")
            out_path = os.path.join(self.dirs["p5"], subj, f"{lecture_base}.md")

            if not os.path.exists(in_path):
                self.log(f"⚠️ 找不到來源：{in_path}", "warn")
                continue

            with open(in_path, "r", encoding="utf-8") as f:
                content = self._clean_content(f.read())

            self.log(f"📝 [{idx}/{len(tasks)}] 生成筆記：[{subj}] {lecture_base}.md ({len(content)} 字元)")

            try:
                generator = NoteGenerator(profile="default")
                generator.logger = self.logger
                
                final_doc = generator.run(
                    markdown_text=content,
                    subject=subj,
                    label=lecture_base
                )

                AtomicWriter.write_text(out_path, final_doc)

                out_hash = self.state_manager.get_file_hash(out_path)
                self.state_manager.update_task(subj, fname, "p5", char_count=len(final_doc), note_tag=None, output_hash=out_hash)
                
                self.log(f"✅ [{idx}/{len(tasks)}] 筆記完成：{lecture_base}.md")

                # Publish to wiki (Obsidian Vault) via knowledge-compiler's input
                wiki_dir = os.path.abspath(os.path.join(self.base_dir, "..", "..", "data", "wiki"))
                os.makedirs(wiki_dir, exist_ok=True)
                wiki_path = os.path.join(wiki_dir, subj, f"{lecture_base}.md")
                os.makedirs(os.path.dirname(wiki_path), exist_ok=True)
                AtomicWriter.write_text(wiki_path, final_doc)
                self.log(f"📚 [{idx}/{len(tasks)}] 已發布至 Obsidian Vault: {wiki_path}")

                # 暫停機制：每個任務完成後檢查是否要 checkpoint
                if self.stop_requested:
                    if self.pause_requested and idx < len(tasks):
                        next_task = tasks[idx]  # idx 已是 1-based，下一個剛好
                        self.save_checkpoint(next_task["subject"], next_task["filename"])
                    break

            except Exception as e:
                self.log(f"❌ 合成失敗 {lecture_base}.md: {e}", "error")

        # Models are handled by NoteGenerator

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase5NotionSynthesis().run(force=args.force, subject=args.subject)
