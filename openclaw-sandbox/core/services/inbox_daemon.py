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
import re
import sys
import threading
import time
from typing import Any, Optional

# Path Resolution MUST happen before importing internal packages
_core_dir = os.path.dirname(os.path.abspath(__file__))
from core.utils.workspace import get_workspace_root

_workspace_root = get_workspace_root()

from core.cli.cli_runner import SkillRunner
from core.orchestration.router_agent import RouterAgent, TaskManifest
from core.orchestration.session_manifest import update_session_manifest
from core.orchestration.skill_registry import SkillRegistry
from core.utils.atomic_writer import AtomicWriter
from core.utils.file_stability import FileStabilityPoller

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
        self._lock = threading.Lock()
        self.router = RouterAgent()
        self.stability_poller = FileStabilityPoller(
            poll_interval_sec=_POLL_INTERVAL_SEC, timeout_sec=_WAIT_TIMEOUT_SEC
        )
        # B-2 Fix: track files already dispatched to prevent dual-trigger
        import collections

        self._seen_files: collections.OrderedDict[str, bool] = collections.OrderedDict()
        self.MAX_SEEN = 10000

        # Configure global raw path
        self.raw_path = os.path.join(_workspace_root, "data", "raw")
        os.makedirs(self.raw_path, exist_ok=True)

        # Initialize Registry and Router
        self.registry = SkillRegistry(os.path.join(_workspace_root, "skills"))
        self.registry.discover()
        self.router = RouterAgent(registry=self.registry)

    def _process_file(self, filepath: str) -> None:
        """Route a single raw file to its target skill's input directory."""
        # Auto-fix filename format before doing anything
        filename = os.path.basename(filepath)
        import re

        if re.match(r"^L\d{2} ", filename):
            new_filename = filename[:3] + "_" + filename[4:]
            new_filepath = os.path.join(os.path.dirname(filepath), new_filename)
            try:
                os.rename(filepath, new_filepath)
                filepath = new_filepath
                filename = new_filename
                _logger.info("自動校正檔名: %s", new_filename)
            except Exception as e:
                _logger.error("自動校正檔名失敗: %s", e)

        # B-2 Fix: deduplicate files already dispatched by scan_all or watchdog
        with self._lock:
            if filepath in self._seen_files:
                return
            self._seen_files[filepath] = True
            if len(self._seen_files) > self.MAX_SEEN:
                self._seen_files.popitem(last=False)

        # Extract Subject from relative path
        rel_path = os.path.relpath(filepath, os.path.join(_workspace_root, "data"))
        parts = rel_path.split(os.sep)
        if parts[0] == "raw":
            subject = parts[1] if len(parts) > 2 else "Default"
        elif len(parts) >= 3 and parts[1] == "input":
            subject = parts[2] if len(parts) > 3 else "Default"
        else:
            subject = "Default"

        subject = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fa5]", "", subject)
        if not subject:
            subject = "Default"

        intent = "auto"
        if subject.lower() == "inbox":
            subject = "Default"
            if filename.lower().endswith((".md", ".txt")):
                try:
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                    # Find first hashtag
                    match = re.search(r"#([a-zA-Z0-9_\u4e00-\u9fa5]+)", content)
                    if match:
                        subject = match.group(1)
                        _logger.info("標籤解析成功: 找到主題 %s", subject)
                except Exception as e:
                    _logger.error("讀取標籤失敗: %s", e)

        if filename.startswith("Gemini_") or filename.startswith("Ollama_"):
            intent = "research"
            _logger.info("偵測到對話紀錄，強制掛載研究意圖: %s", intent)

        # Ask RouterAgent to resolve the intent based on file
        manifest = TaskManifest(source_path=filepath, subject=subject, intent=intent)
        chain = self.router.resolve(manifest)

        if not chain:
            _logger.info("未知格式或無法路由，忽略: %s", filepath)
            return

        target_skill = chain[0]

        # Strict Sandbox Routing
        target_dir = os.path.join(_workspace_root, "data", target_skill, "input", subject)

        import pathlib

        target_resolved = pathlib.Path(target_dir).resolve()
        sandbox_resolved = pathlib.Path(_workspace_root, "data").resolve()
        # 確保 target_dir 完全在 sandbox 內，防範惡意 subject / target_skill 造成的目錄逃逸
        if not str(target_resolved).startswith(str(sandbox_resolved) + os.sep):
            _logger.error("🚨 Path traversal detected! Blocking move: %s", target_dir)
            return

        _logger.info("路由派發: [%s] %s → %s", subject, filename, target_skill)

        # Clear deleted_at flag if it exists
        state_file = os.path.join(
            _workspace_root, "data", target_skill, "state", ".pipeline_state.json"
        )
        if os.path.exists(state_file):
            try:
                import json

                with self._lock:
                    with open(state_file) as f:
                        state = json.load(f)
                    if (
                        subject in state
                        and filename in state[subject]
                        and "deleted_at" in state[subject][filename]
                    ):
                        del state[subject][filename]["deleted_at"]
                        with open(state_file, "w") as f:
                            json.dump(state, f, indent=4, ensure_ascii=False)
                        _logger.info("檔案已歸位，撤銷軟刪除標記: [%s] %s", subject, filename)
            except Exception as e:
                pass

        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, filename)

        try:
            if os.path.abspath(filepath) != os.path.abspath(target_path):
                os.rename(filepath, target_path)
                _logger.info("已移動: [%s] %s → %s", subject, filename, target_skill)
            else:
                _logger.info("檔案已就位: [%s] %s (%s)", subject, filename, target_skill)

            # Update Session Manifest (File arrived and waiting to stabilize)
            update_session_manifest(_workspace_root, subject, filename, target_skill, "pending")

            if os.sep + "input" + os.sep in target_dir + os.sep:
                self.stability_poller.schedule_trigger(
                    target_path,
                    callback=lambda path: self._trigger_pipeline(target_skill, path, intent),
                )
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

                def on_deleted(self, event):
                    if event.is_directory:
                        return
                    self.daemon._mark_deleted(event.src_path)

                def on_moved(self, event):
                    if event.is_directory:
                        return
                    self.daemon._mark_deleted(event.src_path)
                    self.daemon._process_file(event.dest_path)

            class OutputWatchdogHandler(FileSystemEventHandler):
                def __init__(self, daemon: "SystemInboxDaemon"):
                    self.daemon = daemon

                def on_modified(self, event):
                    if event.is_directory or not event.src_path.endswith(".md"):
                        return

                    if "04_final_verified" in event.src_path:
                        self.daemon._check_proofreader_resume(event.src_path)
                    else:
                        self.daemon._check_rewrite_status(event.src_path)

                def on_created(self, event):
                    if event.is_directory or not event.src_path.endswith(".md"):
                        return

                    if "04_final_verified" in event.src_path:
                        self.daemon._check_proofreader_resume(event.src_path)

                    if "doc_parser" in event.src_path and "output" in event.src_path:
                        self.daemon._invalidate_proofreader(event.src_path)

            self._observer = Observer()
            watch_dirs = [
                self.raw_path,
                os.path.join(_workspace_root, "data", "audio_transcriber", "input"),
                os.path.join(_workspace_root, "data", "doc_parser", "input"),
            ]

            for wd in watch_dirs:
                os.makedirs(wd, exist_ok=True)
                self._observer.schedule(InboxHandler(self), wd, recursive=True)
                _logger.info("監控啟動 (遞迴支援多科目): 全局收件匣 -> %s", wd)

            data_path = os.path.join(_workspace_root, "data")
            if os.path.exists(data_path):
                self._observer.schedule(OutputWatchdogHandler(self), data_path, recursive=True)
                _logger.info("監控啟動 (Obsidian Watchdog): 輸出資料夾 -> %s", data_path)

            self._observer.start()

        except ImportError:
            _logger.warning("watchdog 未安裝 (pip install watchdog)，忽略即時監控。")

        # Start GC thread
        import threading

        gc_thread = threading.Thread(target=self._gc_loop, daemon=True)
        gc_thread.start()
        _logger.info("背景垃圾回收機制 (GC Thread) 已啟動")

    def _mark_deleted(self, filepath: str) -> None:
        """Mark a file as softly deleted when it is removed from the input directory."""
        import json
        import time

        filename = os.path.basename(filepath)

        # Get skill and subject
        rel_path = os.path.relpath(filepath, os.path.join(_workspace_root, "data"))
        parts = rel_path.split(os.sep)
        skill = (
            "audio_transcriber"
            if filepath.endswith((".mp3", ".m4a", ".wav", ".ogg"))
            else "doc_parser"
        )

        if parts[0] == "raw":
            subject = parts[1] if len(parts) > 2 else "Default"
        elif len(parts) >= 3 and parts[1] == "input":
            skill = parts[0]
            subject = parts[2] if len(parts) > 3 else "Default"
        else:
            subject = "Default"

        subject = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fa5]", "", subject)
        if not subject:
            subject = "Default"

        state_file = os.path.join(_workspace_root, "data", skill, "state", ".pipeline_state.json")
        if not os.path.exists(state_file):
            return

        try:
            with self._lock:
                with open(state_file) as f:
                    state = json.load(f)

                if subject in state and filename in state[subject]:
                    state[subject][filename]["deleted_at"] = time.time()
                    with open(state_file, "w") as f:
                        json.dump(state, f, indent=4, ensure_ascii=False)
                    _logger.warning(
                        "已將檔案標記為軟刪除 (24小時後回收): [%s] %s", subject, filename
                    )
        except Exception as e:
            _logger.error("標記軟刪除失敗: %s", e)

    def _gc_loop(self) -> None:
        """Periodically sweep state files for expired softly deleted records."""
        import json
        import shutil
        import time

        from core.state.global_registry import GlobalRegistry

        GC_DELAY_SEC = 24 * 3600  # 24 hours

        while True:
            time.sleep(300)  # Check every 5 minutes

            skills = ["audio_transcriber", "doc_parser"]
            registry = GlobalRegistry(_workspace_root)
            registry_data = registry._load()
            registry_changed = False

            for skill in skills:
                state_file = os.path.join(
                    _workspace_root, "data", skill, "state", ".pipeline_state.json"
                )
                if not os.path.exists(state_file):
                    continue

                state_changed = False
                try:
                    with self._lock:
                        with open(state_file) as f:
                            state = json.load(f)

                        for subj in list(state.keys()):
                            if subj == "_checkpoint":
                                continue
                            for fname in list(state[subj].keys()):
                                record = state[subj][fname]
                                if isinstance(record, dict) and "deleted_at" in record:
                                    if time.time() - record["deleted_at"] > GC_DELAY_SEC:
                                        _logger.warning(
                                            "🗑️ 檔案已逾時 24 小時，執行垃圾回收: [%s] %s",
                                            subj,
                                            fname,
                                        )
                                        prefix = os.path.splitext(fname)[0]
                                        output_base = os.path.join(
                                            _workspace_root, "data", skill, "output"
                                        )
                                        trash_base = os.path.join(
                                            _workspace_root, "data", ".trash", skill, "output"
                                        )

                                        # 1. Move to Trash
                                        if os.path.exists(output_base):
                                            for phase_dir in os.listdir(output_base):
                                                phase_path = os.path.join(
                                                    output_base, phase_dir, subj
                                                )
                                                trash_path = os.path.join(
                                                    trash_base, phase_dir, subj
                                                )

                                                if not os.path.exists(phase_path):
                                                    continue
                                                os.makedirs(trash_path, exist_ok=True)

                                                folder_path = os.path.join(phase_path, prefix)
                                                if os.path.isdir(folder_path):
                                                    shutil.move(
                                                        folder_path,
                                                        os.path.join(trash_path, prefix),
                                                    )

                                                for out_f in os.listdir(phase_path):
                                                    if out_f.startswith(prefix) and os.path.isfile(
                                                        os.path.join(phase_path, out_f)
                                                    ):
                                                        shutil.move(
                                                            os.path.join(phase_path, out_f),
                                                            os.path.join(trash_path, out_f),
                                                        )

                                        # 2. Remove from Registry
                                        if subj in registry_data and prefix in registry_data[subj]:
                                            if skill in registry_data[subj][prefix]:
                                                del registry_data[subj][prefix][skill]
                                                if not registry_data[subj][prefix]:
                                                    del registry_data[subj][prefix]
                                                registry_changed = True

                                        # 3. Remove from state
                                        del state[subj][fname]
                                        state_changed = True

                            if not state[subj]:
                                del state[subj]
                                state_changed = True

                        if state_changed:
                            with open(state_file, "w") as f:
                                json.dump(state, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    _logger.error("GC 錯誤 (%s): %s", skill, e)

            if registry_changed:
                registry._memory_cache = registry_data
                registry._save()

    def _invalidate_proofreader(self, filepath: str) -> None:
        """When doc_parser finishes a file, invalidate P3 for the subject in proofreader to force re-pairing."""
        import json

        rel_path = os.path.relpath(
            filepath, os.path.join(_workspace_root, "data", "doc_parser", "output")
        )
        parts = rel_path.split(os.sep)
        if len(parts) >= 2:
            # phase_dir / subject / ...
            subject = parts[1]
            state_file = os.path.join(
                _workspace_root, "data", "proofreader", "state", ".pipeline_state.json"
            )
            if os.path.exists(state_file):
                try:
                    with open(state_file) as f:
                        state = json.load(f)
                    if subject in state:
                        changed = False
                        for fname, record in state[subject].items():
                            if isinstance(record, dict) and "p3" in record and record["p3"] != "⏳":
                                record["p3"] = "⏳"
                                changed = True
                        if changed:
                            with open(state_file, "w") as f:
                                json.dump(state, f, indent=4, ensure_ascii=False)
                            _logger.info("已失效 Proofreader P3 狀態，強制重新配對: %s", subject)
                            # Trigger proofreader
                            self._trigger_pipeline(
                                "proofreader",
                                os.path.join(
                                    _workspace_root,
                                    "data",
                                    "audio_transcriber",
                                    "output",
                                    "03_merged",
                                    subject,
                                    "dummy.md",
                                ),
                                intent="auto",
                            )
                except Exception as e:
                    _logger.error("無法更新 proofreader 狀態: %s", e)

    def _trigger_pipeline(self, skill: str, filepath: str, intent: str = "auto") -> None:
        """Route trigger through RouterAgent."""
        _logger.info("檔案已穩定，開始分發: %s (%s)", filepath, skill)

        # Re-extract subject since it might have changed
        rel_path = os.path.relpath(filepath, os.path.join(_workspace_root, "data", skill, "input"))
        parts = rel_path.split(os.sep)
        subject = parts[0] if len(parts) > 1 else "Default"
        subject = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fa5]", "", subject)
        if not subject:
            subject = "Default"

        manifest = TaskManifest(source_path=filepath, subject=subject, intent=intent)
        self.router.dispatch(manifest)

    def _check_rewrite_status(self, filepath: str) -> None:
        """Watch for YAML `status: rewrite` to trigger note_generator.

        B-1 Fix: reads the full file, replaces the status token atomically using
        AtomicWriter so a mid-write crash cannot corrupt the Obsidian note.
        Uses a separate rewrite-debounce set to avoid interfering with the
        file-arrival debounce map.
        """
        # Use a dedicated set so Watchdog debounce doesn't block file-arrival debounce
        # Check if the poller is already tracking it
        with self._lock:
            if filepath in self._seen_files:
                return
            self._seen_files[filepath] = True

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
            subject = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fa5]", "", subject)
            if not subject:
                subject = "Default"

            # 3. Enqueue the task
            cmd = SkillRunner.run_note_generator(
                input_file=filepath,
                output_file=filepath.replace(".md", "_rewrite.md"),
                subject=subject,
            )
            from core.orchestration.task_queue import LocalTaskQueue

            LocalTaskQueue().enqueue(
                "Note Generator (Rewrite)",
                cmd,
                os.path.join(
                    _workspace_root, "skills", "note_generator"
                ),  # P0-1: underscore (matches skills/ dir)
            )

        except OSError as e:
            _logger.error("讀取重寫狀態時發生 I/O 錯誤: %s — %s", filepath, e, exc_info=True)
        except Exception as e:
            _logger.error(
                "_check_rewrite_status 發生未預期錯誤: %s — %s", filepath, e, exc_info=True
            )

    def _check_proofreader_resume(self, filepath: str) -> None:
        """Watch for new files in proofreader/output/04_final_verified to resume the pipeline."""
        with self._lock:
            if filepath in self._seen_files:
                return
            self._seen_files[filepath] = True

        try:
            filename = os.path.basename(filepath)
            rel_path = os.path.relpath(
                filepath,
                os.path.join(_workspace_root, "data", "proofreader", "output", "04_final_verified"),
            )
            parts = rel_path.split(os.sep)
            if len(parts) < 2:
                return

            subject = parts[0]
            subject = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fa5]", "", subject)
            if not subject:
                subject = "Default"
            file_id = os.path.splitext(filename)[0]

            pending_path = os.path.join(
                _workspace_root, "data", "proofreader", "pending_chains", subject, f"{file_id}.json"
            )
            if not os.path.exists(pending_path):
                return

            _logger.info("偵測到校對完成，準備喚醒後續管線: %s", filepath)

            with open(pending_path, encoding="utf-8") as f:
                pending_data = json.load(f)

            remaining_chain = pending_data.get("chain", [])
            env = pending_data.get("env", {})

            if not remaining_chain:
                _logger.info("無後續管線需要喚醒。")
                os.remove(pending_path)
                return

            # Publish EventBus message so RouterAgent picks it up
            from core.orchestration.event_bus import DomainEvent, EventBus

            # Include proofreader as current_skill so RouterAgent maps to the next_skill properly
            resume_chain = ["proofreader", *remaining_chain]

            EventBus.publish(
                DomainEvent(
                    name="PipelineCompleted",
                    source_skill="proofreader",
                    payload={
                        "filepath": filepath,
                        "chain": resume_chain,
                        "subject": subject,
                        "model": env.get("OPENCLAW_ROUTER_MODEL") if env else None,
                    },
                )
            )

            # Remove the pending file so we don't trigger it again
            os.remove(pending_path)

            # File stability poller already debounces this, no need for manual lock

        except Exception as e:
            _logger.error(
                "_check_proofreader_resume 發生未預期錯誤: %s — %s", filepath, e, exc_info=True
            )

    def stop(self) -> None:
        """Gracefully stop the observer and all pending poll threads."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            _logger.info("監控已停止")
        with self._lock:
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
