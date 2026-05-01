"""
queue_manager.py — Phase 0: 串行 PDF 佇列管理
============================================
管理 input/ → output/01_processed/ 的 PDF 處理佇列：
- 串行處理（ModelMutex：Docling 和 Playwright 不同時執行）
- `check_system_health()` 前置（RAM/Disk/Temp 防禦）
- 首次啟動設定引導（Chrome Profile 路徑確認）
- 三層去重（已完成 / 佇列中 / MD5 hash）

設計原則：
- 所有邏輯讀自 config.yaml（零硬編碼）
- 中斷後重啟自動從 resume_state.json 繼續
"""

from datetime import datetime
from enum import Enum
import hashlib
import json
import os
import sys
import threading
from typing import Dict, List, Optional

# Internal Core Bootstrap

# Temporary path injection just to reach core/bootstrap.py from skills/doc_parser/scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import build_skill_parser
from core.orchestration.pipeline_base import PipelineBase
from core.state.resume_manager import ResumeManager


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

    def __init__(
        self,
        force_mode: bool = False,
        subject_filter: str = None,
        file_filter: str = None,
        single_mode: bool = False,
    ):
        super().__init__(
            phase_key="phase0",
            phase_name="佇列管理",
            skill_name="doc_parser",
        )
        self.force_mode = force_mode
        self.subject_filter = subject_filter
        self.file_filter = file_filter
        self.single_mode = single_mode
        # Utilizing canonical self.dirs from PipelineBase
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
        print("=" * 50)
        print("✈️  進行啟動前置檢查 (Preflight Check)...")

        # 1. Ensure inbox exists
        os.makedirs(self.dirs["inbox"], exist_ok=True)
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)

        # 2. Check poppler-utils
        import subprocess

        try:
            subprocess.run(["pdfinfo", "--version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            self.error("❌ poppler-utils 未安裝！請執行: brew install poppler")
            return False

        # 3. Chrome Profile confirmation (config check)
        playwright_cfg = self.config_manager.get_section("playwright", {})
        profile = playwright_cfg.get("chrome_profile", "")

        if not profile or "limchinkun" not in profile:
            self.warning(
                "⚠️ Chrome Profile 路徑尚未設定！\n"
                "   請在 skills/doc_parser/config/config.yaml 中填寫:\n"
                '   playwright.chrome_profile: "<your Chrome profile path>"'
            )

        # 4. Check for interrupted sessions
        interrupted = self.resume_manager.get_all_interrupted()
        if interrupted:
            self.info(f"📌 偵測到 {len(interrupted)} 個未完成的 PDF：{list(interrupted.keys())}")

        # 5. System health baseline
        if self.check_system_health():
            self.error("❌ 系統資源不足，請稍後再試")
            return False

        print("✅ 前置檢查通過。\n")

        # Sync inbox state to generate initial checklist.md
        self.state_manager.sync_physical_files()
        return True

    # ------------------------------------------------------------------ #
    #  Queue Building                                                      #
    # ------------------------------------------------------------------ #

    def scan_inbox(self) -> List[Dict]:
        """
        Scan input/ for PDF files and build the processing queue.
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
        for root, dirs, files in os.walk(inbox_dir):
            for filename in sorted(files):
                if not filename.lower().endswith(".pdf"):
                    continue

                pdf_path = os.path.join(root, filename)
                pdf_id = os.path.splitext(filename)[0]

                # Resolve subject from directory structure relative to inbox_dir
                rel_path = os.path.relpath(root, inbox_dir)
                subject = "Default" if rel_path == "." else rel_path.replace(os.sep, "_")

                # Layer 1: Check if already processed
                is_completed = self._is_already_processed(pdf_id, subject)
                if not self.force_mode and is_completed:
                    status = PDFStatus.COMPLETED.value
                else:
                    status = PDFStatus.PENDING.value

                # Layer 2: Check if already in queue
                if any(item["pdf_id"] == pdf_id for item in self._queue):
                    continue

                # Layer 3: MD5 hash dedup
                pdf_hash = self._md5(pdf_path)
                if (
                    status == PDFStatus.PENDING.value
                    and not self.force_mode
                    and pdf_hash in self._processed_hashes
                ):
                    status = PDFStatus.COMPLETED.value

                # Check for encryption
                is_encrypted = self._quick_check_encrypted(pdf_path)

                new_pdfs.append(
                    {
                        "pdf_id": pdf_id,
                        "subject": subject,
                        "pdf_path": pdf_path,
                        "filename": filename,
                        "md5": pdf_hash,
                        "status": status,
                        "added_at": datetime.now().isoformat(),
                        "encrypted": is_encrypted,
                    }
                )

        # 1. Subject Filter Enforcement
        if self.subject_filter:
            new_pdfs = [p for p in new_pdfs if p["subject"] == self.subject_filter]

        # 2. Sort explicitly to ensure ascending alphabetical execution
        new_pdfs.sort(key=lambda t: (t["subject"], t["filename"]))

        # 3. Targeted execution scope slice
        if self.file_filter:
            start_idx = 0
            found = False
            for i, p in enumerate(new_pdfs):
                if p["filename"] == self.file_filter:
                    start_idx = i
                    found = True
                    break

            if not found:
                self.log(
                    f"⚠️  --file 指定的檔案 '{self.file_filter}' 不在未處理清單中，將掃描全部 Inbox。",
                    "warn",
                )
            elif self.single_mode:
                new_pdfs = [new_pdfs[start_idx]]
                self.log(f"🎯  單檔模式：僅抽出 [{new_pdfs[0]['subject']}] {self.file_filter}")
            else:
                new_pdfs = new_pdfs[start_idx:]
                if start_idx > 0:
                    self.log(
                        f"➩️  指定起點：從 {self.file_filter} 之後開始處理（共計 {len(new_pdfs)} 項）。"
                    )

        self._queue.extend(new_pdfs)
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
        subject = item.get("subject", "Default")

        self.info(f"🔄 [Queue] 開始處理: [{subject}] {item['filename']}")
        item["status"] = PDFStatus.PROCESSING.value
        item["started_at"] = datetime.now().isoformat()

        # System health check before heavy processing
        if self.check_system_health():
            item["status"] = PDFStatus.PENDING.value  # Return to queue
            return None

        try:
            # --- Phase 0a: Diagnostic ---
            if self.force_mode or not self._is_already_processed(pdf_id, subject, phase_key="p0a"):
                self.info(f"📋 [Queue] Phase 0a: 輕量診斷 ({subject})...")
                from phases.p00a_diagnostic import Phase0aDiagnostic

                success = Phase0aDiagnostic().run(subject, item["filename"])

                if not success:
                    raise RuntimeError("Phase 0a 診斷失敗")
                self.state_manager.update_task(subject, item["filename"], "p0a", "✅")
            else:
                self.info("📋 [Queue] Phase 0a 已完成，載入快取")
                from phases.p00a_diagnostic import DiagnosticReport

                report_path = os.path.join(
                    self.dirs["processed"], subject, pdf_id, "scan_report.json"
                )
                if os.path.exists(report_path):
                    with open(report_path, encoding="utf-8") as f:
                        import json

                        scan_report = DiagnosticReport(**json.load(f))
                else:
                    raise RuntimeError("Phase 0a 完成但找不到 scan_report.json")

            # --- Phase 1a: Docling Extraction ---
            if self.force_mode or not self._is_already_processed(pdf_id, subject, phase_key="p1a"):
                if not self.model_mutex.acquire_docling():
                    self.warning("⚠️ [Queue] Playwright 執行中，Docling 等待...")
                    while self.model_mutex._playwright_active:
                        import time

                        time.sleep(10)
                        if self.stop_requested:
                            return None
                    self.model_mutex.acquire_docling()

                try:
                    self.info(f"📄 [Queue] Phase 1a: Docling 提取 ({subject})...")
                    from phases.p01a_engine import Phase1aPDFEngine

                    success = Phase1aPDFEngine().run(subject, item["filename"])
                    if not success:
                        raise RuntimeError("Phase 1a Docling 提取失敗")
                    self.state_manager.update_task(subject, item["filename"], "p1a", "✅")
                finally:
                    self.model_mutex.release_docling()
            else:
                self.info("📄 [Queue] Phase 1a 已完成，跳過")

            # --- Phase 1b-S: Text Sanitizer (header/footer purge, hyphenation) ---
            # This runs AFTER the IMMUTABLE raw_extracted.md is written by Phase 1a.
            # It produces sanitized.md which downstream phases should prefer.
            self.info(f"🧼 [Queue] Phase 1b-S: 文字淨化 ({subject})...")
            from phases.p01b_text_sanitizer import Phase1bTextSanitizer

            Phase1bTextSanitizer().run(subject, item["filename"])
            self.state_manager.update_task(subject, item["filename"], "p1b_s", "✅")


            # --- Phase 1b: Vector Chart Extraction ---
            if self.force_mode or not self._is_already_processed(pdf_id, subject, phase_key="p1b"):
                # Always call run(), Phase 1b internally reads scan_report.json and skips if empty
                self.info(f"🎨 [Queue] Phase 1b: 向量圖表補充 ({subject})...")
                from phases.p01b_vector_charts import Phase1bVectorChartExtractor

                Phase1bVectorChartExtractor().run(subject, item["filename"])
                self.state_manager.update_task(subject, item["filename"], "p1b", "✅")
            else:
                self.info("🎨 [Queue] Phase 1b 已完成，跳過")

            # --- Phase 1c: OCR Quality (if scanned) ---
            if self.force_mode or not self._is_already_processed(pdf_id, subject, phase_key="p1c"):
                # Phase 1c internally reads scan_report.json and skips if not scanned
                self.info(f"🔤 [Queue] Phase 1c: OCR 品質評估 ({subject})...")
                from phases.p01c_ocr_gate import Phase1cOCRQualityGate

                Phase1cOCRQualityGate().run(subject, item["filename"])
                self.state_manager.update_task(subject, item["filename"], "p1c", "✅")
            else:
                self.info("🔤 [Queue] Phase 1c 已完成，跳過")

            # --- Phase 1d: VLM Vision ---
            if self.force_mode or not self._is_already_processed(pdf_id, subject, phase_key="p1d"):
                self.info(f"👁️ [Queue] Phase 1d: VLM 視覺圖表解析 ({subject})...")
                from phases.p01d_vlm_vision import Phase1dVLMVision

                Phase1dVLMVision().run(subject, item["filename"])
                self.state_manager.update_task(subject, item["filename"], "p1d", "✅")
            else:
                self.info("👁️ [Queue] Phase 1d 已完成，跳過")

            if getattr(self, "interactive", False):
                input("⏸️ [Interactive] Phase 1d 已完成。請確認 figure_list.md，按 Enter 繼續...")

            # Done
            item["status"] = PDFStatus.COMPLETED.value
            item["completed_at"] = datetime.now().isoformat()
            self._processed_hashes.add(item["md5"])
            self.state_manager.update_task(
                subject, item["filename"], "p1d", "✅", note_tag="Pipeline 全部完成"
            )
            self.info(f"✅ [Queue] {item['filename']} 處理完成")

        except Exception as e:
            self.error(f"❌ [Queue] {item['filename']} 失敗: {e}")
            item["status"] = PDFStatus.FAILED.value
            item["error"] = str(e)

            # Explicitly mark as failed in StateManager so it isn't re-queued
            self.state_manager.update_task(
                subject, item["filename"], "p1d", "❌", note_tag=f"處理失敗: {e}"
            )
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

    def _is_already_processed(
        self, pdf_id: str, subject: str = "Default", phase_key: str = None
    ) -> bool:
        """
        Check if pdf_id has completed processing via StateManager checklist.
        If phase_key is provided, checks if that specific phase is '✅'.
        If no phase_key is provided, checks if the final phase 'p3' is '✅'.
        """
        # We need the original filename which we can infer or pass, but StateManager
        # stores it by filename. To be exact, we should look up the task.
        # Since Queue relies on filename, we can search the state checklist for pdf_id.
        state = self.state_manager.state
        if subject not in state or not state[subject]:
            return False

        # Find the record matching this pdf_id
        record = None
        for fn, details in state[subject].items():
            if os.path.splitext(fn)[0] == pdf_id:
                record = details
                break

        if not record:
            return False

        if phase_key:
            return record.get(phase_key) in ("✅", "❌")

        # If no explicit phase requested, consider it processed if the final phase is success OR explicitly failed
        return record.get("p1d") in ("✅", "❌")

    def _load_processed_hashes(self):
        """Load MD5 hashes of already-processed PDFs from scan_reports."""
        processed_dir = self.dirs["processed"]
        if not os.path.exists(processed_dir):
            return
        for subject_dir in os.listdir(processed_dir):
            subject_path = os.path.join(processed_dir, subject_dir)
            if not os.path.isdir(subject_path):
                continue

            for pdf_id in os.listdir(subject_path):
                report_path = os.path.join(subject_path, pdf_id, "scan_report.json")
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
                ["pdfinfo", pdf_path], capture_output=True, text=True, timeout=10
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
    try:
        parser = build_skill_parser(
            "Doc Parser Queue Manager",
            include_force=True,
            include_resume=True,
            include_subject=True,
            include_process_all=True,
            include_interactive=True,
        )
        parser.add_argument("--scan", action="store_true", help="只掃描 Inbox，不處理")
        parser.add_argument("--process-one", action="store_true", help="只處理下一個 PDF")
        args = parser.parse_args()

        qm = QueueManager(
            force_mode=args.force,
            subject_filter=getattr(args, "subject", None),
            file_filter=getattr(args, "file", None),
            single_mode=getattr(args, "single", False),
        )
        qm.interactive = args.interactive

        if not qm.startup_check():
            sys.exit(1)

        qm.scan_inbox()

        if args.scan:
            qm.state_manager.print_dashboard()
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

        else:
            # 互動式選單 (當沒有帶入任何執行參數時)
            qm.state_manager.print_dashboard()

            # 處理「已完成」的 PDF（可選擇重跑）
            done_tasks = [i for i in qm._queue if i["status"] == PDFStatus.COMPLETED.value]
            if done_tasks:
                from core.cli.cli_menu import batch_select_tasks

                reprocess_dict = batch_select_tasks(done_tasks, header="已完成的 PDF (重跑選取)")
                if reprocess_dict:
                    # 將選中的任務標記為 PENDING
                    for item in reprocess_dict.values():
                        item["status"] = PDFStatus.PENDING.value

            # 處理「待處理」的 PDF
            pending = [i for i in qm._queue if i["status"] == PDFStatus.PENDING.value]
            if pending:
                from core.cli.cli_menu import batch_select_tasks

                chosen_dict = batch_select_tasks(pending, header="待處理的 PDF")
                if not chosen_dict:
                    print("\n已退出。")
                else:
                    # 覆寫佇列為所選的檔案
                    qm._queue = list(chosen_dict.values())
                    qm.process_all()
            else:
                print("\n📭 目前沒有需要處理的 PDF。")
        print("🏁 Pipeline 執行完畢。")
        try:
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Pipeline 執行完畢" with title "Open-Claw"',
                ],
                check=False,
            )
        except Exception:
            pass
    except KeyboardInterrupt:
        print("\n🛑 使用者手動中斷執行 (KeyboardInterrupt)")
        try:
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Execution Interrupted" with title "Open-Claw"',
                ],
                check=False,
            )
        except Exception:
            pass
        import sys

        sys.exit(130)
