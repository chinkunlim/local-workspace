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
        self.audio_ref_suffixes = []
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    
                    # Flatten routing rules to {ext: skill}
                    # Map old names to new names if necessary
                    rules = cfg.get("routing_rules", {})
                    for ext in rules.get("voice_memo", []): self.routing_rules[ext] = "audio-transcriber"
                    for ext in rules.get("pdf_knowledge", []): self.routing_rules[ext] = "doc-parser"
                    for ext in rules.get("compiler", []): self.routing_rules[ext] = "knowledge-compiler"
                    
                    self.audio_ref_suffixes = cfg.get("audio_reference_suffixes", [])
            except Exception as e:
                print(f"❌ [Daemon] 讀取 inbox_config.json 失敗: {e}")
                
        # Fallback if empty
        if not self.routing_rules:
            self.routing_rules = {".m4a": "audio-transcriber", ".mp3": "audio-transcriber", ".pdf": "doc-parser"}

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
                        
                    self.daemon._load_config() # Reload config on fly
                    
                    filepath = event.src_path
                    filename = os.path.basename(filepath)
                    ext = os.path.splitext(filename)[1].lower()
                    basename_noext = os.path.splitext(filename)[0]
                    
                    # Extract Subject from relative path
                    rel_path = os.path.relpath(filepath, self.daemon.raw_path)
                    parts = rel_path.split(os.sep)
                    subject = parts[0] if len(parts) > 1 else "Default"
                    
                    target_skill = self.daemon.routing_rules.get(ext)
                    
                    if not target_skill:
                        print(f"ℹ️ [Daemon] 未知格式，忽略: {filepath}")
                        return

                    # Smart PDF Routing — case-insensitive; underscore-prefixed patterns
                    # are suffix matches; CJK patterns match anywhere in the name.
                    target_dir = os.path.join(_workspace_root, "data", target_skill, "input", subject)
                    is_audio_ref = False
                    if ext == ".pdf":
                        name_lower = basename_noext.lower()
                        for suffix in self.daemon.audio_ref_suffixes:
                            s = suffix.lower()
                            if s.startswith("_"):           # Underscore patterns → suffix match
                                if name_lower.endswith(s):
                                    is_audio_ref = True
                                    break
                            else:                           # CJK / word patterns → contains match
                                if s in name_lower:
                                    is_audio_ref = True
                                    break

                        if is_audio_ref:
                            target_skill = "audio-transcriber"
                            target_dir = os.path.join(_workspace_root, "data", target_skill, "output", "00_glossary", subject)
                            print(f"🔍 [Daemon] 偵測到參考文獻規則，路由至音檔詞庫區: {filename}")
                        else:
                            print(f"📄 [Daemon] 一般文獻，路由至 doc-parser 解析: {filename}")

                    os.makedirs(target_dir, exist_ok=True)
                    target_path = os.path.join(target_dir, filename)

                    try:
                        os.rename(filepath, target_path)
                        print(f"🚚 [Daemon] 已移動: [{subject}] {filename} → {target_skill}")

                        # Only trigger pipeline for files that landed in input/
                        if os.sep + "input" + os.sep in target_dir + os.sep:
                            self.daemon._schedule_trigger(target_skill, target_path)
                    except Exception as e:
                        print(f"❌ [Daemon] 無法移動檔案 {filename}: {e}")

            self._observer = Observer()
            print(f"👁️ [Daemon] 監控啟動 (遞迴支援多科目): 全局收件匣 -> {self.raw_path}")
            self._observer.schedule(InboxHandler(self), self.raw_path, recursive=True)
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
    daemon = SystemInboxDaemon()
    daemon.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()
