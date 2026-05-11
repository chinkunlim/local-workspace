"""
Phase 2: Glossary Application (Regex Only)
Refactored to remove LLM proofreading and HITL.
"""

import json
import os
import re
import sys

# Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase


class Phase2GlossaryApply(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p2", phase_name="術語詞庫套用", logger=None)

    def _apply_glossary_regex(self, text: str, subject: str) -> str:
        ref_dir = self.dirs.get("p0_ref", os.path.join(self.base_dir, "output", "00_glossary"))
        glossary_path = os.path.join(ref_dir, subject, "glossary.json")
        if not os.path.exists(glossary_path):
            return text
        try:
            with open(glossary_path, encoding="utf-8") as f:
                gloss = json.load(f)
        except Exception:
            return text

        replacements = 0
        for wrong, correct in gloss.items():
            if wrong.strip() == correct.strip():
                continue
            pattern = re.escape(wrong)
            new_text, n = re.subn(pattern, correct, text)
            if n:
                text = new_text
                replacements += n

        if replacements:
            self.log(f"🔄 [Regex術語修正] 共強制替換 {replacements} 處術語")
        return text

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🧠 啟動 Phase 2：術語詞庫套用模式")

        tasks = self.get_tasks(
            prev_phase_key="p1",
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )

        if not tasks:
            self.log("📋 Phase 2 沒有待處理的檔案。")
            return

        self.log(f"📋 Phase 2 共有 {len(tasks)} 個檔案待處理。")

        for idx, task in enumerate(tasks, 1):
            if self.check_system_health():
                break

            subj, fname = task["subject"], task["filename"]
            base_name = fname.replace(".m4a", "")

            in_path = os.path.join(self.dirs["p1"], subj, f"{base_name}.md")
            if not os.path.exists(in_path):
                self.log(f"⚠️ 找不到 P1 來源: {in_path}", "warn")
                continue

            with open(in_path, encoding="utf-8") as f:
                raw_text = f.read()

            self.log(f"📦 [{idx}/{len(tasks)}] 正在套用詞庫：[{subj}] {base_name}.md")

            corrected_text = self._apply_glossary_regex(raw_text, subj)

            out_path = os.path.join(self.dirs["p2"], subj, f"{base_name}.md")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            AtomicWriter.write_text(out_path, corrected_text)

            out_hash = self.state_manager.get_file_hash(out_path)
            self.state_manager.update_task(
                subj, fname, "p2", status="✅", char_count=len(corrected_text), output_hash=out_hash
            )
            self.log(f"✅ [{idx}/{len(tasks)}] 詞庫套用完成：{fname}")

            if self.stop_requested:
                break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase2GlossaryApply().run(force=args.force, subject=args.subject)
