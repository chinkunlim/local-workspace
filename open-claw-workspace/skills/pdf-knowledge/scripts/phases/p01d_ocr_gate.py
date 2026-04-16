# -*- coding: utf-8 -*-
"""
ocr_quality_gate.py — Phase 1d: OCR 品質評估
============================================
對掃描件頁面執行 per-word 信心分數評估（pytesseract），
精確定位哪些段落有 OCR 問題，並在 content.md 插入警告標記。

設計決策：[D019] — DECISIONS_v2.1.md
- pytesseract.image_to_data() per-word 分數比 Docling 整頁判斷更細緻
- 200 DPI（比 150 DPI 繁中 OCR 準確率高 15-20%）
- 門檻 0.80：低於此值觸發黃色警告，不中斷流程

依賴：
  pip install pytesseract pillow
  brew install tesseract tesseract-lang
  （繁中語言包: tesseract-lang 已含 chi_tra）
"""

import os
import sys
import gc
import json
import subprocess
import tempfile
from typing import List, Dict, Optional

import os, sys
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../..")))

from core.pipeline_base import PipelineBase

# OCR settings are required from config.yaml.
DEFAULT_CONFIDENCE_THRESHOLD = None
DEFAULT_OCR_DPI = None
DEFAULT_OCR_LANG = None


