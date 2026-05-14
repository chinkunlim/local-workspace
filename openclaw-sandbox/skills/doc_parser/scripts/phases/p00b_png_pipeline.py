"""
p00b_png_pipeline.py — Phase 0b: Dedicated PNG/JPG Extraction
=============================================================
Parallel entry point for parsing image-based course materials (.png, .jpg).

Process:
1. Validate image (dimensions, size)
2. Tesseract OCR (chi_tra+eng)
3. VLM fallback (`llama3.2-vision`) if Tesseract confidence < 0.75
4. Write `<png_id>_raw_extracted.md`
5. Copy original image to `assets/<png_id>.png` for figure embedding
"""

import os
import shutil
import sys
from typing import Optional, Tuple

from PIL import Image
import pytesseract

# Temporary path injection just to reach core/bootstrap.py from skills/doc_parser/scripts/phases
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core.ai.llm_client import OllamaClient
from core.orchestration.pipeline_base import PipelineBase
from core.state.resume_manager import ResumeManager
from core.utils.atomic_writer import AtomicWriter
from core.utils.file_utils import encode_image_b64


class Phase0bPNGPipeline(PipelineBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="p0b",
            phase_name="PNG/JPG 直接提取",
            skill_name="doc_parser",
        )
        self.resume_manager = ResumeManager(self.base_dir)

        cfg = self.config_manager.get_nested("phase0b_png") or {}
        self.vlm_model = cfg.get("vlm_model", "llama3.2-vision")
        self.ocr_confidence_threshold = float(cfg.get("ocr_confidence_threshold", 75.0))
        self.tesseract_lang = cfg.get("tesseract_lang", "chi_tra+eng")

        self.llm = OllamaClient(api_url="http://localhost:11434/api/generate")

    def run(
        self,
        force: bool = False,
        subject: str = None,
        file_filter: str = None,
        single_mode: bool = False,
        resume_from: str = None,
    ):
        """
        Execute PNG extraction pipeline across all pending tasks horizontally.
        """
        self.process_tasks(
            self._process_file,
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )

    def _process_file(self, idx: int, task: dict, total: int) -> Optional[bool]:
        subject = task["subject"]
        filename = task["filename"]
        img_path = os.path.join(self.dirs.get("inbox", ""), subject, filename)
        img_id = os.path.splitext(filename)[0]
        ext = os.path.splitext(filename)[1].lower()

        self.info(f"🖼️  [Phase 0b] 開始處理圖片課件: {filename}")

        # 1. Validation
        if not os.path.exists(img_path):
            self.error(f"❌ 找不到圖片檔案: {img_path}")
            self.state_manager.update_task(
                subject, filename, self.phase_key, "❌", note_tag="FileNotFound"
            )
            return False

        file_size_mb = os.path.getsize(img_path) / (1024 * 1024)
        if file_size_mb > 20:
            msg = f"檔案過大 ({file_size_mb:.1f}MB > 20MB)"
            self._move_to_error(img_path, img_id, msg)
            self.state_manager.update_task(subject, filename, self.phase_key, "❌", note_tag=msg)
            return False

        try:
            with Image.open(img_path) as img:
                w, h = img.size
                short_edge = min(w, h)
                # Validation logic: log warning but don't strictly fail on resolution
                if short_edge < 800:
                    self.warning(f"⚠️ 圖片解析度偏低 ({w}x{h})，可能影響辨識品質")
        except Exception as e:
            self._move_to_error(img_path, img_id, f"圖片無法開啟: {e}")
            self.state_manager.update_task(
                subject, filename, self.phase_key, "❌", note_tag=f"圖片無法開啟: {e}"
            )
            return False

        output_dir = os.path.join(self.dirs["processed"], subject, img_id)
        os.makedirs(output_dir, exist_ok=True)
        raw_output_path = os.path.join(output_dir, f"{img_id}_raw_extracted.md")

        # 2. Tesseract OCR
        self.info(f"🔍 [Phase 0b] 執行 Tesseract OCR ({self.tesseract_lang})")
        ocr_text, avg_confidence = self._run_tesseract(img_path)

        extracted_text = ""
        extraction_method = ""

        # 3. VLM Fallback
        if avg_confidence >= self.ocr_confidence_threshold and ocr_text.strip():
            self.info(
                f"✅ [Phase 0b] Tesseract 信心分 {avg_confidence:.1f} ≥ {self.ocr_confidence_threshold}，使用 OCR 結果"
            )
            extracted_text = ocr_text
            extraction_method = "Tesseract OCR"
        else:
            self.warning(
                f"⚠️ Tesseract 信心分 {avg_confidence:.1f} < {self.ocr_confidence_threshold}，啟動 VLM ({self.vlm_model})"
            )
            vlm_text = self._run_vlm(img_path)
            if vlm_text:
                extracted_text = vlm_text
                extraction_method = f"VLM ({self.vlm_model})"
                self.info("✅ [Phase 0b] VLM 提取完成")
            elif ocr_text.strip():
                self.warning("⚠️ VLM 提取失敗，退回使用低信心分的 OCR 結果")
                extracted_text = ocr_text
                extraction_method = "Tesseract OCR (Low Confidence Fallback)"
            else:
                self._move_to_error(img_path, img_id, "OCR 與 VLM 皆無法提取文字")
                self.state_manager.update_task(
                    subject, filename, self.phase_key, "❌", note_tag="OCR 與 VLM 皆無法提取文字"
                )
                return False

        # 4. Write Markdown
        AtomicWriter.write_text(
            raw_output_path,
            (
                f"<!-- {img_id}_raw_extracted.md — IMMUTABLE — DO NOT MODIFY —\n"
                f"     img_id: {img_id}\n"
                f"     source: {filename}\n"
                f"     method: {extraction_method}\n"
                "-->\n\n"
                f"{extracted_text}"
            ),
        )

        # 5. Copy original image to assets
        assets_dir = os.path.join(output_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        asset_path = os.path.join(assets_dir, f"{img_id}{ext}")
        shutil.copy2(img_path, asset_path)

        # Also create a dummy scan_report and figure_list so downstream p02 completeness check won't crash
        scan_report_path = os.path.join(output_dir, "scan_report.json")
        AtomicWriter.write_json(
            scan_report_path, {"is_image_only": True, "method": extraction_method}
        )

        # Create a single figure list entry representing the slide itself
        figure_list_path = os.path.join(output_dir, "figure_list.md")
        AtomicWriter.write_text(
            figure_list_path,
            (
                "# Figure List\n\n"
                "> 自動生成（圖片課件模式）。[I] = 原始投影片圖片\n\n"
                "| 檔案名稱 | 頁碼 | 原始 Caption | VLM 描述 | 數據趨勢標籤 | 來源 |\n"
                "| :--- | :---: | :--- | :--- | :---: | :---: |\n"
                f"| assets/{img_id}{ext} | 1 | - | - | - | [I] |\n"
            ),
        )

        self.info(f"✅ [Phase 0b] {filename} 處理完成，已寫入 raw_extracted.md 與 assets")
        self.state_manager.update_task(subject, filename, self.phase_key, "✅")

        from core.orchestration.event_bus import DomainEvent, EventBus

        EventBus.publish(
            DomainEvent(
                name="PipelineCompleted",
                source_skill="doc_parser",
                payload={"filepath": img_path, "subject": subject, "chain": []},
            )
        )
        return True

    def _run_tesseract(self, img_path: str) -> Tuple[str, float]:
        try:
            data = pytesseract.image_to_data(
                Image.open(img_path), lang=self.tesseract_lang, output_type=pytesseract.Output.DICT
            )
            text_blocks = []
            confidences = []

            for i in range(len(data["text"])):
                conf = float(data["conf"][i])
                text = data["text"][i].strip()
                if conf > 0 and text:
                    text_blocks.append(text)
                    confidences.append(conf)

            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            full_text = pytesseract.image_to_string(Image.open(img_path), lang=self.tesseract_lang)
            return full_text, avg_conf

        except Exception as e:
            self.error(f"Tesseract 執行錯誤: {e}")
            return "", 0.0

    def _run_vlm(self, img_path: str) -> Optional[str]:
        prompt = (
            "You are a document transcription assistant. "
            "Please extract ALL visible text from this image exactly as it appears. "
            "Follow the natural reading order. Preserve paragraphs and lists. "
            "If there are tables or diagrams, describe them or extract their text clearly. "
            "Output ONLY the extracted text, no introductory remarks."
        )
        try:
            # Ollama API requires base64-encoded image strings, not file paths
            b64_img = encode_image_b64(img_path)
            result = self.llm.generate(
                model=self.vlm_model, prompt=prompt, images=[b64_img], options={"temperature": 0.0}
            )
            self.llm.unload_model(self.vlm_model)
            return result
        except Exception as e:
            self.error(f"VLM 執行錯誤: {e}")
            return None

    def _move_to_error(self, file_path: str, file_id: str, reason: str):
        error_dir = self.dirs["error"]
        os.makedirs(error_dir, exist_ok=True)
        dest = os.path.join(error_dir, os.path.basename(file_path))
        try:
            shutil.move(file_path, dest)
        except Exception:
            pass
        error_meta = os.path.join(error_dir, f"{file_id}_error.json")
        AtomicWriter.write_json(error_meta, {"file_id": file_id, "reason": reason})
        self.error(f"❌ [Phase 0b] {file_id} 已移至 Error/ — {reason}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 0b: PNG/JPG Extraction")
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--subject", default="Default")
    args = parser.parse_args()

    engine = Phase0bPNGPipeline()
    result = engine.run(args.subject, os.path.basename(args.image))
    if result:
        print("\n✅ 提取完成")
    else:
        print("\n❌ 提取失敗")
        sys.exit(1)
