"""
pdf_diagnostic.py — Phase 0a: 輕量 PDF 診斷 + 文件意圖識別
=============================================
目標：在 Docling（~2.5GB RAM，3-5分鐘）啟動之前，
用 poppler-utils 在 < 50MB、< 5秒 內完成六項診斷：

  1. pdfinfo     → 頁數、版本、加密狀態
  2. pdftotext   → 首頁採樣（掃描偵測：< 50 字 → 掃描件）
  3. pdffonts    → 字型健康診斷（未嵌入 + Custom/Identity-H → 亂碼風險）
  4. pdfimages   → raster 圖片統計
  5. 向量圖偵測  → 有文字但 pdfimages 無圖的頁面 = 可能有向量圖 → 標記頁碼
  6. 多欄偵測    → pdftotext -layout 行寬分析
  7. 意圖識別   → LLM 分類文件類型（academic / report / manual / other），
                   自動選擇最佳 VLM Prompt 路由

結果寫入 scan_report.json，供所有後續 Phase 讀取。

依賴：poppler-utils（brew install poppler）
設計決策：[D017] — DECISIONS_v2.1.md
"""

from dataclasses import asdict, dataclass, field
import gc
import os
import re
import subprocess
from typing import List, Optional

# Internal Core Bootstrap
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core.orchestration.pipeline_base import PipelineBase
from core.utils.atomic_writer import AtomicWriter


@dataclass
class DiagnosticReport:
    """Structured diagnostic result for a single PDF."""

    pdf_path: str = ""
    pdf_id: str = ""
    subject: str = "Default"

    # pdfinfo
    pages: int = 0
    pdf_version: str = ""
    encrypted: bool = False
    pdf_type: str = "unknown"  # "digital" | "scanned" | "mixed"

    # pdftotext scan detect
    is_scanned: bool = False
    first_page_chars: int = 0

    # pdffonts
    has_broken_fonts: bool = False
    font_issues: List[str] = field(default_factory=list)

    # pdfimages
    has_raster_images: bool = False
    raster_image_count: int = 0

    # vector chart pages
    vector_chart_pages: List[int] = field(default_factory=list)

    # multi-column
    likely_multi_column: bool = False

    # downstream (filled by later phases)
    low_confidence_pages: List[int] = field(default_factory=list)

    # intent recognition (step 7)
    document_class: str = "unknown"  # "academic" | "report" | "manual" | "other"
    vlm_prompt_route: str = "default"  # key for VLM prompt selection

    # status
    error: Optional[str] = None
    success: bool = True


