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


def run_pipelines() -> None:
    """Run all skills sequentially, respecting a preferred order."""
    if not _acquire_lock():
        sys.exit(0)

    try:
        _logger.info("開始執行全域管線排程...")

        try:
            from core.services.inbox_daemon import SystemInboxDaemon

            _logger.info("掃描 Inbox 分發新檔案...")
            SystemInboxDaemon().scan_all()
        except Exception as e:
            _logger.error(f"Inbox 掃描發生錯誤: {e}")

        skills_dir = os.path.join(_workspace_root, "skills")

        # 定義優先執行的順序
        preferred_order = [
            "doc_parser",
            "audio_transcriber",
            "proofreader",
            "smart_highlighter",
        ]

        # 尋找所有包含 run_all.py 的 skill
        available_skills = set()
        if os.path.exists(skills_dir):
            for item in os.listdir(skills_dir):
                if os.path.isfile(os.path.join(skills_dir, item, "scripts", "run_all.py")):
                    available_skills.add(item)

        # 決定最終執行順序 (先跑 priority，再跑其他的)
        execution_queue = []
        for p_skill in preferred_order:
            if p_skill in available_skills:
                execution_queue.append(p_skill)
                available_skills.remove(p_skill)

        execution_queue.extend(sorted(available_skills))

        for skill_name in execution_queue:
            script_path = os.path.join(skills_dir, skill_name, "scripts", "run_all.py")
            _logger.info(f"啟動 {skill_name}...")
            try:
                # 檢查該 script 是否支援 --process-all 或是否為 PipelineBase
                with open(script_path, encoding="utf-8") as f:
                    content = f.read()

                cmd = [sys.executable, script_path]
                if "PipelineBase" in content or "--process-all" in content:
                    cmd.append("--process-all")

                result = subprocess.run(cmd)
                if result.returncode not in (0, 1):
                    _logger.warning(f"{skill_name} 退出狀態: {result.returncode}")
            except Exception as e:
                _logger.error(f"執行 {skill_name} 發生錯誤: {e}")

        _logger.info("全域管線排程結束。")

    finally:
        _release_lock()


if __name__ == "__main__":
    run_pipelines()
