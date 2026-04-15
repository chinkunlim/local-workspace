# -*- coding: utf-8 -*-
"""
queue_manager.py — Phase 0: 串行 PDF 佇列管理
============================================
管理 01_Inbox/ → 02_Processed/ 的 PDF 處理佇列：
- 串行處理（ModelMutex：Docling 和 Playwright 不同時執行）
- `check_system_health()` 前置（RAM/Disk/Temp 防禦）
- 首次啟動設定引導（Chrome Profile 路徑確認）
- 三層去重（已完成 / 佇列中 / MD5 hash）

設計原則：
- 所有邏輯讀自 config.yaml（零硬編碼）
- 中斷後重啟自動從 resume_state.json 繼續
"""

import os
import sys
import json
import hashlib
import time
import threading
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

# --- Boundary-Safe Initialization ---
_script_dir = os.path.dirname(os.path.abspath(__file__))
_skill_root = os.path.dirname(os.path.dirname(_script_dir))  # skills/pdf-knowledge
_openclawed_root = os.path.dirname(_skill_root)  # open-claw-workspace
_core_dir = os.path.abspath(os.path.join(_openclawed_root, "core"))
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.dirname(_openclawed_root)  # local-workspace
)

# Enforce sandbox boundary: only core and this skill
sys.path = [_core_dir, _script_dir]

from core.pipeline_base import PipelineBase
from core.resume_manager import ResumeManager
from core import build_skill_parser


class PDFStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED_DUPLICATE = "skipped_duplicate"


