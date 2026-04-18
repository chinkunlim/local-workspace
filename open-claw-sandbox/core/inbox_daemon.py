# -*- coding: utf-8 -*-
"""
inbox_daemon.py — Open Claw System-Wide Inbox Monitor
======================================================
Monitors the `inbox` canonical directories for all active skills using Watchdog.
When a new file arrives (e.g. .m4a for audio-transcriber, .pdf for doc-parser),
it triggers the target skill's pipeline logic automatically.

Designed to be spawned by the background Execution Manager in Web UI.
"""

import os
import sys
import time
import threading
import subprocess
from typing import List

# Path Resolution
_core_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.dirname(_core_dir)
)
sys.path.insert(0, _core_dir)

from path_builder import PathBuilder


class SystemInboxDaemon:
    def __init__(self, skills: List[str]):
        self.skills = skills
        self.monitors = []
        self._observer = None
        self._debounce_timers = {}
        
        # Configure tracking paths
        for skill in skills:
            pb = PathBuilder(_workspace_root, skill)
            if "input" in pb.canonical_dirs:
                # Use phase alias mapping if available to find precise paths
                inbox_path = pb.phase_dirs.get("inbox", pb.phase_dirs.get("p0", pb.canonical_dirs["input"]))
                os.makedirs(inbox_path, exist_ok=True)
                exts = [".pdf"] if skill == "doc-parser" else [".m4a", ".mp3", ".wav"]
                self.monitors.append({
                    "skill": skill,
                    "path": inbox_path,
                    "extensions": exts
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
                        path = event.src_path
                        if path in self.daemon._debounce_timers:
                            self.daemon._debounce_timers[path].cancel()
                        # Use a thread to poll file size instead of a naive timer
                        timer = threading.Thread(target=self.daemon._wait_and_trigger, args=(self.monitor_cfg["skill"], path))
                        self.daemon._debounce_timers[path] = timer
                        timer.start()

            self._observer = Observer()
            for m in self.monitors:
                print(f"👁️ [Daemon] 監控啟動: [{m['skill']}] -> {m['path']} (副檔名: {m['extensions']})")
                self._observer.schedule(InboxHandler(self, m), m["path"], recursive=True)
                
            self._observer.start()

        except ImportError:
            print("⚠️ [Daemon] watchdog 未安裝 (pip install watchdog)，忽略即時監控。")

    def _wait_and_trigger(self, skill: str, filepath: str):
        prev_size = -1
        while True:
            try:
                current_size = os.path.getsize(filepath)
                if current_size == prev_size and current_size > 0:
                    break
                prev_size = current_size
                time.sleep(2.0)
            except OSError:
                time.sleep(2.0)
        self._trigger_pipeline(skill, filepath)

    def _trigger_pipeline(self, skill: str, filepath: str):
        print(f"\n🚀 [Daemon] 偵測到新檔案: {filepath} ({skill})")
        # In this daemon, we just call the background worker mechanism or run the script directly.
        # Since this script runs globally, we can use subprocess to start the background process, 
        # but the Web UI already handles task launching. So we can just call the run_all.py of that skill.
        script_path = os.path.join(_workspace_root, "skills", skill, "scripts", "run_all.py")
        if os.path.exists(script_path):
            print(f"👉 呼叫: python3 {script_path} --process-all")
            # We fire and forget
            subprocess.Popen([sys.executable, script_path, "--process-all"], 
                             cwd=os.path.join(_workspace_root, "skills", skill))
        else:
            print(f"❌ 找不到執行腳本: {script_path}")

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
            print("👁️ [Daemon] 監控已停止")

if __name__ == "__main__":
    daemon = SystemInboxDaemon(["audio-transcriber", "doc-parser"])
    daemon.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()