class Phase0aDiagnostic(PipelineBase):
    """
    Phase 0a: Lightweight PDF Diagnostic
    Inherits PipelineBase with skill_name='doc-parser' (V2.2 keyword arg pattern).
    """

    def __init__(self) -> None:
        super().__init__(
            phase_key="phase0a",
            phase_name="PDF 輕量診斷",
            skill_name="doc-parser",
        )
        # Utilizing canonical self.dirs from PipelineBase
        self.min_text_chars = self.config_manager.get_nested(
            "pdf_processing", "diagnostic", "min_text_chars_first_page"
        )
        if self.min_text_chars is None:
            raise RuntimeError(
                "doc-parser config missing pdf_processing.diagnostic.min_text_chars_first_page"
            )

    # ------------------------------------------------------------------ #
    #  Public Entry Point                                                  #
    # ------------------------------------------------------------------ #

    def run(self, subject: str, filename: str) -> bool:
        """
        Execute all six diagnostic checks.
        This is the main public API — call this before Docling.

        Args:
            subject: The subject category folder name.
            filename: The PDF filename (e.g., 'document.pdf').

        Returns:
            bool: True if successful, False if failed.
        """
        pdf_path = os.path.join(self.dirs.get("inbox", ""), subject, filename)
        pdf_id = os.path.splitext(filename)[0]
        report = DiagnosticReport(pdf_path=pdf_path, pdf_id=pdf_id, subject=subject)

        if not os.path.exists(pdf_path):
            report.error = f"PDF not found: {pdf_path}"
            report.success = False
            self.error(report.error)
            return False

        self.info(f"📋 [Diagnose] 開始診斷: [{subject}] {os.path.basename(pdf_path)}")

        try:
            # 1. pdfinfo
            self._run_pdfinfo(pdf_path, report)
            if report.encrypted:
                self.warning("⚠️ [Diagnose] PDF 已加密，嘗試空密碼...")
                # Note: actual decryption handled by pdf_engine.py

            # 2. pdftotext scan detection
            self._run_scan_detect(pdf_path, report)

            # 3. pdffonts health
            self._run_pdffonts(pdf_path, report)

            # 4. pdfimages raster count
            self._run_pdfimages(pdf_path, report)

            # 5. Vector chart page detection
            self._detect_vector_chart_pages(pdf_path, report)

            # 6. Multi-column detection
            self._detect_multi_column(pdf_path, report)

            # 7. Intent Recognition (LLM document classification)
            self._classify_intent(pdf_path, report)

        except Exception as e:
            report.error = str(e)
            report.success = False
            self.error(f"❌ [Diagnose] 診斷失敗: {e}")

        # Derive pdf_type
        if report.is_scanned:
            report.pdf_type = "scanned"
        elif report.has_broken_fonts:
            report.pdf_type = "mixed"
        else:
            report.pdf_type = "digital"

        # Write scan_report.json
        self._write_scan_report(report)
        self._log_summary(report)

        gc.collect()
        return report.success

    # ------------------------------------------------------------------ #
    #  Diagnostic Steps                                                    #
    # ------------------------------------------------------------------ #

    def _run_pdfinfo(self, pdf_path: str, report: DiagnosticReport):
        """Step 1: pdfinfo → pages, version, encryption."""
        result = self._run_tool(["pdfinfo", pdf_path])
        if result is None:
            raise RuntimeError(
                "pdfinfo failed — is poppler-utils installed? (brew install poppler)"
            )

        for line in result.splitlines():
            line = line.strip()
            if line.startswith("Pages:"):
                try:
                    report.pages = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("PDF version:"):
                report.pdf_version = line.split(":", 1)[1].strip()
            elif line.startswith("Encrypted:"):
                report.encrypted = "yes" in line.lower()

        if report.pages == 0:
            raise RuntimeError("pdfinfo returned 0 pages — PDF may be corrupt or empty.")
        self.info(
            f"📋 [Diagnose] pdfinfo: {report.pages} 頁, PDF {report.pdf_version}, 加密: {'是' if report.encrypted else '否'}"
        )

    def _run_scan_detect(self, pdf_path: str, report: DiagnosticReport):
        """Step 2: pdftotext first page sample for scan detection."""
        result = self._run_tool(["pdftotext", "-f", "1", "-l", "1", pdf_path, "-"])
        if result is None:
            result = ""
        report.first_page_chars = len(result.strip())
        report.is_scanned = report.first_page_chars < self.min_text_chars

        status = "掃描件 ⚠️" if report.is_scanned else "數位文字 ✅"
        self.info(f"📋 [Diagnose] 掃描偵測: {status} (首頁 {report.first_page_chars} 字元)")

    def _run_pdffonts(self, pdf_path: str, report: DiagnosticReport):
        """Step 3: pdffonts font health check."""
        result = self._run_tool(["pdffonts", pdf_path])
        if result is None:
            self.warning("⚠️ [Diagnose] pdffonts 無法執行，跳過字型診斷")
            return

        issues = []
        lines = result.splitlines()
        # Skip header (first 2 lines)
        for line in lines[2:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            # Column: name type encoding emb sub uni object-ID
            # emb is at index 3, encoding is at index 2
            # Format varies; detect by 'no' in emb column
            font_line = line
            emb_col = parts[3] if len(parts) > 3 else ""
            encoding_col = parts[2] if len(parts) > 2 else ""
            if emb_col.lower() == "no" and any(
                e in encoding_col for e in ["Custom", "Identity-H", "Identity-V"]
            ):
                font_name = parts[0] if parts[0] != "name" else "(unnamed)"
                issues.append(f"{font_name} [{encoding_col}] not embedded")

        report.has_broken_fonts = len(issues) > 0
        report.font_issues = issues[:10]  # Cap to 10

        if report.has_broken_fonts:
            self.warning(f"⚠️ [Diagnose] 偵測到未嵌入字型（{len(issues)} 個），文字提取可能產生亂碼")
        else:
            self.info("📋 [Diagnose] pdffonts: 字型健康 ✅")

    def _run_pdfimages(self, pdf_path: str, report: DiagnosticReport):
        """Step 4: pdfimages raster image count."""
        result = self._run_tool(["pdfimages", "-list", pdf_path])
        if result is None:
            self.warning("⚠️ [Diagnose] pdfimages 無法執行，跳過圖片統計")
            return

        lines = [
            l
            for l in result.splitlines()
            if l.strip() and not l.startswith("-") and not l.lower().startswith("page")
        ]
        report.raster_image_count = len(lines)
        report.has_raster_images = report.raster_image_count > 0

        self.info(f"📋 [Diagnose] pdfimages: {report.raster_image_count} 張 raster 圖片")

    def _detect_vector_chart_pages(self, pdf_path: str, report: DiagnosticReport):
        """
        Step 5: Vector chart detection.
        Pages with text but NO raster images = likely have vector charts.
        Strategy: check each page separately with pdftotext + pdfimages.
        """
        vector_pages = []
        # Only check up to 100 pages to avoid excessive time
        pages_to_check = min(report.pages, 100)

        for page_num in range(1, pages_to_check + 1):
            # Check if page has text
            page_text = self._run_tool(
                ["pdftotext", "-f", str(page_num), "-l", str(page_num), pdf_path, "-"]
            )
            page_has_text = page_text and len(page_text.strip()) > 20

            if not page_has_text:
                continue

            # Check if page has raster images
            page_imgs = self._run_tool(
                ["pdfimages", "-list", "-f", str(page_num), "-l", str(page_num), pdf_path]
            )
            page_img_lines = [
                l
                for l in (page_imgs or "").splitlines()
                if l.strip() and not l.startswith("-") and not l.lower().startswith("page")
            ]
            page_has_raster = len(page_img_lines) > 0

            # Text present but no raster → potential vector chart
            if not page_has_raster and re.search(
                r"(fig|figure|chart|graph|plot|diagram|table|圖|表)\s*\.?\s*\d",
                page_text or "",
                re.IGNORECASE,
            ):
                vector_pages.append(page_num)

        report.vector_chart_pages = vector_pages

        if vector_pages:
            self.info(f"📋 [Diagnose] 疑似向量圖表頁面: {vector_pages} ⚠️")
        else:
            self.info("📋 [Diagnose] 向量圖表: 未偵測到特殊頁面")

    def _detect_multi_column(self, pdf_path: str, report: DiagnosticReport):
        """
        Step 6: Multi-column detection via pdftotext -layout line width analysis.
        If > 30% of lines have length difference suggesting 2 columns → flag.
        """
        result = self._run_tool(["pdftotext", "-layout", "-f", "1", "-l", "5", pdf_path, "-"])
        if result is None:
            return

        lines = [l for l in result.splitlines() if l.strip()]
        if not lines:
            return

        lengths = [len(l) for l in lines]
        avg_len = sum(lengths) / len(lengths)
        # Lines significantly shorter than average suggest column breaks
        short_lines = sum(1 for l in lengths if l < avg_len * 0.6)
        multi_col_ratio = short_lines / len(lengths)

        report.likely_multi_column = multi_col_ratio > 0.30

        status = "疑似多欄 ⚠️" if report.likely_multi_column else "單欄 ✅"
        self.info(f"📋 [Diagnose] 多欄偵測: {status}")

    def _classify_intent(self, pdf_path: str, report: DiagnosticReport):
        """
        Step 7: LLM-based Document Intent Recognition.
        Analyzes the first 2 pages to classify document type and route VLM prompts.
        Document classes: academic | report | manual | other
        """
        # Extract first 2 pages text as context
        sample_text = self._run_tool(["pdftotext", "-f", "1", "-l", "2", pdf_path, "-"])
        if not sample_text or len(sample_text.strip()) < 50:
            self.info("📋 [Diagnose] 意圖識別: 文字內容不足，使用 default 路由")
            report.document_class = "other"
            report.vlm_prompt_route = "default"
            return

        sample = sample_text.strip()[:3000]
        intent_prompt = self.get_prompt("Phase 0a: Intent Recognition")
        if not intent_prompt:
            self.info("⚠️ [Diagnose] 找不到 Intent Recognition prompt，使用 default 路由")
            report.document_class = "other"
            report.vlm_prompt_route = "default"
            return

        model_name = (
            self.config_manager.get_nested("models", "diagnostic_classifier")
            or self.config_manager.get_nested("models", "default")
            or "qwen2.5-coder:7b"
        )

        prompt = f"{intent_prompt}\n\n【文件前兩頁摘要】:\n{sample}\n\n請只輸出分類結果（academic/report/manual/other），不要輸出任何解釋。"
        try:
            raw = self.llm.generate(model=model_name, prompt=prompt)
            doc_class = raw.strip().lower().split()[0] if raw.strip() else "other"
            if doc_class not in ("academic", "report", "manual", "other"):
                doc_class = "other"
            report.document_class = doc_class
            report.vlm_prompt_route = doc_class  # 1-to-1 mapping for now
            self.info(f"🧠 [Diagnose] 意圖識別完成: 文件類型 → [{doc_class}]")
        except Exception as e:
            self.warning(f"⚠️ [Diagnose] 意圖識別 LLM 呼叫失敗: {e}，使用 default 路由")
            report.document_class = "other"
            report.vlm_prompt_route = "default"
        finally:
            self.llm.unload_model(model_name, logger=self)

    # ------------------------------------------------------------------ #
    #  Output                                                              #
    # ------------------------------------------------------------------ #

    def _write_scan_report(self, report: DiagnosticReport):
        """Write diagnostic results to scan_report.json."""
        output_dir = os.path.join(self.dirs["processed"], report.subject, report.pdf_id)
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "scan_report.json")

        # Convert dataclass to dict, exclude internal fields
        report_dict = asdict(report)
        report_dict.pop("pdf_path", None)  # Don't export full path for security

        AtomicWriter.write_json(report_path, report_dict)

        self.info(f"💾 [Diagnose] scan_report.json 已寫入: {report_path}")

    def _log_summary(self, report: DiagnosticReport):
        """Log a human-readable diagnostic summary."""
        issues = []
        if report.encrypted:
            issues.append("🔒 加密")
        if report.is_scanned:
            issues.append("🖨️ 掃描件")
        if report.has_broken_fonts:
            issues.append(f"⚠️ 字型問題({len(report.font_issues)}個)")
        if report.vector_chart_pages:
            issues.append(f"📊 向量圖表({len(report.vector_chart_pages)}頁)")
        if report.likely_multi_column:
            issues.append("📄 多欄格式")

        summary = "無特殊問題 ✅" if not issues else " | ".join(issues)
        self.info(f"📋 [Diagnose] {report.pdf_id} 診斷完成 → {summary}")

    # ------------------------------------------------------------------ #
    #  Utilities                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _run_tool(cmd: List[str]) -> Optional[str]:
        """Run a CLI tool and return stdout, or None on failure."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None


# ---------------------------------------------------------------------------- #
#  CLI Entry Point                                                              #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 0a: PDF Lightweight Diagnostic (poppler-utils)"
    )
    parser.add_argument("pdf", help="Path to the PDF file to diagnose")
    parser.add_argument(
        "--id",
        dest="pdf_id",
        default=None,
        help="PDF identifier (default: filename without extension)",
    )
    args = parser.parse_args()

    pdf_id = args.pdf_id or os.path.splitext(os.path.basename(args.pdf))[0]
    filename = os.path.basename(args.pdf)

    diag = Phase0aDiagnostic()
    # Mock for CLI standalone run
    diag.dirs["inbox"] = os.path.dirname(os.path.abspath(args.pdf))
    success = diag.run("Default", filename)

    print(f"\n{'=' * 50}")
    print(f"Diagnostic Execution Success: {success}")
    print(f"{'=' * 50}")
