# -*- coding: utf-8 -*-
"""
inbox_daemon.py — Open Claw System-Wide Inbox Monitor
======================================================
Monitors the `inbox` canonical directories for all active skills using Watchdog.
When a new file arrives (e.g. .m4a for audio-transcriber, .pdf for doc-parser),
it triggers the target skill's pipeline via the WebUI API (with direct subprocess
fallback when the WebUI is not running).

Design:
  - File stability via size-polling (2s interval) with 300s timeout guard.
  - Same-file debounce via threading.Event (cancellable).
  - Routes triggers through ExecutionManager's Job Queue via HTTP POST /api/start
    to respect RAM-safety limits and prevent OOM from concurrent LLM processes.
"""

import os
import sys
import time
import json
import threading
import subprocess
import urllib.request
import urllib.error
from typing import List, Optional

# Path Resolution
_core_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.dirname(_core_dir)
)
sys.path.insert(0, _core_dir)

from path_builder import PathBuilder

# Constants
_WAIT_TIMEOUT_SEC = 300   # 5 min: abort if file never stabilises
_POLL_INTERVAL_SEC = 2.0
_WEBUI_API_URL = os.environ.get("OPENCLAW_DASHBOARD_URL", "http://127.0.0.1:5001")


class SystemInboxDaemon:
    def __init__(self, skills: List[str]):
        self.skills = skills
        self.monitors = []
        self._observer = None
        # Maps filepath → threading.Event (to cancel a pending poll thread)
        self._debounce_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

        # Configure tracking paths
        for skill in skills:
            pb = PathBuilder(_workspace_root, skill)
            if "input" in pb.canonical_dirs:
                inbox_path = pb.phase_dirs.get("inbox", pb.phase_dirs.get("p0", pb.canonical_dirs["input"]))
                os.makedirs(inbox_path, exist_ok=True)
                exts = [".pdf"] if skill == "doc-parser" else [".m4a", ".mp3", ".wav"]
                self.monitors.append({
                    "skill": skill,
                    "path": inbox_path,
                    "extensions": exts,
                })

    def start(self):
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class InboxHandler(FileSystemEventHandler):
                def __init__(self, daemon: "SystemInboxDaemon", monitor_cfg: dict):
                    self.daemon = daemon
                    self.monitor_cfg = monitor_cfg

                def on_created(self, event):
                    if event.is_directory:
                        return
                    ext = os.path.splitext(event.src_path)[1].lower()
                    if ext in self.monitor_cfg["extensions"]:
                        self.daemon._schedule_trigger(self.monitor_cfg["skill"], event.src_path)

            self._observer = Observer()
            for m in self.monitors:
                print(f"👁️ [Daemon] 監控啟動: [{m['skill']}] -> {m['path']} (副檔名: {m['extensions']})")
                self._observer.schedule(InboxHandler(self, m), m["path"], recursive=True)
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
        Route trigger through WebUI's ExecutionManager Job Queue (via HTTP POST).
        Falls back to direct subprocess.Popen only when WebUI is not running.
        This prevents OOM from N concurrent LLM processes on large batch arrivals.
        """
        print(f"\n🚀 [Daemon] 偵測到新檔案: {filepath} ({skill})")

        # --- Primary path: route through WebUI Job Queue ---
        try:
            payload = json.dumps({"skill": skill}).encode("utf-8")
            req = urllib.request.Request(
                f"{_WEBUI_API_URL}/api/start",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                body = json.loads(resp.read())
                if body.get("success"):
                    print(f"✅ [Daemon] 已通過 WebUI API 排入佇列: {skill}")
                    return
                else:
                    print(f"⚠️ [Daemon] WebUI API 拒絕: {body.get('error', '?')} — 改為直接啟動")
        except (urllib.error.URLError, OSError):
            print(f"ℹ️ [Daemon] WebUI 未運行，改為直接啟動行程...")

        # --- Fallback: direct subprocess (standalone mode without WebUI) ---
        script_path = os.path.join(_workspace_root, "skills", skill, "scripts", "run_all.py")
        if os.path.exists(script_path):
            print(f"👉 呼叫: python3 {script_path} --process-all")
            subprocess.Popen(
                [sys.executable, script_path, "--process-all"],
                cwd=os.path.join(_workspace_root, "skills", skill),
            )
        else:
            print(f"❌ 找不到執行腳本: {script_path}")

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
    daemon = SystemInboxDaemon(["audio-transcriber", "doc-parser"])
    daemon.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()
