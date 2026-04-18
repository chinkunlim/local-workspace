# -*- coding: utf-8 -*-
"""
Execution Manager
=================
Safely spawns, streams, and terminates Python subprocesses.
Ensures safe interrupts and no zombie processes.

V2.0 Changes:
- Replaced single-task model with a sequential Job Queue (queue.Queue).
- Added same-skill deduplication: a task_name already in queue is rejected.
- Added get_queue_status() for /api/queue introspection.
- Worker thread processes jobs one at a time to preserve RAM safety.
"""
import subprocess
import threading
import queue
import collections
import time
import datetime
import json
import os
import psutil


class ExecutionManager:
    def __init__(self):
        self._process = None
        self._log_buffer = collections.deque(maxlen=2000)
        self._lock = threading.Lock()
        self._current_task_name = None
        self._total_lines_read = 0

        # Lightweight re-run state log (for /api/highlight, /api/synthesize)
        self._rerun_state_path = os.path.join(
            os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))),
            "data", ".rerun_state.json"
        )
        self._job_queue: queue.Queue = queue.Queue()
        self._queued_names: list[str] = []   # ordered list for introspection + dedup
        self._worker = threading.Thread(target=self._process_queue, daemon=True)
        self._worker.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue_task(self, task_name: str, command: list, cwd: str) -> bool:
        """
        Add a task to the sequential job queue.

        Returns:
            True  — task enqueued successfully.
            False — rejected because a task with the same name is already
                    in the queue or currently running.
        """
        with self._lock:
            if task_name in self._queued_names or self._current_task_name == task_name:
                return False  # same-skill dedup
            self._queued_names.append(task_name)

        self._log_buffer.append(f"📥 [Queue] 任務加入排隊: {task_name}\n")
        self._job_queue.put((task_name, command, cwd))
        return True

    # Keep start_task as a backwards-compatible alias for immediate single tasks
    def start_task(self, task_name: str, command: list, cwd: str) -> bool:
        """Backwards-compatible: immediately enqueues (same dedup rules apply)."""
        return self.enqueue_task(task_name, command, cwd)

    def get_queue_status(self) -> dict:
        """Return pending queue contents for /api/queue."""
        with self._lock:
            return {
                "pending": list(self._queued_names),
                "running": self._current_task_name if self.is_running() else None,
            }

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def get_status(self) -> dict:
        with self._lock:
            return {
                "running": self.is_running(),
                "task_name": self._current_task_name if self.is_running() else None,
            }

    def get_logs(self, cursor: int) -> dict:
        with self._lock:
            lines = list(self._log_buffer)
            total = self._total_lines_read
            if cursor == 0 or total - cursor >= len(lines):
                new_lines = lines
            else:
                new_idx = len(lines) - (total - cursor)
                new_lines = lines[new_idx:]
            return {"lines": new_lines, "cursor": total}

    def terminate_task(self):
        """Send SIGTERM to the currently running process and flush the queue."""
        with self._lock:
            # Clear pending queue
            while not self._job_queue.empty():
                try:
                    self._job_queue.get_nowait()
                    self._job_queue.task_done()
                except queue.Empty:
                    break
            self._queued_names.clear()

            if not self.is_running():
                return

            self._log_buffer.append(f"\n⚠️ [System] 寄出中止信號 (SIGTERM) 給 {self._current_task_name}...\n")
            try:
                parent = psutil.Process(self._process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                _, alive = psutil.wait_procs(parent.children(recursive=True) + [parent], timeout=3)
                for p in alive:
                    p.kill()
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                self._log_buffer.append(f"❌ [System] 強制退出時發生錯誤: {e}\n")

    def _write_rerun_state(self, task_name: str, status: str, error: str = None):
        """Append a lightweight state record for Re-run tasks to data/.rerun_state.json."""
        record = {
            "task": task_name,
            "status": status,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        if error:
            record["error"] = error
        try:
            os.makedirs(os.path.dirname(self._rerun_state_path), exist_ok=True)
            existing = []
            if os.path.exists(self._rerun_state_path):
                with open(self._rerun_state_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.append(record)
            existing = existing[-200:]  # Keep last 200 records
            # Write via temp file (best-effort atomic)
            import tempfile
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self._rerun_state_path))
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(existing, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self._rerun_state_path)
        except Exception:
            pass  # Rerun state logging must never block the pipeline

    def pause_task(self):
        with self._lock:
            if not self.is_running():
                return
            self._log_buffer.append(f"\n⚠️ [System] 寄出暫停信號 (SIGINT) 給 {self._current_task_name}...\n")
            try:
                import signal
                os.kill(self._process.pid, signal.SIGINT)
            except Exception as e:
                self._log_buffer.append(f"❌ [System] 暫停任務時發生錯誤: {e}\n")

    # ------------------------------------------------------------------
    # Queue worker (runs in background daemon thread)
    # ------------------------------------------------------------------

    def _process_queue(self):
        """Background worker: consume and run jobs sequentially."""
        while True:
            task_name, command, cwd = self._job_queue.get()
            try:
                self._run_job(task_name, command, cwd)
            finally:
                with self._lock:
                    if task_name in self._queued_names:
                        self._queued_names.remove(task_name)
                self._job_queue.task_done()

    def _run_job(self, task_name: str, command: list, cwd: str):
        """Synchronously execute one job, streaming stdout to log buffer."""
        with self._lock:
            self._log_buffer.clear()
            self._total_lines_read = 0
            self._current_task_name = task_name
            self._log_buffer.append(f"🟢 [System] 啟動任務: {task_name}\n")

        env = os.environ.copy()
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + env.get("PATH", "")
        env["PYTHONUNBUFFERED"] = "1"

        try:
            proc = subprocess.Popen(
                command, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, env=env,
            )
            with self._lock:
                self._process = proc
            self._write_rerun_state(task_name, "RUNNING")

            for line in iter(proc.stdout.readline, ""):
                with self._lock:
                    self._log_buffer.append(line)
                    self._total_lines_read += 1
            proc.stdout.close()
            proc.wait()

            with self._lock:
                retcode = proc.returncode
                if retcode == 0:
                    self._log_buffer.append(f"\n✅ [System] {task_name} 執行完畢 (Exit 0)\n")
                    self._write_rerun_state(task_name, "COMPLETED")
                elif retcode in (-15, 143):
                    self._log_buffer.append(f"\n⏹️ [System] {task_name} 已被使用者強制中止\n")
                    self._write_rerun_state(task_name, "CANCELLED")
                else:
                    self._log_buffer.append(f"\n❌ [System] {task_name} 異常結束 (Exit {retcode})\n")
                    self._write_rerun_state(task_name, "FAILED", error=f"Exit {retcode}")

        except Exception as e:
            with self._lock:
                self._log_buffer.append(f"❌ [System] 無法啟動進程: {e}\n")
            self._write_rerun_state(task_name, "FAILED", error=str(e))
        finally:
            with self._lock:
                self._current_task_name = None
                self._process = None
