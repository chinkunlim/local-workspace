"""
core/run_all_pipelines.py — 全域管線執行器
========================================
依序執行 doc_parser 與 audio_transcriber，
確保兩個重量級模型不會同時執行導致 OOM。

B-3 Fix: Uses a PID lockfile to prevent concurrent invocations spawned by
rapid /run commands from the Telegram bot.
"""

import logging
import os
import subprocess
import sys

_core_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.environ.get(
    "WORKSPACE_DIR", os.path.abspath(os.path.join(_core_dir, "..", ".."))
)
_LOCK_FILE = os.path.join(_workspace_root, "logs", "run_pipelines.lock")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RunAll] %(message)s",
    datefmt="%H:%M:%S",
)
_logger = logging.getLogger("OpenClaw.RunAll")


def _acquire_lock() -> bool:
    """Write current PID to lockfile. Return False if already locked by a live process."""
    if os.path.exists(_LOCK_FILE):
        try:
            with open(_LOCK_FILE) as f:
                existing_pid = int(f.read().strip())
            os.kill(existing_pid, 0)  # raises if process is dead
            _logger.warning("另一個管線排程器正在執行 (PID %s)，退出以防止重複執行。", existing_pid)
            return False
        except (ValueError, ProcessLookupError, PermissionError):
            pass  # Stale lockfile — safe to overwrite

    os.makedirs(os.path.dirname(_LOCK_FILE), exist_ok=True)
    with open(_LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def _release_lock() -> None:
    """Remove the PID lockfile on clean exit."""
    try:
        os.unlink(_LOCK_FILE)
    except OSError:
        pass


def _notify_timeout(pipeline_name: str) -> None:
    """Try to send a Telegram notification for timeouts."""
    try:
        from core.services.telegram_bot import send_message

        send_message(f"🚨 [Open Claw] {pipeline_name} 執行超時 (> 2 小時)，已強制中斷並釋放鎖。")
    except ImportError:
        pass


def run_pipelines() -> None:
    """Run doc_parser then audio_transcriber sequentially."""
    if not _acquire_lock():
        sys.exit(0)

    try:
        _logger.info("開始執行全域管線排程...")

        doc_script = os.path.join(_workspace_root, "skills", "doc_parser", "scripts", "run_all.py")
        audio_script = os.path.join(
            _workspace_root, "skills", "audio_transcriber", "scripts", "run_all.py"
        )

        # 1. doc_parser (--process-all skips interactive menu)
        _logger.info("啟動 doc_parser...")
        try:
            result_doc = subprocess.run([sys.executable, doc_script, "--process-all"], timeout=7200)
            if result_doc.returncode not in (0, 1):  # 1 = clean SIGTERM/sys.exit
                _logger.warning("doc_parser 退出狀態: %s", result_doc.returncode)
        except subprocess.TimeoutExpired:
            _logger.error("🚨 doc_parser 執行超時 (> 2h)，強制中斷。")
            _notify_timeout("doc_parser")
            sys.exit(1)

        # 2. audio_transcriber
        _logger.info("啟動 audio_transcriber...")
        try:
            result_audio = subprocess.run([sys.executable, audio_script], timeout=7200)
            if result_audio.returncode not in (0, 1):
                _logger.warning("audio_transcriber 退出狀態: %s", result_audio.returncode)
        except subprocess.TimeoutExpired:
            _logger.error("🚨 audio_transcriber 執行超時 (> 2h)，強制中斷。")
            _notify_timeout("audio_transcriber")
            sys.exit(1)

        _logger.info("全域管線排程結束。")

    finally:
        _release_lock()


if __name__ == "__main__":
    run_pipelines()
