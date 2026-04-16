# -*- coding: utf-8 -*-
import sys, os

import os, sys
# Workspace Root Resolver
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../..")))

from core import PipelineBase, AtomicWriter
from core.text_utils import smart_split


class Phase2bSynthesis(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="phase2b",
            phase_name="知識濃縮合成",
            skill_name="pdf-knowledge"
        )
        self.syn_model = self.config_manager.get_nested("models", "synthesis")
        if not self.syn_model:
            raise RuntimeError("Missing models.synthesis in config.yaml")
        
        self.max_chunk = self.config_manager.get_nested("pdf_processing", "chunking", "max_chunk_chars") or 8000
        self.min_retention_ratio = 0.01  # 1% content-loss guard threshold (PDFs output very dense text summaries)

    def _read_figure_list(self, pdf_dir: str) -> str:
        fig_path = os.path.join(pdf_dir, "figure_list.md")
        if os.path.exists(fig_path):
            with open(fig_path, "r", encoding="utf-8") as f:
                return f.read()
        return "無圖片或圖表。"

    def run_synthesis(self, pdf_id: str, subject: str = "Default"):
        self.info(f"🧠 [Phase 2b] 啟動知識合成: {pdf_id}")
        
        # Paths
        processed_dir = os.path.join(self.dirs["processed"], subject, pdf_id)
        raw_path = os.path.join(processed_dir, "raw_extracted.md")
        final_dir = os.path.join(self.dirs["final"], subject, pdf_id)
        os.makedirs(final_dir, exist_ok=True)
        final_path = os.path.join(final_dir, "content.md")
        
        if not os.path.exists(raw_path):
            self.warning(f"⚠️ [Phase 2b] 找不到 raw_extracted.md: {raw_path}")
            return
            
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        figure_list_txt = self._read_figure_list(processed_dir)
        
        # 1. Chunking
        chunks = smart_split(raw_text, self.max_chunk)
        self.info(f"📦 [Phase 2b] 原文長度 {len(raw_text):,} 字元，將進行 {len(chunks)} 次 Map 處理 (模型: {self.syn_model})")
        
        # 2. MAP phase
        map_prompt_template = (
            "你是一個專業的學術與知識分析師。以下是 PDF 文件的部分原始萃取內容，可能包含換行碎化或 OCR 錯誤。\n"
            "請為這個區塊提取出核心知識點、重要的定義、數據以及公式推導邏輯。\n"
            "請將產出結構化為豐富的 Markdown 筆記。\n\n"
            "【原始內容】:\n{INPUT}"
        )
        
        map_results = []
        for ci, chunk in enumerate(chunks, 1):
            if len(chunk.strip()) < 50:
                continue
                
            prompt = map_prompt_template.replace("{INPUT}", chunk)
            self.info(f"   🗂  Map [{ci}/{len(chunks)}]：提取關鍵材料...")
            
            try:
                res = self.llm.generate(model=self.syn_model, prompt=prompt, logger=self)
                map_results.append(res)
            except Exception as e:
                self.error(f"❌ Map [{ci}/{len(chunks)}] 失敗: {e}")
                return

        from core.glossary_manager import GlossaryManager
        gm = GlossaryManager(_workspace_root)
        gm.sync_all(logger=self)
        glossary_injection = gm.get_global_prompt_injection()
        
        # 3. REDUCE phase
        reduce_prompt = (
            "你是一個頂尖的技術筆記整理專家。以下是我透過 AI 逐步解讀一份文件所得出的「各段落重點筆記」，以及一份「圖表清單 (包含 VLM 解讀)」。\n\n"
            "請將這些材料融合成一份結構完美、排版嚴謹的最終知識庫筆記 (Final Knowledge Base Markdown)。\n"
            "【要求】\n"
            "1. 必須具備清晰的階層標題 (H1, H2, H3)。\n"
            "2. 絕對不要流失核心資訊、數學公式和專有名詞。\n"
            "3. 如果圖表清單內有重要的圖片資訊，請適度在對應概念的段落提及或引用。\n"
            "4. 以專業的[繁體中文]撰寫。\n\n"
            f"{glossary_injection}\n\n"
            
            "【圖表清單與解析】:\n"
            f"{figure_list_txt}\n\n"
            
            "【各段落重點筆記】:\n"
            + "\n\n---\n\n".join(map_results)
        )
        
        self.info("🔄 [Phase 2b] Reduce：啟動終極版面合成整合...")
        try:
            final_content = self.llm.generate(model=self.syn_model, prompt=reduce_prompt, logger=self)
        except Exception as e:
            self.error(f"❌ Reduce 失敗: {e}")
            return
            
        # 4. Content-Loss Guard (防偷懶閥門)
        retention_ratio = len(final_content) / max(1, len(raw_text))
        self.info(f"📊 [Phase 2b] 壓縮率檢核: 最終 {len(final_content):,} 字元 / 原始 {len(raw_text):,} 字元 (保留率 {retention_ratio:.1%})")
        
        if retention_ratio < self.min_retention_ratio:
            self.error(f"❌ [Content-loss Guard] 觸發：筆記保留率 {retention_ratio:.1%} 低於下限 {self.min_retention_ratio:.1%}！")
            self.error(f"   LLM 模型可能發生截斷或過度簡化(偷懶)，本次寫入中止。請調整系統 prompt 或更換擁有更大窗口的模型。")
            return
            
        # Write output successfully
        AtomicWriter.write_text(final_path, final_content)
        self.info(f"✅ [Phase 2b] 知識合成完成！已寫入 {final_path}")
        self.llm.unload_model(self.syn_model, logger=self)
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_id", help="The PDF identifier string")
    args = parser.parse_args()
    
    phase = Phase2bSynthesis()
    phase.run_synthesis(args.pdf_id)