class ModelMutex:
    """
    Ensures Docling and Playwright never run simultaneously.
    Docling: ~2.5GB RAM
    Playwright + Gemma: ~3.3GB RAM combined
    Total available on 16GB: ~10GB (after OS/other processes)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._docling_active = False
        self._playwright_active = False

    def acquire_docling(self) -> bool:
        with self._lock:
            if self._playwright_active:
                return False  # Cannot start Docling while Playwright is running
            self._docling_active = True
            return True

    def release_docling(self):
        with self._lock:
            self._docling_active = False

    def acquire_playwright(self) -> bool:
        with self._lock:
            if self._docling_active:
                return False  # Cannot start Playwright while Docling is running
            self._playwright_active = True
            return True

    def release_playwright(self):
        with self._lock:
            self._playwright_active = False

    @property
    def is_busy(self) -> bool:
        return self._docling_active or self._playwright_active


class QueueManager(PipelineBase):
    """
    PDF processing queue manager.
    Orchestrates the full pipeline: Phase 1a → 1b → 1c → 1d → (later phases).
    """

    def __init__(self):
        super().__init__(
            phase_key="phase0",
            phase_name="佇列管理",
            skill_name="pdf-knowledge",
        )
        self.dirs = {
            "inbox": os.path.join(self.base_dir, "01_Inbox"),
            "processed": os.path.join(self.base_dir, "02_Processed"),
            "agent_core": os.path.join(self.base_dir, "03_Agent_Core"),
            "error": os.path.join(self.base_dir, "Error"),
        }
        self.resume_manager = ResumeManager(self.base_dir)
        self.model_mutex = ModelMutex()
        self._queue: List[Dict] = []
        self._processed_hashes: set = set()

    # ------------------------------------------------------------------ #
    #  Startup                                                             #
    # ------------------------------------------------------------------ #

    def startup_check(self) -> bool:
        """
        Preflight checks before starting the queue:
        1. Chrome Profile path confirmation (first run)
        2. poppler-utils availability
        3. Resume detection
        4. System health baseline

        Returns True if safe to proceed.
        """
        self.info("🔍 [Queue] 執行啟動前置檢查...")

        # 1. Ensure inbox exists
        os.makedirs(self.dirs["inbox"], exist_ok=True)
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)

        # 2. Check poppler-utils
        import subprocess
        try:
            subprocess.run(["pdfinfo", "--version"], capture_output=True, timeout=5)
            self.info("✅ [Queue] poppler-utils 可用")
        except FileNotFoundError:
            self.error("❌ [Queue] poppler-utils 未安裝！請執行: brew install poppler")
            return False

        # 3. Chrome Profile confirmation (config check)
        playwright_cfg = self.config_manager.get_section("playwright", {})
        profile = playwright_cfg.get("chrome_profile", "")
        hint = playwright_cfg.get("account_hint", "（未設定）")

        if not profile or "limchinkun" not in profile:
            self.warning(
                "⚠️ [Queue] Chrome Profile 路徑尚未設定！\n"
                "   請在 skills/pdf-knowledge/config/config.yaml 中填寫:\n"
                    "   playwright.chrome_profile: \"<your Chrome profile path>\""
            )
            # Non-fatal: Phase 1a/1b/1c/1d can run without Playwright

        # 4. Check for interrupted sessions
        interrupted = self.resume_manager.get_all_interrupted()
        if interrupted:
            self.info(f"📌 [Queue] 偵測到 {len(interrupted)} 個未完成的 PDF：{list(interrupted.keys())}")

        # 5. System health baseline
        if self.check_system_health():
            self.error("❌ [Queue] 系統資源不足，請稍後再試")
            return False

        self.info("✅ [Queue] 啟動前置檢查通過")
        return True

    # ------------------------------------------------------------------ #
    #  Queue Building                                                      #
    # ------------------------------------------------------------------ #

    def scan_inbox(self) -> List[Dict]:
        """
        Scan 01_Inbox/ for PDF files and build the processing queue.
        Applies three-layer deduplication:
          Layer 1: Already in 02_Processed/ (by pdf_id)
          Layer 2: Already in current queue
          Layer 3: MD5 hash match with already-processed files
        """
        inbox_dir = self.dirs["inbox"]
        if not os.path.exists(inbox_dir):
            return []

        # Load known hashes
        self._load_processed_hashes()

        new_pdfs = []
        for filename in sorted(os.listdir(inbox_dir)):
            if not filename.lower().endswith(".pdf"):
                continue

            pdf_path = os.path.join(inbox_dir, filename)
            pdf_id = os.path.splitext(filename)[0]

            # Layer 1: Check if already processed
            if self._is_already_processed(pdf_id):
                self.info(f"⏭️ [Queue] {filename} 已完成，跳過")
                continue

            # Layer 2: Check if already in queue
            if any(item["pdf_id"] == pdf_id for item in self._queue):
                self.info(f"⏭️ [Queue] {filename} 已在佇列中，跳過")
                continue

            # Layer 3: MD5 hash dedup
            pdf_hash = self._md5(pdf_path)
            if pdf_hash in self._processed_hashes:
                self.info(f"⏭️ [Queue] {filename} 內容重複（MD5 相同），跳過")
                continue

            # Check for encryption
            is_encrypted = self._quick_check_encrypted(pdf_path)

            new_pdfs.append({
                "pdf_id": pdf_id,
                "pdf_path": pdf_path,
                "filename": filename,
                "md5": pdf_hash,
                "status": PDFStatus.PENDING.value,
                "added_at": datetime.now().isoformat(),
                "encrypted": is_encrypted,
            })

        self._queue.extend(new_pdfs)
        if new_pdfs:
            self.info(f"🔍 [Queue] 偵測到 {len(new_pdfs)} 個新 PDF")
        else:
            self.info("📭 [Queue] 01_Inbox/ 無新 PDF")

        return new_pdfs

    # ------------------------------------------------------------------ #
    #  Processing                                                          #
    # ------------------------------------------------------------------ #

    def process_next(self) -> Optional[Dict]:
        """
        Process the next pending PDF in the queue.
        Runs Phase 1a → 1b → 1c → 1d sequentially.

        Returns the processed item dict, or None if queue is empty.
        """
        pending = [item for item in self._queue if item["status"] == PDFStatus.PENDING.value]
        if not pending:
            return None

        item = pending[0]
        pdf_id = item["pdf_id"]
        pdf_path = item["pdf_path"]

        self.info(f"🔄 [Queue] 開始處理: {item['filename']}")
        item["status"] = PDFStatus.PROCESSING.value
        item["started_at"] = datetime.now().isoformat()

        # System health check before heavy processing
        if self.check_system_health():
            item["status"] = PDFStatus.PENDING.value  # Return to queue
            return None

        try:
            # --- Phase 1a: Diagnostic ---
            self.info(f"📋 [Queue] Phase 1a: 輕量診斷...")
            from pdf_diagnostic import Phase1aDiagnostic
            diag = Phase1aDiagnostic()
            scan_report = diag.run_diagnostics(pdf_path, pdf_id)

            if not scan_report.success:
                raise RuntimeError(f"Phase 1a 失敗: {scan_report.error}")

            # Acquire Docling mutex
            if not self.model_mutex.acquire_docling():
                self.warning("⚠️ [Queue] Playwright 執行中，Docling 等待...")
                while self.model_mutex._playwright_active:
                    time.sleep(10)
                    if self.stop_requested:
                        return None
                self.model_mutex.acquire_docling()

            # --- Phase 1b: Docling Extraction ---
            try:
                self.info(f"📄 [Queue] Phase 1b: Docling 提取...")
                from pdf_engine import Phase1bPDFEngine
                engine = Phase1bPDFEngine()
                raw_path = engine.extract(pdf_path, pdf_id)
                if raw_path is None:
                    raise RuntimeError("Phase 1b Docling 提取失敗")
            finally:
                self.model_mutex.release_docling()

            # --- Phase 1c: Vector Chart Extraction ---
            vector_pages = scan_report.vector_chart_pages
            if vector_pages:
                self.info(f"🎨 [Queue] Phase 1c: 向量圖表光柵化 ({len(vector_pages)} 頁)...")
                from vector_chart_extractor import Phase1cVectorChartExtractor
                extractor = Phase1cVectorChartExtractor()
                extractor.extract_vector_charts(pdf_path, pdf_id, vector_pages)

            # --- Phase 1d: OCR Quality (if scanned) ---
            if scan_report.is_scanned:
                self.info(f"🔤 [Queue] Phase 1d: OCR 品質評估...")
                from ocr_quality_gate import Phase1dOCRQualityGate
                gate = Phase1dOCRQualityGate()
                gate.assess_all_scanned_pages(pdf_path, pdf_id)

            # Done
            item["status"] = PDFStatus.COMPLETED.value
            item["completed_at"] = datetime.now().isoformat()
            self._processed_hashes.add(item["md5"])
            self.info(f"✅ [Queue] {item['filename']} 處理完成")

        except Exception as e:
            self.error(f"❌ [Queue] {item['filename']} 失敗: {e}")
            item["status"] = PDFStatus.FAILED.value
            item["error"] = str(e)
        finally:
            self.model_mutex.release_docling()  # Safety release

        return item

    def process_all(self):
        """Process all pending PDFs in queue until empty or interrupted."""
        while True:
            if self.check_system_health() or self.stop_requested:
                break

            # Re-scan inbox for new PDFs
            self.scan_inbox()

            pending = [i for i in self._queue if i["status"] == PDFStatus.PENDING.value]
            if not pending:
                self.info("✅ [Queue] 佇列處理完畢")
                break

            self.process_next()

    # ------------------------------------------------------------------ #
    #  Utilities                                                           #
    # ------------------------------------------------------------------ #

    def _is_already_processed(self, pdf_id: str) -> bool:
        """Check if pdf_id has raw_extracted.md in 02_Processed/."""
        raw_path = os.path.join(self.dirs["processed"], pdf_id, "raw_extracted.md")
        return os.path.exists(raw_path)

    def _load_processed_hashes(self):
        """Load MD5 hashes of already-processed PDFs from scan_reports."""
        processed_dir = self.dirs["processed"]
        if not os.path.exists(processed_dir):
            return
        for pdf_id in os.listdir(processed_dir):
            report_path = os.path.join(processed_dir, pdf_id, "scan_report.json")
            if os.path.exists(report_path):
                try:
                    with open(report_path) as f:
                        data = json.load(f)
                    h = data.get("md5")
                    if h:
                        self._processed_hashes.add(h)
                except Exception:
                    pass

    def _quick_check_encrypted(self, pdf_path: str) -> bool:
        """Quick encryption check using pdfinfo."""
        import subprocess
        try:
            result = subprocess.run(
                ["pdfinfo", pdf_path],
                capture_output=True, text=True, timeout=10
            )
            return "encrypted: yes" in result.stdout.lower()
        except Exception:
            return False

    @staticmethod
    def _md5(path: str) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                h.update(block)
        return h.hexdigest()


# ---------------------------------------------------------------------------- #
#  CLI Entry Point                                                              #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    parser = build_skill_parser("PDF Knowledge Queue Manager")
    parser.add_argument("--scan", action="store_true", help="只掃描 Inbox，不處理")
    parser.add_argument("--process-all", action="store_true", help="處理所有待辦 PDF")
    parser.add_argument("--process-one", action="store_true", help="只處理下一個 PDF")
    args = parser.parse_args()

    qm = QueueManager()

    if not qm.startup_check():
        sys.exit(1)

    qm.scan_inbox()

    if args.scan:
        print(f"\n佇列狀態: {len(qm._queue)} 個 PDF")
        for item in qm._queue:
            print(f"  {item['status']:10s} {item['filename']}")

    elif args.process_one:
        result = qm.process_next()
        if result:
            print(f"\n✅ 已處理: {result['filename']} ({result['status']})")
        else:
            print("\n📭 佇列為空")

    elif args.process_all:
        qm.process_all()
