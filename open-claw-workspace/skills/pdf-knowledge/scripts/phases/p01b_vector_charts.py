# -*- coding: utf-8 -*-
"""
vector_chart_extractor.py — Phase 1b: 向量圖表補充
===================================================
對 Phase 0a 診斷標記的向量圖頁面執行 pdftoppm 光柵化，
確保 matplotlib/Excel/R 等工具生成的統計圖不被遺漏。

設計決策：[D018] — DECISIONS_v2.1.md
pdfimages 只能提取 raster（點陣）圖片，向量圖表完全不在其列。
解決方案：對這些頁面執行 pdftoppm（150 DPI，JPEG），
存入 assets/fig_p{n}_vector.jpg，
並在 figure_list.md 標記 type="vector_rasterized"。

依賴：poppler-utils（brew install poppler）
"""

import os
import sys
import glob
import shutil
import json
import subprocess
from typing import List, Dict, Optional

# Internal Core Bootstrap
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

from core.pipeline_base import PipelineBase


class Phase1bVectorChartExtractor(PipelineBase):
    """
    Phase 1b: Vector Chart Rasterization.
    Rasterizes vector-chart pages identified by Phase 0a diagnostic.
    """

    def __init__(self) -> None:
        super().__init__(
            phase_key="phase1b",
            phase_name="向量圖表補充",
            skill_name="pdf-knowledge",
        )
        # Utilizing canonical self.dirs from PipelineBase
        vc = self.config_manager.get_nested("pdf_processing", "vector_chart") or {}
        self.dpi = vc.get("dpi")
        self.fmt = vc.get("format")
        if self.dpi is None or self.fmt is None:
            raise RuntimeError("pdf-knowledge config missing pdf_processing.vector_chart.dpi or format")

    # ------------------------------------------------------------------ #
    #  Public Entry Point                                                  #
    # ------------------------------------------------------------------ #

    def run(self, subject: str, filename: str) -> bool:
        """
        Rasterize vector-chart pages and add them to figure_list.md.
        Automatically loads scan_report.json to discover vector_chart_pages.

        Args:
            subject: The subject category folder name.
            filename: The PDF filename.

        Returns:
            bool: True if successful, False if failed.
        """
        pdf_path = os.path.join(self.dirs.get("inbox", ""), subject, filename)
        pdf_id = os.path.splitext(filename)[0]
        
        # Load scan_report.json
        scan_report_path = os.path.join(self.dirs.get("processed", ""), subject, pdf_id, "scan_report.json")
        if not os.path.exists(scan_report_path):
            self.error(f"❌ [VectorChart] 無法找到診斷報告: {scan_report_path}")
            return False
            
        with open(scan_report_path, "r", encoding="utf-8") as f:
            scan_report = json.load(f)
            
        page_nums = scan_report.get("vector_chart_pages", [])
        if not page_nums:
            self.info("📋 [VectorChart] 無向量圖表頁面需要處理")
            return True

        processed_dir = os.path.join(self.dirs["processed"], subject, pdf_id)
        assets_dir = os.path.join(processed_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        self.info(f"🎨 [VectorChart] 光柵化向量圖表頁面: {page_nums}")
        extracted = []

        for page_num in page_nums:
            if self.check_system_health():
                break
            result = self._rasterize_page(pdf_path, page_num, assets_dir)
            if result:
                extracted.append(result)
                self.info(f"✅ [VectorChart] 頁面 {page_num} → {result['src']}")
            else:
                self.warning(f"⚠️ [VectorChart] 頁面 {page_num} 光柵化失敗")

        # Update figure_list.md
        if extracted:
            self._update_figure_list(processed_dir, extracted)

        self.info(f"🎨 [VectorChart] 完成: {len(extracted)}/{len(page_nums)} 頁")
        return True

    # ------------------------------------------------------------------ #
    #  Rasterization                                                       #
    # ------------------------------------------------------------------ #

    def _rasterize_page(
        self,
        pdf_path: str,
        page_num: int,
        assets_dir: str,
    ) -> Optional[Dict[str, str]]:
        """
        Rasterize a single page using pdftoppm.

        Returns dict with {page, src, type} or None on failure.
        """
        tmp_prefix = f"/tmp/openclaw_vec_p{page_num}"

        cmd = [
            "pdftoppm",
            f"-{self.fmt}",
            "-r", str(self.dpi),
            "-f", str(page_num),
            "-l", str(page_num),
            pdf_path,
            tmp_prefix,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.error(f"❌ pdftoppm 失敗 (頁面 {page_num}): {e}")
            return None

        # pdftoppm outputs files like: /tmp/prefix-001.jpg
        ext = "jpg" if self.fmt == "jpeg" else self.fmt
        output_files = sorted(glob.glob(f"{tmp_prefix}-*.{ext}"))
        if not output_files:
            self.warning(f"⚠️ pdftoppm 無輸出 (頁面 {page_num})")
            return None

        dest_filename = f"fig_p{page_num}_vector.{ext}"
        dest_path = os.path.join(assets_dir, dest_filename)
        shutil.move(output_files[0], dest_path)

        return {
            "page": page_num,
            "src": os.path.join("assets", dest_filename),
            "type": "vector_rasterized",
            "dpi": self.dpi,
        }

    # ------------------------------------------------------------------ #
    #  figure_list.md Update                                               #
    # ------------------------------------------------------------------ #

    def _update_figure_list(self, processed_dir: str, extracted: List[Dict]) -> None:
        """
        Append extracted vector charts to figure_list.md.
        Creates the file if it doesn't exist.

        Table format mirrors CLAUDE_v2.1.md specification.
        """
        figure_list_path = os.path.join(processed_dir, "figure_list.md")

        # Read existing entries
        existing = ""
        if os.path.exists(figure_list_path):
            with open(figure_list_path, "r", encoding="utf-8") as f:
                existing = f.read()

        new_rows = []
        for entry in extracted:
            page = entry["page"]
            src = entry["src"]
            row = (
                f"| {src} | {page} | (向量圖表 — 自動光柵化) "
                f"| 待 VLM 描述 | - | [V] |"
            )
            new_rows.append(row)

        from core import AtomicWriter
        content = []
        if not existing.strip():
            content.append("# Figure List\n\n")
            content.append("> 自動生成。[P] = raster 圖片，[V] = 向量圖表光柵化\n\n")
            content.append("| 檔案名稱 | 頁碼 | 原始 Caption | VLM 描述 | 數據趨勢標籤 | 來源 |\n")
            content.append("| :--- | :---: | :--- | :--- | :---: | :---: |\n")
        else:
            content.append(existing.rstrip() + "\n")

        for row in new_rows:
            content.append(row + "\n")

        AtomicWriter.write_text(figure_list_path, "".join(content))

        self.info(f"📄 [VectorChart] figure_list.md 已更新 (+{len(new_rows)} 筆)")


# ---------------------------------------------------------------------------- #
#  CLI Entry Point                                                              #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 1b: Vector Chart Extractor"
    )
    parser.add_argument("pdf", help="Path to PDF")
    parser.add_argument("--id", dest="pdf_id", default=None)
    parser.add_argument("--pages", nargs="+", type=int, default=[],
                        help="Page numbers to rasterize (1-indexed)")
    parser.add_argument("--from-report", dest="from_report", action="store_true",
                        help="Read vector_chart_pages from existing scan_report.json")
    args = parser.parse_args()

    pdf_id = args.pdf_id or os.path.splitext(os.path.basename(args.pdf))[0]
    extractor = Phase1bVectorChartExtractor()

    page_nums = args.pages
    if args.from_report:
        report_path = os.path.join(
            extractor.dirs["processed"], pdf_id, "scan_report.json"
        )
        if os.path.exists(report_path):
            with open(report_path) as f:
                data = json.load(f)
            page_nums = data.get("vector_chart_pages", [])
            print(f"📋 從 scan_report.json 讀取向量圖表頁面: {page_nums}")
        else:
            print(f"❌ scan_report.json 不存在: {report_path}")
            sys.exit(1)

    results = extractor.extract_vector_charts(args.pdf, pdf_id, page_nums)
    print(f"\n✅ 完成: {len(results)} 張向量圖表已光柵化")
    for r in results:
        print(f"  頁面 {r['page']} → {r['src']}")
