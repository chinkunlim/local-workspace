"""
inbox_daemon.py — Open Claw System-Wide Inbox Monitor
======================================================
Monitors the `inbox` canonical directories for all active skills using Watchdog.
When a new file arrives (e.g. .m4a for audio_transcriber, .pdf for doc_parser),
it triggers the target skill's pipeline via the WebUI API (with direct subprocess
fallback when the WebUI is not running).

Design:
  - Watches the global `data/raw` directory.
  - Routes files to specific skills based on extension (.m4a -> voice-memo, .pdf -> pdf-knowledge).
  - File stability via size-polling (2s interval) with 300s timeout guard.
  - Same-file debounce via threading.Event (cancellable).
"""

import json
import logging
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional

from core.cli.cli_runner import SkillRunner
from core.orchestration.router_agent import RouterAgent, TaskManifest
from core.orchestration.skill_registry import SkillRegistry
from core.orchestration.task_queue import task_queue

# Path Resolution
_core_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.dirname(_core_dir))
# Ensure workspace root is on sys.path so `from core.xxx` always resolves
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

from core.utils.atomic_writer import AtomicWriter

_logger = logging.getLogger("OpenClaw.InboxDaemon")
if not _logger.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S"))
    _logger.addHandler(_h)
    _logger.setLevel(logging.INFO)

# Constants
_WAIT_TIMEOUT_SEC = 300  # 5 min: abort if file never stabilises
_POLL_INTERVAL_SEC = 2.0


