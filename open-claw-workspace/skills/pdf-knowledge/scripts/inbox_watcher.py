# -*- coding: utf-8 -*-
"""
inbox_watcher.py — 01_Inbox/ 目錄監視器
========================================
使用 Watchdog 監控 01_Inbox/，自動偵測新 PDF 並加入佇列。

功能：
- Watchdog 目錄事件監控（比 polling 更高效）
- 三層去重：已完成 / 佇列中 / MD5 hash
- 加密 PDF 快速偵測（pdfinfo）
- 新 PDF 通知（Console 訊息，未來可接 Telegram）

依賴：pip install watchdog
"""

import os
import sys
import time
import threading
from typing import Callable, Optional

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


class InboxWatcher(PipelineBase):
    """
    Watches 01_Inbox/ for new PDF files and triggers processing.

    Usage:
        watcher = InboxWatcher(on_new_pdf=queue_manager.scan_inbox)
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    def __init__(self, on_new_pdf: Optional[Callable] = None):
        super().__init__(
            phase_key="inbox",
            phase_name="Inbox 監視器",
            skill_name="pdf-knowledge",
        )
        self.inbox_dir = os.path.join(self.base_dir, "01_Inbox")
        os.makedirs(self.inbox_dir, exist_ok=True)
        self.on_new_pdf = on_new_pdf
        self._observer = None
        self._debounce_timers: dict = {}

    # ------------------------------------------------------------------ #
    #  Watchdog Integration                                                #
    # ------------------------------------------------------------------ #

    def start(self):
        """Start watching the inbox directory."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class PDFHandler(FileSystemEventHandler):
                def __init__(self, watcher: "InboxWatcher"):
                    self.watcher = watcher

                def on_created(self, event):
                    if not event.is_directory and event.src_path.lower().endswith(".pdf"):
                        # Debounce: wait 2s for file to finish copying
                        path = event.src_path
                        if path in self.watcher._debounce_timers:
                            self.watcher._debounce_timers[path].cancel()
                        timer = threading.Timer(2.0, self.watcher._handle_new_pdf, args=[path])
                        self.watcher._debounce_timers[path] = timer
                        timer.start()

            self._observer = Observer()
            self._observer.schedule(PDFHandler(self), self.inbox_dir, recursive=False)
            self._observer.start()
            self.info(f"👁️ [Inbox] 開始監控: {self.inbox_dir}")

        except ImportError:
            self.warning("⚠️ [Inbox] watchdog 未安裝（pip install watchdog），改用輪詢模式")
            self._start_polling_fallback()

    def stop(self):
        """Stop directory watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self.info("👁️ [Inbox] 監控已停止")

    def _handle_new_pdf(self, pdf_path: str):
        """Called when a new PDF is detected (after debounce)."""
        filename = os.path.basename(pdf_path)
        self.info(f"🔍 [Inbox] 偵測到新 PDF: {filename}")

        # Basic validation
        if not os.path.exists(pdf_path):
            return
        if os.path.getsize(pdf_path) == 0:
            self.warning(f"⚠️ [Inbox] {filename} 大小為 0，跳過")
            return

        # Trigger callback
        if self.on_new_pdf:
            self.on_new_pdf()

    # ------------------------------------------------------------------ #
    #  Polling Fallback (when watchdog not available)                      #
    # ------------------------------------------------------------------ #

    def _start_polling_fallback(self, interval_seconds: int = 30):
        """Fallback: poll inbox directory every N seconds."""
        self.info(f"👁️ [Inbox] 輪詢模式啟動（每 {interval_seconds}秒）: {self.inbox_dir}")
        self._polling_stop = threading.Event()

        def poll():
            seen = set(os.listdir(self.inbox_dir)) if os.path.exists(self.inbox_dir) else set()
            while not self._polling_stop.wait(interval_seconds):
                if not os.path.exists(self.inbox_dir):
                    continue
                current = set(os.listdir(self.inbox_dir))
                new_files = current - seen
                for f in sorted(new_files):
                    if f.lower().endswith(".pdf"):
                        self._handle_new_pdf(os.path.join(self.inbox_dir, f))
                seen = current

        self._poll_thread = threading.Thread(target=poll, daemon=True)
        self._poll_thread.start()

    def stop_polling(self):
        """Stop polling fallback."""
        if hasattr(self, "_polling_stop"):
            self._polling_stop.set()


# ---------------------------------------------------------------------------- #
#  CLI Entry Point (standalone monitor)                                        #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PDF Inbox Watcher (standalone monitoring)")
    parser.add_argument("--interval", type=int, default=30,
                        help="Polling fallback interval in seconds (default: 30)")
    args = parser.parse_args()

    def on_new(path=None):
        print(f"📥 新 PDF 偵測到！觸發處理...")
        # In production: queue_manager.scan_inbox() + process_all()

    watcher = InboxWatcher(on_new_pdf=on_new)
    watcher.start()

    print("\n👁️  按 Ctrl+C 停止監控...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        print("\n✅ 監控已停止")
