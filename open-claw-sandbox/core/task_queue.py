# -*- coding: utf-8 -*-
"""
core/task_queue.py — Single-Threaded Task Queue for OOM Prevention
===================================================================
A lightweight, background job queue that ensures Open Claw skills run
sequentially. This replaces the old concurrent `subprocess.Popen` logic
in `inbox_daemon.py` which could easily crash the system (OOM) when
multiple files arrive simultaneously.
"""

import os
import sys
import queue
import threading
import subprocess
import time
from typing import Dict, Any, List

class LocalTaskQueue:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LocalTaskQueue, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.q = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="OpenClaw-Worker")
        self.worker_thread.start()
        print("🔧 [TaskQueue] 背景任務佇列已啟動 (單線程防 OOM 機制)")

    def _worker_loop(self):
        while True:
            try:
                task = self.q.get()
                if task is None:
                    break  # Poison pill to stop the thread

                name = task.get("name", "Unknown Task")
                cmd = task.get("cmd")
                cwd = task.get("cwd")

                print(f"\n▶️ [TaskQueue] 開始執行任務: {name}")
                print(f"👉 指令: {' '.join(cmd)}")
                
                # Execute the subprocess synchronously in this worker thread
                start_time = time.time()
                result = subprocess.run(cmd, cwd=cwd)
                elapsed = time.time() - start_time

                if result.returncode == 0:
                    print(f"✅ [TaskQueue] 任務成功完成: {name} (耗時 {elapsed:.1f}s)")
                else:
                    print(f"❌ [TaskQueue] 任務執行失敗 (Exit Code {result.returncode}): {name}")

            except Exception as e:
                print(f"❌ [TaskQueue] 任務執行發生嚴重錯誤: {e}")
            finally:
                self.q.task_done()

    def enqueue(self, name: str, cmd: List[str], cwd: str):
        """
        Add a task to the queue.
        """
        self.q.put({
            "name": name,
            "cmd": cmd,
            "cwd": cwd
        })
        print(f"📥 [TaskQueue] 任務已排入佇列 (等候中: {self.q.qsize()}): {name}")

    def join(self):
        """Block until all tasks are completed."""
        self.q.join()

# Global instance
task_queue = LocalTaskQueue()
