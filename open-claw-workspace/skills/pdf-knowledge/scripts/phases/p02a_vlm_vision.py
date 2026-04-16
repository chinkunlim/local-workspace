# -*- coding: utf-8 -*-
import sys, os

import os, sys
# Workspace Root Resolver
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../..")))

import base64
import re
from core import PipelineBase, AtomicWriter

class Phase2aVLMVision(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="phase2a",
            phase_name="VLM 視覺圖表解析",
            skill_name="pdf-knowledge"
        )
        config = self.get_config("phase2a")
        self.vlm_model = config.get("model")
        self.vlm_options = config.get("options", {})
        if not self.vlm_model:
            raise RuntimeError("Missing model in phase2a config profile")

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _clean_markdown_text(self, text: str) -> str:
        """Escape tricky characters that break Markdown tables."""
        text = text.replace('\n', '<br>')
        text = text.replace('|', '\\|')
        return text

    def run_vision(self, pdf_id: str, subject: str = "Default"):
        self.info(f"👁️ [Phase 2a] 啟動 VLM 視覺圖表解析: {pdf_id}")
        
        pdf_dir = os.path.join(self.dirs["processed"], subject, pdf_id)
        figure_list_path = os.path.join(pdf_dir, "figure_list.md")
        
        if not os.path.exists(figure_list_path):
            self.warning(f"⚠️ [Phase 2a] 找不到 figure_list.md，略過。")
            return
            
        with open(figure_list_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Parse table headers to map indices dynamically
        header_idx = -1
        for i, line in enumerate(lines):
            if "| 檔案名稱 |" in line or "| :--- |" in line:
                if "檔案名稱" in line:
                    header_idx = i
                    headers = [col.strip() for col in line.split("|")[1:-1]]
                break
                
        if header_idx == -1 or not headers:
            self.error("❌ 無法解析 figure_list.md 的表格標題格式。")
            return

        try:
            filename_col = headers.index("檔案名稱")
            vlm_col = headers.index("VLM 描述")
        except ValueError:
            self.error("❌ figure_list.md 缺少必要的 '檔案名稱' 或 'VLM 描述' 欄位。")
            return

        prompt = self.get_prompt("Phase 2a: VLM Vision")
        if not prompt:
            self.error("❌ 找不到 Phase 2a 的 prompt 指令，請確認 prompt.md 內有對應的段落。")
            return

        modifications = 0
        for i in range(header_idx + 2, len(lines)):
            line = lines[i].strip()
            if not line.startswith("|") or not line.endswith("|"):
                continue  # Not a table row
                
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) != len(headers):
                continue
                
            if "待 VLM 描述" in cols[vlm_col]:
                rel_img_path = cols[filename_col]
                abs_img_path = os.path.join(pdf_dir, rel_img_path)
                
                if not os.path.exists(abs_img_path):
                    self.warning(f"⚠️ 找不到實體圖片檔案: {abs_img_path}")
                    cols[vlm_col] = "圖片遺失"
                else:
                    self.info(f"🔍 正在解析圖片: {rel_img_path}")
                    b64_image = self._encode_image(abs_img_path)
                    
                    try:
                        res = self.llm.generate(
                            model=self.vlm_model,
                            prompt=prompt,
                            images=[b64_image],
                            options=self.vlm_options,
                            logger=self
                        )
                        safe_res = self._clean_markdown_text(res.strip())
                        cols[vlm_col] = safe_res
                        self.info(f"✅ 解析完成: {safe_res[:20]}...")
                        modifications += 1
                    except Exception as e:
                        self.error(f"❌ VLM 解析失敗 ({rel_img_path}): {e}")
                        cols[vlm_col] = f"[錯誤] {self._clean_markdown_text(str(e))}"

                # Reconstruct row
                lines[i] = "| " + " | ".join(cols) + " |\n"

        if modifications > 0:
            AtomicWriter.write_text(figure_list_path, "".join(lines))
            self.info(f"💾 [Phase 2a] 成功更新了 {modifications} 張圖片的描述至 figure_list.md")
        else:
            self.info("🆗 [Phase 2a] 沒有需要解析的新圖片。")
            
        self.llm.unload_model(self.vlm_model, logger=self)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_id", help="The PDF identifier string inside 02_Processed")
    args = parser.parse_args()
    
    phase = Phase2aVLMVision()
    phase.run_vision(args.pdf_id)
