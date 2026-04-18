# -*- coding: utf-8 -*-
import os
import sys

# Internal Core Bootstrap
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

from core import PipelineBase, AtomicWriter

# Delegate to standalone skill
from skills.note_generator.scripts.synthesize import NoteGenerator


class Phase3Synthesis(PipelineBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="phase3",
            phase_name="知識濃縮合成",
            skill_name="doc-parser"
        )

    def _read_figure_list(self, pdf_dir: str) -> str:
        fig_path = os.path.join(pdf_dir, "figure_list.md")
        if os.path.exists(fig_path):
            with open(fig_path, "r", encoding="utf-8") as f:
                return f.read()
        return "無圖片或圖表。"

    def run(self, subject: str, filename: str) -> bool:
        """
        Synthesize highlighted markdown blocks into a final comprehensive study guide.

        Args:
            subject: The subject category folder name.
            filename: The PDF filename.

        Returns:
            bool: True if successful, False if failed.
        """
        pdf_id = os.path.splitext(filename)[0]
        self.info(f"🧠 [Phase 3] 啟動知識合成: {pdf_id}")
        
        # Paths
        processed_dir = os.path.join(self.dirs["processed"], subject, pdf_id)
        highlighted_path = os.path.join(self.dirs["highlighted"], subject, pdf_id, "highlighted.md")
        raw_path = os.path.join(processed_dir, "raw_extracted.md")
        
        final_dir = os.path.join(self.dirs["synthesis"], subject, pdf_id)
        os.makedirs(final_dir, exist_ok=True)
        final_path = os.path.join(final_dir, "content.md")
        
        source_path = highlighted_path
        if not os.path.exists(source_path):
            self.warning(f"⚠️ [Phase 3] 找不到 highlighted.md，退回使用 raw_extracted.md")
            source_path = raw_path
            
        if not os.path.exists(source_path):
            self.warning(f"⚠️ [Phase 3] 來源文件不存在: {source_path}")
            return False
            
        with open(source_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        figure_list_txt = self._read_figure_list(processed_dir)
        
        from core.glossary_manager import GlossaryManager
        workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(self.base_dir, "..", "..")))
        gm = GlossaryManager(workspace_root, self.skill_name)
        gm.sync_all(logger=self)
        glossary_injection = gm.get_global_prompt_injection()
        
        self.info(f"📖 [Phase 3] 原文長度 {len(raw_text):,} 字元，委派給 NoteGenerator")
        
        generator = NoteGenerator(profile="default")
        generator.logger = self.logger
        
        try:
            final_content = generator.run(
                markdown_text=raw_text,
                subject=subject,
                label=pdf_id,
                figure_list=figure_list_txt,
                glossary_injection=glossary_injection
            )
        except Exception as e:
            self.error(f"❌ Synthesis failed: {e}")
            return False

        # Write output successfully
        AtomicWriter.write_text(final_path, final_content)
        self.info(f"✅ [Phase 3] 知識合成完成！已寫入 {final_path}")
        return True
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="The PDF path")
    args = parser.parse_args()
    
    filename = os.path.basename(args.pdf)
    phase = Phase3Synthesis()
    success = phase.run("Default", filename)
    print(f"Success: {success}")