class Phase1dOCRQualityGate(PipelineBase):
    """
    Phase 1d: OCR Quality Assessment.
    Evaluates per-word confidence scores for scanned PDF pages.
    """

    def __init__(self):
        super().__init__(
            phase_key="phase1d",
            phase_name="OCR 品質評估",
            skill_name="pdf-knowledge",
        )
        # Utilizing canonical self.dirs from PipelineBase
        ocr_cfg = self.config_manager.get_nested("pdf_processing", "ocr") or {}
        self.dpi = ocr_cfg.get("dpi")
        self.lang = ocr_cfg.get("lang")
        self.threshold = ocr_cfg.get("confidence_threshold")
        if self.dpi is None or self.lang is None or self.threshold is None:
            raise RuntimeError("pdf-knowledge config missing pdf_processing.ocr.dpi/lang/confidence_threshold")

    # ------------------------------------------------------------------ #
    #  Public Entry Point                                                  #
    # ------------------------------------------------------------------ #

    def assess_all_scanned_pages(
        self, pdf_path: str, pdf_id: str, scanned_pages: Optional[List[int]] = None
    ) -> Dict[int, float]:
        """
        Assess OCR quality for all scanned pages.

        Args:
            pdf_path: Path to PDF.
            pdf_id: PDF identifier.
            scanned_pages: List of page numbers to assess. If None, reads from scan_report.json.

        Returns:
            Dict mapping page_number → confidence_score (0.0-1.0)
        """
        if scanned_pages is None:
            scanned_pages = self._get_scanned_pages_from_report(pdf_id)

        if not scanned_pages:
            self.info("📋 [OCR] 無掃描頁面需要品質評估")
            return {}

        self.info(f"🔤 [OCR] 開始評估 {len(scanned_pages)} 個掃描頁面...")

        page_scores: Dict[int, float] = {}
        low_confidence_pages: List[int] = []

        for page_num in scanned_pages:
            if self.check_system_health():
                break

            score = self.assess_page_ocr_quality(pdf_path, page_num)
            page_scores[page_num] = score

            status = "✅" if score >= self.threshold else "⚠️"
            self.info(f"🔤 [OCR] 頁面 {page_num}: {score:.0%} {status}")

            if score < self.threshold:
                low_confidence_pages.append(page_num)

        # Update scan_report.json
        self._update_scan_report(pdf_id, page_scores, low_confidence_pages)

        if low_confidence_pages:
            self.warning(
                f"⚠️ [OCR] {len(low_confidence_pages)} 頁信心值低於 {self.threshold:.0%}: "
                f"{low_confidence_pages}"
            )
        else:
            self.info(f"✅ [OCR] 所有頁面信心值 ≥ {self.threshold:.0%}")

        gc.collect()
        return page_scores

    def assess_page_ocr_quality(self, pdf_path: str, page_num: int) -> float:
        """
        Assess OCR quality for a single page.

        Steps:
          1. Rasterize page with pdftoppm (200 DPI for best chi_tra accuracy)
          2. Run pytesseract.image_to_data() for per-word confidence
          3. Return mean confidence score (0.0-1.0)

        Returns 0.0 on failure (will trigger warning).
        """
        try:
            import pytesseract
            from PIL import Image
            from pytesseract import Output
        except ImportError as e:
            self.warning(f"⚠️ [OCR] 缺少套件 {e}。請安裝: pip install pytesseract pillow")
            return 0.0

        # Rasterize
        img_path = self._rasterize_page(pdf_path, page_num)
        if not img_path:
            return 0.0

        try:
            img = Image.open(img_path)
            data = pytesseract.image_to_data(
                img,
                output_type=Output.DICT,
                lang=self.lang,
            )
            scores = [c / 100.0 for c in data["conf"] if isinstance(c, (int, float)) and int(c) > 0]
            return sum(scores) / len(scores) if scores else 0.0
        except Exception as e:
            self.warning(f"⚠️ [OCR] 頁面 {page_num} 評估失敗: {e}")
            return 0.0
        finally:
            # Clean up temp file
            if img_path and os.path.exists(img_path):
                os.unlink(img_path)

    # ------------------------------------------------------------------ #
    #  Rasterization                                                       #
    # ------------------------------------------------------------------ #

    def _rasterize_page(self, pdf_path: str, page_num: int) -> Optional[str]:
        """Rasterize a single page to a temp PNG file using pdftoppm."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = os.path.join(tmpdir, f"ocr_p{page_num}")
            cmd = [
                "pdftoppm",
                "-png",
                "-r", str(self.dpi),
                "-f", str(page_num),
                "-l", str(page_num),
                pdf_path,
                prefix,
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                self.warning(f"⚠️ pdftoppm 失敗 (頁面 {page_num}): {e}")
                return None

            import glob as glob_mod
            files = sorted(glob_mod.glob(f"{prefix}-*.png"))
            if not files:
                return None

            # Copy to a named temp file (tmpdir will be deleted on exit)
            import shutil
            dest = tempfile.mktemp(suffix=f"_p{page_num}.png")
            shutil.copy(files[0], dest)
            return dest

    # ------------------------------------------------------------------ #
    #  Output                                                              #
    # ------------------------------------------------------------------ #

    def _get_scanned_pages_from_report(self, pdf_id: str) -> List[int]:
        """Read scanned page list from scan_report.json."""
        report_path = os.path.join(self.dirs["processed"], subject, pdf_id, "scan_report.json")
        if not os.path.exists(report_path):
            return []
        try:
            with open(report_path) as f:
                data = json.load(f)
            # If the whole doc is scanned, assess all pages; otherwise check specific pages
            if data.get("is_scanned", False):
                pages = data.get("pages", 0)
                return list(range(1, pages + 1))
            return []
        except Exception:
            return []

    def _update_scan_report(
        self,
        pdf_id: str,
        page_scores: Dict[int, float],
        low_confidence_pages: List[int],
    ):
        """Update scan_report.json with OCR assessment results."""
        report_path = os.path.join(self.dirs["processed"], subject, pdf_id, "scan_report.json")
        try:
            data = {}
            if os.path.exists(report_path):
                with open(report_path) as f:
                    data = json.load(f)

            data["low_confidence_pages"] = low_confidence_pages
            data["ocr_page_scores"] = {str(k): round(v, 4) for k, v in page_scores.items()}
            data["ocr_threshold"] = self.threshold
            data["ocr_dpi"] = self.dpi
            data["ocr_lang"] = self.lang

            from core import AtomicWriter
            AtomicWriter.write_json(report_path, data)

            self.info(f"💾 [OCR] scan_report.json 已更新 (low_confidence_pages: {low_confidence_pages})")
        except Exception as e:
            self.warning(f"⚠️ [OCR] 無法更新 scan_report.json: {e}")

    @staticmethod
    def format_ocr_warning(page_num: int, score: float) -> str:
        """
        Generate the OCR warning markdown to insert into content.md.
        Called by pdf_engine.py when inserting content for low-confidence pages.
        """
        return f"> ⚠️ **[OCR品質警告]** 此段文字提取信心值 {score:.0%}（第 {page_num} 頁），建議對照原始 PDF 頁面核實。\n"


# ---------------------------------------------------------------------------- #
#  CLI Entry Point                                                              #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1d: OCR Quality Gate")
    parser.add_argument("pdf", help="Path to PDF")
    parser.add_argument("--id", dest="pdf_id", default=None)
    parser.add_argument("--pages", nargs="+", type=int, default=None,
                        help="Specific pages to assess (default: auto from scan_report.json)")
    args = parser.parse_args()

    pdf_id = args.pdf_id or os.path.splitext(os.path.basename(args.pdf))[0]
    gate = Phase1dOCRQualityGate()
    scores = gate.assess_all_scanned_pages(args.pdf, pdf_id, args.pages)

    print(f"\n{'=' * 40}")
    print("OCR Quality Assessment Results")
    print(f"{'=' * 40}")
    for page, score in sorted(scores.items()):
        status = "✅" if score >= gate.threshold else "⚠️ LOW"
        print(f"  Page {page:3d}: {score:.0%} {status}")
