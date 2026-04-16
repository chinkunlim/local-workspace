# -*- coding: utf-8 -*-
"""
pdf_engine.py — Phase 1b: Docling 深度提取
==========================================
在 Phase 1a 診斷通過後，使用 Docling（IBM）執行完整的 PDF 結構提取：
- 文字（含 Layout Analysis，處理多欄）
- 表格（pdfplumber）
- raster 圖片（PyMuPDF / fitz）
- 參考文獻（reference_injector.py，後續 phase）

Phase 1b 設計決策：
- Docling 完成後立即 gc.collect()（釋放 ~2.5GB 記憶體）
- 字型損壞 fallback：Docling + pdftoppm OCR 交叉驗證，差異 > 20% 以 OCR 為主
- raw_extracted.md 永遠 IMMUTABLE（任何 AI 不得修改）

依賴：
  pip install docling pymupdf pdfplumber
"""

import os
import sys
import gc
import json
import hashlib
import shutil
from typing import Optional, Dict

import os, sys
# Workspace Root Resolver
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../..")))

from core.pipeline_base import PipelineBase
from core.resume_manager import ResumeManager


class Phase1bPDFEngine(PipelineBase):
    """
    Phase 1b: Docling Deep Extraction.
    Reads scan_report.json from Phase 1a to adapt processing strategy.
    """

    # Font fallback threshold is defined in config.yaml.
    FONT_FALLBACK_DIFF_THRESHOLD = None

    def __init__(self):
        super().__init__(
            phase_key="phase1b",
            phase_name="Docling 深度提取",
            skill_name="pdf-knowledge",
        )
        # Utilizing canonical self.dirs from PipelineBase
        self.resume_manager = ResumeManager(self.base_dir)
        docling_cfg = self.config_manager.get_nested("pdf_processing", "docling") or {}
        self.gc_collect_after = docling_cfg.get("gc_collect_after")
        self.font_diff_threshold = docling_cfg.get("font_fallback_diff_threshold")
        if self.gc_collect_after is None:
            raise RuntimeError("pdf-knowledge config missing pdf_processing.docling.gc_collect_after")
        if self.font_diff_threshold is None:
            raise RuntimeError("pdf-knowledge config missing pdf_processing.docling.font_fallback_diff_threshold")

    # ------------------------------------------------------------------ #
    #  Public Entry Point                                                  #
    # ------------------------------------------------------------------ #

    def extract(self, pdf_path: str, pdf_id: str, subject: str = "Default") -> Optional[str]:
        """
        Execute full PDF extraction pipeline.

        Steps:
          1. Load scan_report.json from Phase 1a
          2. Check early-exit conditions (encrypted, 0 pages)
          3. Run Docling extraction
          4. Apply font-broken fallback (if needed)
          5. Apply terminology protection (Layer 1 substitutions)
          6. Write IMMUTABLE raw_extracted.md
          7. gc.collect()

        Args:
            pdf_path: Absolute path to PDF.
            pdf_id: PDF identifier.

        Returns:
            Path to raw_extracted.md, or None on failure.
        """
        self.info(f"📄 [Phase 1b] 開始 Docling 提取: {pdf_id}")

        # Load diagnostic report
        scan_report = self._load_scan_report(pdf_id, subject)
        if scan_report is None:
            self.warning("⚠️ [Phase 1b] 找不到 scan_report.json，建議先執行 Phase 1a 診斷")
            scan_report = {}

        # Early exit checks
        if scan_report.get("encrypted") and not self._try_empty_password(pdf_path):
            self._move_to_error(pdf_path, pdf_id, "加密 PDF，空密碼解密失敗")
            return None

        if scan_report.get("pages", 1) == 0:
            self._move_to_error(pdf_path, pdf_id, "PDF 頁數為 0，可能損壞")
            return None

        # Set up output directory
        output_dir = os.path.join(self.dirs["processed"], subject, pdf_id)
        os.makedirs(output_dir, exist_ok=True)
        raw_output_path = os.path.join(output_dir, "raw_extracted.md")

        # Save checkpoint before heavy operation
        self.resume_manager.save_checkpoint(pdf_id, "phase1b", chunk_index=0)

        try:
            # Run Docling
            extracted_text = self._run_docling(pdf_path, pdf_id, subject)

            if extracted_text is None:
                self._move_to_error(pdf_path, pdf_id, "Docling 提取失敗")
                return None

            # Font-broken fallback
            if scan_report.get("has_broken_fonts"):
                extracted_text = self._apply_font_fallback(
                    pdf_path, pdf_id, extracted_text, scan_report
                )

            # Terminology protection — Layer 1 substitutions
            extracted_text = self._apply_terminology_protection(extracted_text)

            # Write IMMUTABLE raw_extracted.md
            from core import AtomicWriter
            AtomicWriter.write_text(
                raw_output_path,
                (
                    "<!-- raw_extracted.md — IMMUTABLE — DO NOT MODIFY —\n"
                    f"     pdf_id: {pdf_id}\n"
                    f"     source: {os.path.basename(pdf_path)}\n"
                    f"     pages: {scan_report.get('pages', '?')}\n"
                    "-->\n\n"
                    f"{extracted_text}"
                ),
            )

            # Record SHA-256 hash
            file_hash = self._sha256(raw_output_path)
            self._update_scan_report(pdf_id, subject, {
                "raw_extracted_hash": file_hash,
                "raw_extracted_chars": len(extracted_text),
                "phase1b_status": "completed",
            })

            self.info(f"✅ [Phase 1b] raw_extracted.md 已寫入 ({len(extracted_text):,} 字元, hash: {file_hash[:8]}...)")
            self.resume_manager.clear_checkpoint(pdf_id)
            return raw_output_path

        except MemoryError:
            self.error("💥 [Phase 1b] Docling 記憶體耗盡，移至 Error/")
            self._move_to_error(pdf_path, pdf_id, "MemoryError during Docling extraction")
            return None
        except Exception as e:
            self.error(f"❌ [Phase 1b] 提取失敗: {e}")
            return None
        finally:
            if self.gc_collect_after:
                gc.collect()
                self.info("🧹 [Phase 1b] gc.collect() 完成，記憶體已釋放")

    # ------------------------------------------------------------------ #
    #  Docling                                                             #
    # ------------------------------------------------------------------ #

    def _run_docling(self, pdf_path: str, pdf_id: str, subject: str) -> Optional[str]:
        """Run Docling PDF extraction. Returns markdown text or None."""
        
        # Sandbox HuggingFace models to project directory
        model_dir = os.path.join(_openclawed_root, "models")
        os.makedirs(model_dir, exist_ok=True)
        os.environ["HF_HOME"] = model_dir
        os.environ["HF_HUB_CACHE"] = model_dir
        
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.datamodel.document import PictureItem
        except ImportError:
            self.error("❌ Docling 未安裝。請執行: pip install docling")
            return None

        self.info("📄 [Phase 1b] Docling 載入中（~2.5GB RAM，請稍候...）")

        # Create output directory for Docling intermediate files
        docling_output = os.path.join(self.dirs["processed"], subject, pdf_id, "_docling_tmp")
        os.makedirs(docling_output, exist_ok=True)
        
        # Setup specific assets directory for image extraction
        assets_dir = os.path.join(self.dirs["processed"], subject, pdf_id, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        try:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.generate_picture_images = True
            
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            result = converter.convert(pdf_path)
            doc = result.document
            
            # Extract images and build figure list database
            extracted_figures = []
            for item, level in doc.iterate_items():
                if isinstance(item, PictureItem):
                    img = item.get_image(doc)
                    if img:
                        page_no = item.prov[0].page_no if getattr(item, "prov", None) else 1
                        filename = f"fig_p{page_no}_{item.self_ref.replace('/', '_')}.png"
                        filepath = os.path.join(assets_dir, filename)
                        img.save(filepath)
                        
                        extracted_figures.append({
                            "page": page_no,
                            "src": f"assets/{filename}",
                            "type": "picture"
                        })
            
            # Write figure_list.md if figures were found
            if extracted_figures:
                figure_list_path = os.path.join(self.dirs["processed"], subject, pdf_id, "figure_list.md")
                content = [
                    "# Figure List\n\n",
                    "> 自動生成。[P] = raster 圖片，[V] = 向量圖表光柵化\n\n",
                    "| 檔案名稱 | 頁碼 | 原始 Caption | VLM 描述 | 數據趨勢標籤 | 來源 |\n",
                    "| :--- | :---: | :--- | :--- | :---: | :---: |\n"
                ]
                
                for fig in extracted_figures:
                    row = f"| {fig['src']} | {fig['page']} | - | 待 VLM 描述 | - | [P] |"
                    content.append(row + "\n")
                    
                from core import AtomicWriter
                AtomicWriter.write_text(figure_list_path, "".join(content))
                self.info(f"📸 [Phase 1b] 提取了 {len(extracted_figures)} 張圖片並建立 figure_list.md")

            markdown_text = doc.export_to_markdown()
            self.info(f"✅ [Phase 1b] Docling 提取完成 ({len(markdown_text):,} 字元)")
            return markdown_text
        except Exception as e:
            self.error(f"❌ [Phase 1b] Docling 失敗: {e}")
            return None
        finally:
            # Clean up Docling temp files
            if os.path.exists(docling_output):
                shutil.rmtree(docling_output, ignore_errors=True)

    # ------------------------------------------------------------------ #
    #  Font Fallback                                                       #
    # ------------------------------------------------------------------ #

    def _apply_font_fallback(
        self,
        pdf_path: str,
        pdf_id: str,
        docling_text: str,
        scan_report: dict,
    ) -> str:
        """
        For PDFs with broken fonts: cross-validate Docling text with OCR.
        If difference > threshold (20%), use OCR result.

        Returns the best available text.
        """
        self.warning("⚠️ [Phase 1b] 字型損壞偵測，啟動 OCR 交叉驗證...")

        import subprocess
        import tempfile

        try:
            # Run pdftotext as OCR baseline
            result = subprocess.run(
                ["pdftotext", "-layout", pdf_path, "-"],
                capture_output=True, text=True, timeout=120
            )
            ocr_text = result.stdout
        except Exception as e:
            self.warning(f"⚠️ pdftotext fallback 失敗: {e}")
            return docling_text

        # Compare text lengths as proxy for extraction quality
        docling_len = len(docling_text.replace(" ", "").replace("\n", ""))
        ocr_len = len(ocr_text.replace(" ", "").replace("\n", ""))

        if ocr_len == 0:
            return docling_text

        diff_ratio = abs(docling_len - ocr_len) / max(docling_len, ocr_len)

        # Update scan report with fallback info
        font_fallback_pages = scan_report.get("font_issues", [])
        self._update_scan_report(pdf_id, {
            "font_fallback_applied": diff_ratio > self.font_diff_threshold,
            "font_fallback_diff_ratio": round(diff_ratio, 4),
        })

        if diff_ratio > self.font_diff_threshold:
            self.warning(
                f"⚠️ [Phase 1b] Docling vs OCR 文字長度差異 {diff_ratio:.0%} > {self.font_diff_threshold:.0%}，"
                f"改用 OCR 結果（{ocr_len:,} 字元）"
            )
            return ocr_text
        else:
            self.info(
                f"✅ [Phase 1b] Docling 結果可信（差異 {diff_ratio:.0%} ≤ {self.font_diff_threshold:.0%}），保留 Docling 輸出"
            )
            return docling_text

    # ------------------------------------------------------------------ #
    #  Terminology Protection (Layer 1)                                    #
    # ------------------------------------------------------------------ #

    def _apply_terminology_protection(self, text: str) -> str:
        """
        Apply Layer 1 terminology protection: string substitutions from
        priority_terms.json CRITICAL_SUBSTITUTIONS.
        """
        terms_path = os.path.join(
            _workspace_root, "skills", "pdf-knowledge", "config", "priority_terms.json"
        )
        if not os.path.exists(terms_path):
            return text

        try:
            with open(terms_path, encoding="utf-8") as f:
                terms = json.load(f)

            substitutions = terms.get("CRITICAL_SUBSTITUTIONS", {})
            count = 0
            for wrong, correct in substitutions.items():
                if wrong.startswith("_"):  # Skip comment keys
                    continue
                occurrences = text.count(wrong)
                if occurrences > 0:
                    text = text.replace(wrong, correct)
                    count += occurrences

            if count > 0:
                self.info(f"🛡️ [Terms] priority_terms 強制替換: {count} 處修正")
        except Exception as e:
            self.warning(f"⚠️ [Terms] priority_terms.json 讀取失敗: {e}")

        return text

    # ------------------------------------------------------------------ #
    #  Utilities                                                           #
    # ------------------------------------------------------------------ #

    def _load_scan_report(self, pdf_id: str, subject: str) -> Optional[Dict]:
        """Load scan_report.json from Phase 1a."""
        path = os.path.join(self.dirs["processed"], subject, pdf_id, "scan_report.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None

    def _update_scan_report(self, pdf_id: str, subject: str, updates: dict):
        """Merge additional keys into scan_report.json."""
        path = os.path.join(self.dirs["processed"], subject, pdf_id, "scan_report.json")
        data = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception:
                pass
        data.update(updates)
        from core import AtomicWriter
        AtomicWriter.write_json(path, data)

    def _move_to_error(self, pdf_path: str, pdf_id: str, reason: str):
        """Move PDF to Error/ directory with error metadata."""
        error_dir = self.dirs["error"]
        os.makedirs(error_dir, exist_ok=True)

        dest = os.path.join(error_dir, os.path.basename(pdf_path))
        try:
            shutil.move(pdf_path, dest)
        except Exception:
            pass

        error_meta = os.path.join(error_dir, f"{pdf_id}_error.json")
        from core import AtomicWriter
        AtomicWriter.write_json(error_meta, {"pdf_id": pdf_id, "reason": reason})

        self.error(f"❌ [Phase 1b] {pdf_id} 已移至 Error/ — {reason}")

    @staticmethod
    def _try_empty_password(pdf_path: str) -> bool:
        """Check if encrypted PDF can be opened with empty password."""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            if doc.is_encrypted:
                return doc.authenticate("")
            return True
        except Exception:
            return False

    @staticmethod
    def _sha256(path: str) -> str:
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha.update(block)
        return sha.hexdigest()


# ---------------------------------------------------------------------------- #
#  CLI Entry Point                                                              #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1b: Docling PDF Extraction")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--id", dest="pdf_id", default=None)
    args = parser.parse_args()

    pdf_id = args.pdf_id or os.path.splitext(os.path.basename(args.pdf))[0]
    engine = Phase1bPDFEngine()
    result = engine.extract(args.pdf, pdf_id)

    if result:
        print(f"\n✅ 提取完成: {result}")
    else:
        print(f"\n❌ 提取失敗（查看 Error/ 目錄）")
        sys.exit(1)
