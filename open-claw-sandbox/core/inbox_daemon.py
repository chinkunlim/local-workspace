# -*- coding: utf-8 -*-
"""
inbox_daemon.py — Open Claw System-Wide Inbox Monitor
======================================================
Monitors the `inbox` canonical directories for all active skills using Watchdog.
When a new file arrives (e.g. .m4a for audio-transcriber, .pdf for doc-parser),
it triggers the target skill's pipeline via the WebUI API (with direct subprocess
fallback when the WebUI is not running).

Design:
  - Watches the global `data/raw` directory.
  - Routes files to specific skills based on extension (.m4a -> voice-memo, .pdf -> pdf-knowledge).
  - File stability via size-polling (2s interval) with 300s timeout guard.
  - Same-file debounce via threading.Event (cancellable).
"""

import os
import sys
import time
import json
import threading
import subprocess
from core.task_queue import task_queue
from core.cli_runner import SkillRunner
from typing import List, Optional

# Path Resolution
_core_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.dirname(_core_dir)
)
# Ensure workspace root is on sys.path so `from core.xxx` always resolves
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

from core.path_builder import PathBuilder

# Constants
_WAIT_TIMEOUT_SEC = 300   # 5 min: abort if file never stabilises
_POLL_INTERVAL_SEC = 2.0


