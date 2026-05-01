import json
import os

# Internal Core Bootstrap
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase
from core.utils.file_utils import encode_image_b64  # S3: DRY — replaces private _encode_image()


class Phase1dVLMVision(PipelineBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="phase1d", phase_name="VLM 視覺圖表解析", skill_name="doc_parser"
        )
        config = self.get_config("phase1d")
        self.vlm_model = config.get("model")
        self.vlm_options = config.get("options", {})
        if not self.vlm_model:
            raise RuntimeError("Missing model in phase1d config profile")

    def _read_vlm_prompt_route(self, subject: str, pdf_id: str) -> str:
        """F1: Read vlm_prompt_route from scan_report.json to select an adaptive prompt.

        Returns:
            str: prompt route key, e.g. "academic", "report", "manual", "default".
        """
        report_path = os.path.join(
            self.dirs.get("processed", ""), subject, pdf_id, "scan_report.json"
        )
        try:
            with open(report_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("vlm_prompt_route", "default")
        except Exception:
            return "default"

    def _get_adaptive_vlm_prompt(self, subject: str, pdf_id: str) -> str:
        """Return the best-fit VLM prompt based on Phase 0a intent classification.

        Prompt section naming convention in prompt.md:
          - "Phase 1d: VLM Vision"          → default fallback
          - "Phase 1d: VLM Vision (Academic)" → academic papers
          - "Phase 1d: VLM Vision (Report)"   → reports / slides
          - "Phase 1d: VLM Vision (Manual)"   → instruction manuals
        """
        route = self._read_vlm_prompt_route(subject, pdf_id)
        route_map = {
            "academic": "Phase 1d: VLM Vision (Academic)",
            "report": "Phase 1d: VLM Vision (Report)",
            "manual": "Phase 1d: VLM Vision (Manual)",
        }
        prompt_key = route_map.get(route, "Phase 1d: VLM Vision")
        prompt = self.get_prompt(prompt_key)
        if not prompt:
            self.warning(f"⚠️ [Phase 1d] 找不到 prompt '{prompt_key}'，回退至預設版本")
            prompt = self.get_prompt("Phase 1d: VLM Vision")
        return prompt

    def _clean_markdown_text(self, text: str) -> str:
        """Escape tricky characters that break Markdown tables."""
        text = text.replace("\n", "<br>")
        text = text.replace("|", "\\|")
        return text

    def run(self, subject: str, filename: str) -> bool:
        """
        Execute VLM Vision analysis on the PDF's figures.

        Args:
            subject: The subject category folder name.
            filename: The PDF filename.

        Returns:
            bool: True if successful, False if failed.
        """
        pdf_id = os.path.splitext(filename)[0]
        self.info(f"👁️ [Phase 1d] 啟動 VLM 視覺圖表解析: {pdf_id}")

        try:
            pdf_dir = os.path.join(self.dirs.get("processed", ""), subject, pdf_id)
            figure_list_path = os.path.join(pdf_dir, "figure_list.md")

            if not os.path.exists(figure_list_path):
                self.warning("⚠️ [Phase 1d] 找不到 figure_list.md，略過。")
                return True

            with open(figure_list_path, encoding="utf-8") as f:
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
                return False

            try:
                filename_col = headers.index("檔案名稱")
                vlm_col = headers.index("VLM 描述")
            except ValueError:
                self.error("❌ figure_list.md 缺少必要的 '檔案名稱' 或 'VLM 描述' 欄位。")
                return False

            prompt = self._get_adaptive_vlm_prompt(subject, pdf_id)
            if not prompt:
                self.error("❌ 找不到 Phase 1d 的 prompt 指令，請確認 prompt.md 內有對應的段落。")
                return False

            pending_tasks = []
            for i in range(header_idx + 2, len(lines)):
                line = lines[i].strip()
                if not line.startswith("|") or not line.endswith("|"):
                    continue

                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) != len(headers):
                    continue

                if "待 VLM 描述" in cols[vlm_col]:
                    rel_img_path = cols[filename_col]
                    abs_img_path = os.path.join(pdf_dir, rel_img_path)

                    if not os.path.exists(abs_img_path):
                        self.warning(f"⚠️ 找不到實體圖片檔案: {abs_img_path}")
                        cols[vlm_col] = "圖片遺失"
                        lines[i] = "| " + " | ".join(cols) + " |\n"
                    else:
                        b64_image = encode_image_b64(abs_img_path)
                        pending_tasks.append((i, rel_img_path, cols, b64_image))
                elif "已略過" in cols[vlm_col] or "Caption" in cols[vlm_col]:
                    # Native caption found in Phase 1a — skip VLM entirely
                    self.info(f"⏭️  [Phase 1d] 已有 Caption，略過 VLM: {cols[filename_col]}")

            modifications = 0
            if pending_tasks:
                self.info(f"🔍 準備併發解析 {len(pending_tasks)} 張圖片...")
                import asyncio

                # async_batch_generate does not natively accept multiple images arrays out of the box in the signature,
                # Wait, looking at async_batch_generate, it takes a single `images` list for ALL prompts?
                # Let's write a small wrapper here for concurrent execution.

                async def _process_img(idx, rel_path, cols_list, b64_img):
                    try:
                        res = await self.llm.async_generate(
                            model=self.vlm_model,
                            prompt=prompt,
                            images=[b64_img],
                            options=self.vlm_options,
                            logger=self,
                        )
                        safe_res = self._clean_markdown_text(res.strip())
                        cols_list[vlm_col] = safe_res
                        self.info(f"✅ 解析完成 ({rel_path}): {safe_res[:20]}...")
                        return idx, cols_list
                    except Exception as e:
                        self.error(f"❌ VLM 解析失敗 ({rel_path}): {e}")
                        cols_list[vlm_col] = f"[錯誤] {self._clean_markdown_text(str(e))}"
                        return idx, cols_list

                async def _run_all():
                    semaphore = asyncio.Semaphore(
                        2
                    )  # Max 2 concurrent VLM requests to avoid VRAM OOM

                    async def _bounded_process(*args):
                        async with semaphore:
                            return await _process_img(*args)

                    tasks = [
                        _bounded_process(i, rel, cols, b64) for i, rel, cols, b64 in pending_tasks
                    ]
                    return await asyncio.gather(*tasks)

                results = asyncio.run(_run_all())

                for idx, new_cols in results:
                    lines[idx] = "| " + " | ".join(new_cols) + " |\n"
                    modifications += 1

            if modifications > 0:
                AtomicWriter.write_text(figure_list_path, "".join(lines))
                self.info(f"💾 [Phase 1d] 成功更新了 {modifications} 張圖片的描述至 figure_list.md")
            else:
                self.info("🆗 [Phase 1d] 沒有需要解析的新圖片。")

            return True
        finally:
            self.llm.unload_model(self.vlm_model, logger=self)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="The PDF path")
    args = parser.parse_args()

    filename = os.path.basename(args.pdf)
    phase = Phase1dVLMVision()
    success = phase.run("Default", filename)
    print(f"Success: {success}")
