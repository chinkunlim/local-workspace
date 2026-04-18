# -*- coding: utf-8 -*-
import os
import sys

# Internal Core Bootstrap
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

from core import PipelineBase, AtomicWriter
from core.text_utils import smart_split


class Phase3Synthesis(PipelineBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="phase3",
            phase_name="知識濃縮合成",
            skill_name="pdf-knowledge"
        )
        config = self.get_config("phase3")
        self.syn_model = config.get("model")
        self.syn_options = config.get("options", {})
        if not self.syn_model:
            raise RuntimeError("Missing model in phase3 config profile")
        
        self.max_chunk = self.config_manager.get_nested("pdf_processing", "chunking", "max_chunk_chars") or 8000
        self.min_chunk_chars = self.config_manager.get_nested("pdf_processing", "chunking", "min_chunk_chars") or 50
        self.min_retention_ratio = 0.01  # 1% content-loss guard threshold (PDFs output very dense text summaries)

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
        
        # 1. Chunking
        chunks = smart_split(raw_text, self.max_chunk)
        self.info(f"📦 [Phase 3] 原文長度 {len(raw_text):,} 字元，將進行 {len(chunks)} 次 Map 處理 (模型: {self.syn_model})")
        
        # 2. MAP phase
        map_prompt_template = self.get_prompt("Phase 3 Map: Concept Extraction")
        if not map_prompt_template:
            self.error("❌ 找不到 Phase 3 Map 的 prompt 指令，請確認 prompt.md 內有對應的段落。")
            return False
        
        map_results = []
        for ci, chunk in enumerate(chunks, 1):
            if len(chunk.strip()) < self.min_chunk_chars:
                continue
                
            prompt = map_prompt_template.replace("{INPUT}", chunk)
            self.info(f"   🗂  Map [{ci}/{len(chunks)}]：提取關鍵材料...")
            
            try:
                res = self.llm.generate(
                    model=self.syn_model,
                    prompt=prompt,
                    options=self.syn_options,
                    logger=self
                )
                map_results.append(res)
            except Exception as e:
                self.error(f"❌ Map [{ci}/{len(chunks)}] 失敗: {e}")
                return False

        from core.glossary_manager import GlossaryManager
        workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(self.base_dir, "..", "..")))
        gm = GlossaryManager(workspace_root, self.skill_name)
        gm.sync_all(logger=self)
        glossary_injection = gm.get_global_prompt_injection()
        
        # 3. REDUCE phase
        reduce_prompt_template = self.get_prompt("Phase 3 Reduce: Final Synthesis")
        if not reduce_prompt_template:
            self.error("❌ 找不到 Phase 3 Reduce 的 prompt 指令，請確認 prompt.md 內有對應的段落。")
            return False
            
        reduce_prompt = (
            reduce_prompt_template
            .replace("{GLOSSARY}", f"{glossary_injection}")
            .replace("{FIGURES}", f"{figure_list_txt}")
            .replace("{NOTES}", "\n\n---\n\n".join(map_results))
        )
        
        self.info("🔄 [Phase 3] Reduce：啟動終極版面合成整合...")
        try:
            final_content = self.llm.generate(
                model=self.syn_model,
                prompt=reduce_prompt,
                options=self.syn_options,
                logger=self
            )
        except Exception as e:
            self.error(f"❌ Reduce 失敗: {e}")
            return False
            
        # 4. Content-Loss Guard (防偷懶閥門)
        retention_ratio = len(final_content) / max(1, len(raw_text))
        self.info(f"📊 [Phase 3] 壓縮率檢核: 最終 {len(final_content):,} 字元 / 原始 {len(raw_text):,} 字元 (保留率 {retention_ratio:.1%})")
        
        if retention_ratio < self.min_retention_ratio:
            self.error(f"❌ [Content-loss Guard] 觸發：筆記保留率 {retention_ratio:.1%} 低於下限 {self.min_retention_ratio:.1%}！")
            self.error(f"   LLM 模型可能發生截斷或過度簡化(偷懶)，本次寫入中止。請調整系統 prompt 或更換擁有更大窗口的模型。")
            return False
            
        # Write output successfully
        AtomicWriter.write_text(final_path, final_content)
        self.info(f"✅ [Phase 3] 知識合成完成！已寫入 {final_path}")
        self.llm.unload_model(self.syn_model, logger=self)
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