class SystemInboxDaemon:
    def __init__(self):
        self._observer = None
        self._debounce_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

        # Configure global raw path
        self.raw_path = os.path.join(_workspace_root, "data", "raw")
        os.makedirs(self.raw_path, exist_ok=True)
        
        # Load Config
        self.config_path = os.path.join(_core_dir, "inbox_config.json")
        self._load_config()

    def _load_config(self):
        self.routing_rules = {}
        self.pdf_routing_rules = []   # list of {pattern, routing}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)

                    rules = cfg.get("routing_rules", {})
                    for ext in rules.get("voice_memo", []):    self.routing_rules[ext] = "audio-transcriber"
                    for ext in rules.get("pdf_knowledge", []): self.routing_rules[ext] = "doc-parser"
                    for ext in rules.get("compiler", []):      self.routing_rules[ext] = "knowledge-compiler"

                    # Remove structured pdf_routing_rules as they violate sandbox boundaries

            except Exception as e:
                print(f"❌ [Daemon] 讀取 inbox_config.json 失敗: {e}")

        if not self.routing_rules:
            self.routing_rules = {".m4a": "audio-transcriber", ".mp3": "audio-transcriber", ".pdf": "doc-parser"}

    def _process_file(self, filepath: str):
        self._load_config() # Reload config on fly
        
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()
        basename_noext = os.path.splitext(filename)[0]
        
        # Extract Subject from relative path
        rel_path = os.path.relpath(filepath, self.raw_path)
        parts = rel_path.split(os.sep)
        subject = parts[0] if len(parts) > 1 else "Default"
        
        target_skill = self.routing_rules.get(ext)
        
        if not target_skill:
            print(f"ℹ️ [Daemon] 未知格式，忽略: {filepath}")
            return

        # Strict Sandbox Routing
        target_dir = os.path.join(_workspace_root, "data", target_skill, "input", subject)
        print(f"📄 [Daemon] 路由派發: [{subject}] {filename} → {target_skill}")

        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, filename)

        try:
            os.rename(filepath, target_path)
            print(f"🚚 [Daemon] 已移動: [{subject}] {filename} → {target_skill}")
            if os.sep + "input" + os.sep in target_dir + os.sep:
                self._schedule_trigger(target_skill, target_path)
        except Exception as e:
            print(f"❌ [Daemon] 無法移動檔案 {filename}: {e}")

    def scan_all(self):
        """Manually trigger scan for all files in raw_path."""
        print(f"🔄 [Daemon] 正在掃描現有檔案: {self.raw_path}")
        for root, dirs, files in os.walk(self.raw_path):
            for filename in sorted(files):
                if filename.startswith("."): continue
                filepath = os.path.join(root, filename)
                self._process_file(filepath)

    def start(self):
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

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
            print(f"👁️ [Daemon] 監控啟動 (遞迴支援多科目): 全局收件匣 -> {self.raw_path}")
            self._observer.schedule(InboxHandler(self), self.raw_path, recursive=True)
            
            data_path = os.path.join(_workspace_root, "data")
            if os.path.exists(data_path):
                self._observer.schedule(OutputWatchdogHandler(self), data_path, recursive=True)
                print(f"👁️ [Daemon] 監控啟動 (Obsidian Watchdog): 輸出資料夾 -> {data_path}")
                
            self._observer.start()

        except ImportError:
            print("⚠️ [Daemon] watchdog 未安裝 (pip install watchdog)，忽略即時監控。")

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
                print(f"⏹️ [Daemon] 去抖取消，停止等待: {filepath}")
                return

            try:
                if not os.path.exists(filepath):
                    print(f"⚠️ [Daemon] 檔案已消失，放棄觸發: {filepath}")
                    return
                current_size = os.path.getsize(filepath)
                if current_size == prev_size and current_size > 0:
                    break  # Stable!
                prev_size = current_size
            except OSError:
                pass

            time.sleep(_POLL_INTERVAL_SEC)
            elapsed += _POLL_INTERVAL_SEC
        else:
            print(f"❌ [Daemon] 等待超時 ({_WAIT_TIMEOUT_SEC}s)，放棄觸發: {filepath}")
            return

        # Clean up debounce map
        with self._lock:
            self._debounce_events.pop(filepath, None)

        self._trigger_pipeline(skill, filepath)

    def _trigger_pipeline(self, skill: str, filepath: str):
        """
        Route trigger through the single-threaded Task Queue to prevent OOM.
        """
        print(f"\n🚀 [Daemon] 偵測到新檔案: {filepath} ({skill})")
        
        cwd = os.path.join(_workspace_root, "skills", skill)
        
        if skill == "audio-transcriber":
            cmd = SkillRunner.run_audio_transcriber()
        elif skill == "doc-parser":
            cmd = SkillRunner.run_doc_parser()
        else:
            script_path = os.path.join(cwd, "scripts", "run_all.py")
            cmd = [sys.executable, script_path, "--process-all"]

        task_queue.enqueue(f"{skill} Pipeline", cmd, cwd)

    def _check_rewrite_status(self, filepath: str):
        """Watch for YAML `status: rewrite` to trigger note_generator."""
        # Simple debounce check using the file lock mechanism
        with self._lock:
            if filepath in self._debounce_events:
                return
                
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                head = f.read(500)
                if "status: rewrite" in head:
                    print(f"\n🔄 [Watchdog] 偵測到重寫請求: {filepath}")
                    
                    # 1. Update status to 'processing' to avoid infinite loops
                    new_content = head.replace("status: rewrite", "status: processing")
                    with open(filepath, "r+", encoding="utf-8") as fw:
                        fw.seek(0)
                        fw.write(new_content)
                        
                    # 2. Extract Subject and infer target
                    rel_path = os.path.relpath(filepath, os.path.join(_workspace_root, "data"))
                    parts = rel_path.split(os.sep)
                    skill = parts[0] if len(parts) > 0 else "note-generator"
                    subject = parts[3] if len(parts) > 3 else "Default"
                    
                    # 3. Enqueue the task
                    cmd = SkillRunner.run_note_generator(
                        input_file=filepath,
                        output_file=filepath.replace(".md", "_rewrite.md"), # simple example output
                        subject=subject
                    )
                    task_queue.enqueue(f"Note Generator (Rewrite)", cmd, os.path.join(_workspace_root, "skills", "note-generator"))
                    
                    # Prevent multiple triggers
                    with self._lock:
                        self._debounce_events[filepath] = threading.Event()
                        
        except Exception:
            pass

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
            print("👁️ [Daemon] 監控已停止")
        # Signal all pending poll threads to stop
        with self._lock:
            for event in self._debounce_events.values():
                event.set()
            self._debounce_events.clear()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Open Claw Inbox Daemon")
    parser.add_argument("--scan-only", action="store_true", help="僅手動掃描並歸檔現有檔案，不啟動常駐監控")
    args = parser.parse_args()

    daemon = SystemInboxDaemon()
    if args.scan_only:
        print("🚀 [Daemon] 執行手動歸檔模式 (Scan Only)...")
        daemon.scan_all()
    else:
        daemon.start()
        daemon.scan_all() # Initial scan on startup
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            daemon.stop()