class SystemInboxDaemon:
    def __init__(self) -> None:
        self._observer: Optional[Any] = None
        self._debounce_events: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        # B-2 Fix: track files already dispatched to prevent dual-trigger
        self._seen_files: set = set()

        # Configure global raw path
        self.raw_path = os.path.join(_workspace_root, "data", "raw")
        os.makedirs(self.raw_path, exist_ok=True)

        # Initialize Registry and Router
        self.registry = SkillRegistry(os.path.join(_workspace_root, "skills"))
        self.registry.discover()
        self.router = RouterAgent(registry=self.registry)

        # Load Config
        self.config_path = os.path.join(_core_dir, "inbox_config.json")
        self._load_config()

    def _load_config(self) -> None:
        self.routing_rules = {}
        self.pdf_routing_rules: List[Dict[str, str]] = []  # list of {pattern, routing}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    cfg = json.load(f)

                    rules = cfg.get("routing_rules", {})
                    for ext in rules.get("voice_memo", []):
                        self.routing_rules[ext] = "audio_transcriber"
                    for ext in rules.get("pdf_knowledge", []):
                        self.routing_rules[ext] = "doc_parser"
                    for ext in rules.get("compiler", []):
                        self.routing_rules[ext] = "knowledge_compiler"

                    # Remove structured pdf_routing_rules as they violate sandbox boundaries

            except Exception as e:
                _logger.error("讀取 inbox_config.json 失敗: %s", e)

        if not self.routing_rules:
            self.routing_rules = {
                ".m4a": "audio_transcriber",
                ".mp3": "audio_transcriber",
                ".pdf": "doc_parser",
                ".mp4": "video_ingester",
                ".mov": "video_ingester",
                ".mkv": "video_ingester",
                ".webm": "video_ingester",
            }

    def _process_file(self, filepath: str) -> None:
        """Route a single raw file to its target skill's input directory."""
        # B-2 Fix: deduplicate files already dispatched by scan_all or watchdog
        with self._lock:
            if filepath in self._seen_files:
                return
            self._seen_files.add(filepath)

        filename = os.path.basename(filepath)

        # Extract Subject from relative path
        rel_path = os.path.relpath(filepath, self.raw_path)
        parts = rel_path.split(os.sep)
        subject = parts[0] if len(parts) > 1 else "Default"

        # Ask RouterAgent to resolve the intent based on file
        manifest = TaskManifest(source_path=filepath, subject=subject)
        chain = self.router.resolve(manifest)

        if not chain:
            _logger.info("未知格式或無法路由，忽略: %s", filepath)
            return

        target_skill = chain[0]

        # Strict Sandbox Routing
        target_dir = os.path.join(_workspace_root, "data", target_skill, "input", subject)
        _logger.info("路由派發: [%s] %s → %s", subject, filename, target_skill)

        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, filename)

        try:
            os.rename(filepath, target_path)
            _logger.info("已移動: [%s] %s → %s", subject, filename, target_skill)
            if os.sep + "input" + os.sep in target_dir + os.sep:
                self._schedule_trigger(target_skill, target_path)
        except Exception as e:
            _logger.error("無法移動檔案 %s: %s", filename, e)

    def scan_all(self) -> None:
        """Manually trigger scan for all files in raw_path."""
        _logger.info("正在掃描現有檔案: %s", self.raw_path)
        for root, _dirs, files in os.walk(self.raw_path):
            for filename in sorted(files):
                if filename.startswith("."):
                    continue
                filepath = os.path.join(root, filename)
                self._process_file(filepath)

    def start(self) -> None:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer

            class InboxHandler(FileSystemEventHandler):
                def __init__(self, daemon: "SystemInboxDaemon"):
                    self.daemon = daemon

                def on_created(self, event):
                    if event.is_directory:
                        return
                    self.daemon._process_file(event.src_path)

            class OutputWatchdogHandler(FileSystemEventHandler):
                def __init__(self, daemon: "SystemInboxDaemon"):
                    self.daemon = daemon

                def on_modified(self, event):
                    if event.is_directory or not event.src_path.endswith(".md"):
                        return
                    self.daemon._check_rewrite_status(event.src_path)

            self._observer = Observer()
            _logger.info("監控啟動 (遞迴支援多科目): 全局收件匣 -> %s", self.raw_path)
            self._observer.schedule(InboxHandler(self), self.raw_path, recursive=True)

            data_path = os.path.join(_workspace_root, "data")
            if os.path.exists(data_path):
                self._observer.schedule(OutputWatchdogHandler(self), data_path, recursive=True)
                _logger.info("監控啟動 (Obsidian Watchdog): 輸出資料夾 -> %s", data_path)

            self._observer.start()

        except ImportError:
            _logger.warning("watchdog 未安裝 (pip install watchdog)，忽略即時監控。")

    def _schedule_trigger(self, skill: str, filepath: str):
        """
        Debounce: cancel any existing poll thread for this file path,
        then start a fresh one with its own stop Event.
        """
        with self._lock:
            existing_event = self._debounce_events.get(filepath)
            if existing_event:
                existing_event.set()  # Signal old thread to stop (correct API)
            stop_event = threading.Event()
            self._debounce_events[filepath] = stop_event

        t = threading.Thread(
            target=self._wait_and_trigger,
            args=(skill, filepath, stop_event),
            daemon=True,
        )
        t.start()

    def _wait_and_trigger(self, skill: str, filepath: str, stop_event: threading.Event):
        """
        Poll file size until stable (unchanged for one interval).
        Exits on: size stable, stop_event set, file disappeared, or timeout.
        """
        prev_size = -1
        elapsed = 0.0

        while elapsed < _WAIT_TIMEOUT_SEC:
            if stop_event.is_set():
                _logger.debug("去抖取消，停止等待: %s", filepath)
                return

            try:
                if not os.path.exists(filepath):
                    _logger.warning("檔案已消失，放棄觸發: %s", filepath)
                    return
                current_size = os.path.getsize(filepath)
                if current_size == prev_size and current_size > 0:
                    break  # Stable!
                prev_size = current_size
            except OSError as e:
                _logger.debug("輪詢檔案大小時發生 OSError: %s — %s", filepath, e)

            time.sleep(_POLL_INTERVAL_SEC)
            elapsed += _POLL_INTERVAL_SEC
        else:
            _logger.error("等待超時 (%ss)，放棄觸發: %s", _WAIT_TIMEOUT_SEC, filepath)
            return

        # Clean up debounce map
        with self._lock:
            self._debounce_events.pop(filepath, None)

        self._trigger_pipeline(skill, filepath)

    def _trigger_pipeline(self, skill: str, filepath: str) -> None:
        """Route trigger through RouterAgent."""
        _logger.info("檔案已穩定，開始分發: %s (%s)", filepath, skill)

        # Re-extract subject since it might have changed
        rel_path = os.path.relpath(filepath, os.path.join(_workspace_root, "data", skill, "input"))
        parts = rel_path.split(os.sep)
        subject = parts[0] if len(parts) > 1 else "Default"

        manifest = TaskManifest(source_path=filepath, subject=subject)
        self.router.dispatch(manifest)

    def _check_rewrite_status(self, filepath: str) -> None:
        """Watch for YAML `status: rewrite` to trigger note_generator.

        B-1 Fix: reads the full file, replaces the status token atomically using
        AtomicWriter so a mid-write crash cannot corrupt the Obsidian note.
        Uses a separate rewrite-debounce set to avoid interfering with the
        file-arrival debounce map.
        """
        # Use a dedicated set so Watchdog debounce doesn't block file-arrival debounce
        with self._lock:
            if filepath in self._debounce_events:
                return

        try:
            with open(filepath, encoding="utf-8") as f:
                full_content = f.read()

            if "status: rewrite" not in full_content:
                return

            _logger.info("偵測到重寫請求: %s", filepath)

            # 1. B-1 Fix: replace status token and write back atomically
            new_content = full_content.replace("status: rewrite", "status: processing", 1)
            AtomicWriter.write_text(filepath, new_content)

            # 2. Extract Subject and infer target
            rel_path = os.path.relpath(filepath, os.path.join(_workspace_root, "data"))
            parts = rel_path.split(os.sep)
            subject = parts[3] if len(parts) > 3 else "Default"

            # 3. Enqueue the task
            cmd = SkillRunner.run_note_generator(
                input_file=filepath,
                output_file=filepath.replace(".md", "_rewrite.md"),
                subject=subject,
            )
            task_queue.enqueue(
                "Note Generator (Rewrite)",
                cmd,
                os.path.join(
                    _workspace_root, "skills", "note_generator"
                ),  # P0-1: underscore (matches skills/ dir)
            )

            # Prevent multiple triggers for this file
            with self._lock:
                self._debounce_events[filepath] = threading.Event()

        except OSError as e:
            _logger.error("讀取重寫狀態時發生 I/O 錯誤: %s — %s", filepath, e, exc_info=True)
        except Exception as e:
            _logger.error(
                "_check_rewrite_status 發生未預期錯誤: %s — %s", filepath, e, exc_info=True
            )

    def stop(self) -> None:
        """Gracefully stop the observer and all pending poll threads."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            _logger.info("監控已停止")
        with self._lock:
            for event in self._debounce_events.values():
                event.set()
            self._debounce_events.clear()
            self._seen_files.clear()


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Open Claw Inbox Daemon")
    parser.add_argument(
        "--scan-only", action="store_true", help="僅手動掃描並歸檔現有檔案，不啟動常駐監控"
    )
    args = parser.parse_args()

    daemon = SystemInboxDaemon()
    if args.scan_only:
        _logger.info("執行手動歸檔模式 (Scan Only)...")
        daemon.scan_all()
    else:
        daemon.start()
        daemon.scan_all()  # Initial scan on startup
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            daemon.stop()
