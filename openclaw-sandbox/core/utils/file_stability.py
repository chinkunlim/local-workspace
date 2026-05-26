"""
core/utils/file_stability.py
============================
Provides FileStabilityPoller for debouncing file arrival events.
Monitors a file's size until it remains unchanged for a specified interval,
then triggers a callback.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Callable

_logger = logging.getLogger("OpenClaw.FileStability")


class FileStabilityPoller:
    """
    Debounces file arrival/modification events by polling file size.
    Triggers the callback only when the file size is stable (unchanged)
    over a poll interval and > 0 bytes.
    """

    def __init__(self, poll_interval_sec: float = 2.0, timeout_sec: float = 600.0):
        self.poll_interval_sec = poll_interval_sec
        self.timeout_sec = timeout_sec
        self._lock = threading.RLock()
        self._debounce_events: dict[str, threading.Event] = {}

    def schedule_trigger(self, filepath: str, callback: Callable[[str], None]) -> None:
        """
        Cancel any existing poll thread for this filepath,
        then start a fresh one with its own stop Event.
        """
        with self._lock:
            existing_event = self._debounce_events.get(filepath)
            if existing_event:
                existing_event.set()
            stop_event = threading.Event()
            self._debounce_events[filepath] = stop_event

        t = threading.Thread(
            target=self._wait_and_trigger,
            args=(filepath, stop_event, callback),
            daemon=True,
        )
        t.start()

    def _wait_and_trigger(
        self, filepath: str, stop_event: threading.Event, callback: Callable[[str], None]
    ) -> None:
        prev_size = -1
        elapsed = 0.0

        while elapsed < self.timeout_sec:
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

            time.sleep(self.poll_interval_sec)
            elapsed += self.poll_interval_sec
        else:
            _logger.error("等待超時 (%ss)，放棄觸發: %s", self.timeout_sec, filepath)
            return

        # Clean up debounce map
        with self._lock:
            if self._debounce_events.get(filepath) is stop_event:
                self._debounce_events.pop(filepath, None)

        callback(filepath)
