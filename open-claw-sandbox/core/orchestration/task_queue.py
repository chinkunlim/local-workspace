"""
core/task_queue.py — Single-Threaded Task Queue for OOM Prevention
===================================================================
A lightweight, background job queue that ensures Open Claw skills run
sequentially. This replaces the old concurrent `subprocess.Popen` logic
in `inbox_daemon.py` which could easily crash the system (OOM) when
multiple files arrive simultaneously.
"""

from datetime import datetime
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from typing import List, Optional

from core.log_manager import build_logger

# Use workspace root to locate the data directory for quarantine
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_logger = build_logger(
    "OpenClaw.TaskQueue", log_file=os.path.join(_workspace_root, "logs", "task_queue.log")
)


class LocalTaskQueue:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.q = queue.Queue()
        self.max_retries = 3
        self.timeout_sec = 3600  # 1 hour max per pipeline task to prevent hanging

        self.worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="OpenClaw-Worker"
        )
        self.worker_thread.start()
        _logger.info("🔧 [TaskQueue] 背景任務佇列已啟動 (單線程防 OOM 機制)")

    def _quarantine_file(self, task: dict, error_msg: str):
        filepath = task.get("filepath")
        skill = task.get("skill")
        if not filepath or not skill or not os.path.exists(filepath):
            return

        quarantine_dir = os.path.join(_workspace_root, "data", "quarantine", skill)
        os.makedirs(quarantine_dir, exist_ok=True)

        filename = os.path.basename(filepath)
        dest_path = os.path.join(quarantine_dir, filename)

        try:
            shutil.move(filepath, dest_path)
            _logger.error("☠️ [DLQ] 任務多次失敗，已隔離毒藥檔案: %s", dest_path)

            log_path = os.path.join(quarantine_dir, "quarantine_log.json")
            entry = {
                "timestamp": datetime.now().isoformat(),
                "filename": filename,
                "original_path": filepath,
                "skill": skill,
                "error": error_msg,
                "attempts": task.get("retry_count", 0),
            }

            # Simple append to JSON Lines file for quarantine logs
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            try:
                from core.telegram_bot import send_message

                send_message(f"☠️ [隔離區] 發現毒藥檔案！\n已隔離: {filename}\n原因: {error_msg}")
            except ImportError:
                pass

        except Exception as e:
            _logger.error("隔離檔案失敗 (%s): %s", filepath, e, exc_info=True)

    def _worker_loop(self):
        while True:
            try:
                task = self.q.get()
                if task is None:
                    break  # Poison pill to stop the thread

                name = task.get("name", "Unknown Task")
                cmd = task.get("cmd")
                cwd = task.get("cwd")
                retry_count = task.get("retry_count", 0)

                _logger.info(
                    "▶️ [TaskQueue] 開始執行任務: %s (嘗試次數: %d/%d)",
                    name,
                    retry_count + 1,
                    self.max_retries,
                )
                _logger.debug("👉 指令: %s", " ".join(cmd))

                start_time = time.time()
                try:
                    # Execute with timeout to prevent Playwright/Selenium deadlocks
                    result = subprocess.run(cmd, cwd=cwd, timeout=self.timeout_sec)
                    elapsed = time.time() - start_time

                    if result.returncode == 0:
                        msg = f"✅ [TaskQueue] 任務成功完成: {name} (耗時 {elapsed:.1f}s)"
                        _logger.info(msg)
                        try:
                            from core.telegram_bot import send_message

                            send_message(msg)
                        except ImportError:
                            pass
                    else:
                        msg = f"❌ [TaskQueue] 任務執行失敗 (Exit Code {result.returncode}): {name}"
                        _logger.error(msg)
                        self._handle_failure(task, msg)

                except subprocess.TimeoutExpired:
                    msg = f"⏱️ [TaskQueue] 任務執行超時 (> {self.timeout_sec}s): {name}"
                    _logger.error(msg)
                    self._handle_failure(task, msg)

            except Exception as e:
                _logger.error("❌ [TaskQueue] 任務執行發生嚴重錯誤: %s", e, exc_info=True)
            finally:
                self.q.task_done()

    def _handle_failure(self, task: dict, error_msg: str):
        task["retry_count"] = task.get("retry_count", 0) + 1
        name = task.get("name", "Unknown Task")

        if task["retry_count"] >= self.max_retries:
            _logger.error("🚫 [TaskQueue] 達到最大重試次數，放棄任務: %s", name)
            self._quarantine_file(task, error_msg)
        else:
            _logger.warning("🔄 [TaskQueue] 準備重試任務 (將排入佇列尾端): %s", name)
            self.q.put(task)

            try:
                from core.telegram_bot import send_message

                send_message(error_msg + f"\n將進行第 {task['retry_count'] + 1} 次重試...")
            except ImportError:
                pass

    def enqueue(
        self,
        name: str,
        cmd: List[str],
        cwd: str,
        filepath: Optional[str] = None,
        skill: Optional[str] = None,
    ):
        """
        Add a task to the queue.
        """
        self.q.put(
            {
                "name": name,
                "cmd": cmd,
                "cwd": cwd,
                "filepath": filepath,
                "skill": skill,
                "retry_count": 0,
            }
        )
        _logger.info("📥 [TaskQueue] 任務已排入佇列 (等候中: %d): %s", self.q.qsize(), name)

    def join(self):
        """Block until all tasks are completed."""
        self.q.join()


# Global instance
task_queue = LocalTaskQueue()
