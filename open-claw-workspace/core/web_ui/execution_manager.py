# -*- coding: utf-8 -*-
"""
Execution Manager
Safely spawns, streams, and terminates Python subprocesses (queue_manager, run_all.py).
Ensures safe interrupts and no zombie processes.
"""
import subprocess
import threading
import collections
import time
import psutil

class ExecutionManager:
    def __init__(self):
        self._process = None
        self._log_buffer = collections.deque(maxlen=2000)
        self._lock = threading.Lock()
        self._current_task_name = None
        self._total_lines_read = 0

    def start_task(self, task_name: str, command: list, cwd: str) -> bool:
        with self._lock:
            if self.is_running():
                return False  # Already running
            
            self._log_buffer.clear()
            self._total_lines_read = 0
            self._current_task_name = task_name
            self._log_buffer.append(f"🟢 [System] 啟動任務: {task_name}\n")
            
            try:
                self._process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1 # Line buffered
                )
                
                # Start logging thread
                threading.Thread(target=self._read_stdout, args=(self._process,), daemon=True).start()
                return True
            except Exception as e:
                self._log_buffer.append(f"❌ [System] 無法啟動進程: {e}\n")
                return False

    def _read_stdout(self, proc):
        for line in iter(proc.stdout.readline, ''):
            with self._lock:
                self._log_buffer.append(line)
                self._total_lines_read += 1
        proc.stdout.close()
        proc.wait()
        with self._lock:
            retcode = proc.returncode
            if retcode == 0:
                self._log_buffer.append(f"\n✅ [System] {self._current_task_name} 執行完畢 (Exit 0)\n")
            elif retcode == -15 or retcode == 143:
                self._log_buffer.append(f"\n⏹️ [System] {self._current_task_name} 已被使用者強制中止\n")
            else:
                self._log_buffer.append(f"\n❌ [System] {self._current_task_name} 異常結束 (Exit {retcode})\n")

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def get_status(self) -> dict:
        with self._lock:
            return {
                "running": self.is_running(),
                "task_name": self._current_task_name if self.is_running() else None
            }

    def get_logs(self, cursor: int) -> dict:
        with self._lock:
            lines = list(self._log_buffer)
            total = self._total_lines_read
            
            # If cursor is 0, give full buffer.
            # If cursor > 0, calculate how many new lines to give.
            # (Note: due to maxlen clipping, if buffer wrapped, we might miss lines, but for tail streaming it works well enough)
            if cursor == 0 or total - cursor >= len(lines):
                new_lines = lines
            else:
                new_idx = len(lines) - (total - cursor)
                new_lines = lines[new_idx:]
                
            return {
                "lines": new_lines,
                "cursor": total
            }

    def terminate_task(self):
        with self._lock:
            if not self.is_running():
                return
            
            self._log_buffer.append(f"\n⚠️ [System] 寄出中止信號 (SIGTERM) 給 {self._current_task_name}...\n")
            try:
                # Use psutil to terminate children safely
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
