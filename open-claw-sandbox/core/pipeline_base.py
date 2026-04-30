"""
PipelineBase — OpenClaw Shared Base Class (V2.3)
=================================================
共用所有 Skill 的 OOP 基底。

關鍵升級（V2.3）：
- 整合 SessionState 追蹤：所有控制狀態 (RUNNING/PAUSED/STOPPED/
  FORCE_STOPPED/COMPLETED/FAILED) 持久化寫入 state/session.json
- error() 方法現在在 log 檔中附加完整 Python traceback (exc_info=True)
- build_logger 以 DEBUG 層級寫入檔案，INFO 層級印至 console

關鍵升級（V2.2）：
- 新增 `skill_name` keyword 參數（預設 "audio-transcriber"，保持向後相容）
- `base_dir` 動態對應 `data/{skill_name}/`
- 所有現有 audio-transcriber phase 腳本無需修改即可繼續運行

用法（audio-transcriber，不需改動）:
    super().__init__("p1", "Transcription")   # skill_name 預設 audio-transcriber

用法（doc-parser）:
    super().__init__("phase1a", "PDF Diagnostic", skill_name="doc-parser")
"""

import logging
import os
import signal
import sys
import threading
from typing import Any, Dict, List, Optional
import uuid

import psutil

from .config_manager import ConfigManager
from .config_validation import ConfigValidator
from .llm_client import TRACE_ID_VAR, OllamaClient
from .log_manager import build_logger
from .path_builder import PathBuilder
from .session_state import SessionState, write_session_state
from .state_manager import StateManager


class PipelineBase:
    def __init__(
        self,
        phase_key: str,
        phase_name: str,
        skill_name: str = "audio-transcriber",  # ← V2.2 新增，向後相容預設值
        logger=None,
    ):
        self.phase_key = phase_key
        self.phase_name = phase_name
        self.skill_name = skill_name
        self.logger = logger

        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_workspace = os.path.abspath(os.path.join(script_dir, ".."))
        self.workspace_root = os.environ.get("WORKSPACE_DIR", default_workspace)

        self.path_builder = PathBuilder(self.workspace_root, skill_name)
        self.config_manager = ConfigManager(self.workspace_root, skill_name)
        self.base_dir = self.path_builder.base_dir
        self.dirs = self.path_builder.phase_dirs
        self.config_dir = self.path_builder.config_dir
        self.prompt_file = self.path_builder.prompt_file
        self.config_file = self.path_builder.config_file
        self.log_file = self.path_builder.log_file

        # Ensure base_dir and log parent exist before logging
        self.path_builder.ensure_directories()
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        self.state_manager = StateManager(self.base_dir, skill_name=skill_name)
        runtime_cfg = self.config_manager.get_section("runtime", {})
        ollama_cfg = runtime_cfg.get("ollama", {}) if isinstance(runtime_cfg, dict) else {}
        fallback_model = self.config_manager.get_nested("models", "fallback")
        self.llm = OllamaClient(
            api_url=ConfigValidator.require(ollama_cfg.get("api_url"), "runtime.ollama.api_url"),
            timeout=ollama_cfg.get("timeout_seconds", 600),
            retries=ollama_cfg.get("retries", 3),
            backoff_seconds=ollama_cfg.get("backoff_seconds", 5.0),
            fallback_model=fallback_model,
        )
        self.stop_requested = False
        self.pause_requested = False

        # Generate and register a Trace ID for distributed log correlation (#12)
        self.trace_id = TRACE_ID_VAR.get() or str(uuid.uuid4())
        TRACE_ID_VAR.set(self.trace_id)

        self._setup_logging()
        self._setup_signals()

        # Record session start
        self._write_session_state(SessionState.RUNNING)

    # ------------------------------------------------------------------ #
    #  Logging                                                             #
    # ------------------------------------------------------------------ #

    def _setup_logging(self) -> None:
        self.logger = self.logger or build_logger(
            f"OpenClaw.{self.skill_name}",
            log_file=self.log_file,
            file_level=logging.DEBUG,  # Full detail in log file
            console=False,  # Console output handled by self.log()
        )

    def log(self, msg: str, level: str = "info") -> None:
        if "tqdm" in sys.modules:
            import tqdm

            tqdm.tqdm.write(msg)
        else:
            print(msg)

        if self.logger:
            if level == "info":
                self.logger.info(msg)
            elif level == "warn":
                self.logger.warning(msg)
            elif level == "error":
                # exc_info=True captures the active exception traceback into the log file
                self.logger.error(msg, exc_info=True)

    def info(self, msg: str) -> None:
        self.log(msg, level="info")

    def warning(self, msg: str) -> None:
        self.log(msg, level="warn")

    def error(self, msg: str) -> None:
        self.log(msg, level="error")

    # ------------------------------------------------------------------ #
    #  Session State                                                        #
    # ------------------------------------------------------------------ #

    def _write_session_state(
        self,
        state: SessionState,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist the current control state to state/session.json."""
        try:
            state_dir = os.path.join(self.base_dir, "state")
            write_session_state(
                state_dir,
                state,
                context=context,
                skill_name=self.skill_name,
            )
        except Exception:
            pass  # Session state write must never crash the pipeline

    # ------------------------------------------------------------------ #
    #  Signal Handling (Ctrl+C)                                            #
    # ------------------------------------------------------------------ #

    def _setup_signals(self):
        """
        雙層 SIGINT 處理：
        - 第一次 Ctrl+C → 詢問 [P] 暫停 / [S] 停止
        - 第二次 Ctrl+C（在問答期間再按）→ 強制終止
        強制終止不寫 Checkpoint，暫停才寫。
        """

        def handle_interrupt(signum, frame):
            if self.stop_requested:
                self.log("\n🚨 [緊急中斷] 偵測到連續中斷指令，執行強制停機！", "error")
                os._exit(1)

            self.stop_requested = True
            self.pause_requested = False

            if not sys.stdin.isatty():
                self.log(
                    "\n⏸️ [背景服務模式] 收到暫停信號，將於當前任務完成後自動切斷並保存斷點...",
                    "warn",
                )
                self.pause_requested = True
                self._write_session_state(SessionState.PAUSED)
                return

            print("\n")
            print("●" * 50)
            print("🛑  收到中斷指令！請選擇：")
            print("    [P] 暫停 — 儲存進度，稍後下次可從此繼續")
            print("    [S] 停止 — 無儲存進度，完整停止")
            print("●" * 50)

            try:
                choice = input("    請輸入 (P/S) [Enter 預設 = S]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\n🚨 強制退出。")
                self._write_session_state(SessionState.FORCE_STOPPED)
                os._exit(1)

            if choice == "p":
                self.pause_requested = True
                self._write_session_state(SessionState.PAUSED)
                print("💾 已選擇暫停，處理完目前檔案後將儲存進度。")
            else:
                self.pause_requested = False
                self._write_session_state(SessionState.STOPPED)
                print("🛑 已選擇停止，處理完目前檔案後將退出（不儲存進度）。")

        signal.signal(signal.SIGINT, handle_interrupt)
        signal.signal(signal.SIGTERM, handle_interrupt)

    # ------------------------------------------------------------------ #
    #  Hardware Health Check                                               #
    # ------------------------------------------------------------------ #

    def check_system_health(self) -> bool:
        """Monitor RAM, Disk, Temp. Return True if graceful stop is needed."""
        hardware_cfg = self.config_manager.get_section("hardware", {})
        ram_cfg = hardware_cfg.get("ram", {}) if isinstance(hardware_cfg, dict) else {}
        temp_cfg = hardware_cfg.get("temperature", {}) if isinstance(hardware_cfg, dict) else {}
        battery_cfg = hardware_cfg.get("battery", {}) if isinstance(hardware_cfg, dict) else {}
        disk_cfg = hardware_cfg.get("disk", {}) if isinstance(hardware_cfg, dict) else {}

        warning_mb = ConfigValidator.require_int(
            ram_cfg.get("warning_mb"), "hardware.ram.warning_mb", min_value=1
        )
        critical_mb = ConfigValidator.require_int(
            ram_cfg.get("critical_mb"), "hardware.ram.critical_mb", min_value=1
        )
        warning_temp = ConfigValidator.require_int(
            temp_cfg.get("warning_celsius"), "hardware.temperature.warning_celsius", min_value=1
        )
        critical_temp = ConfigValidator.require_int(
            temp_cfg.get("critical_celsius"), "hardware.temperature.critical_celsius", min_value=1
        )
        critical_disk_mb = ConfigValidator.require_int(
            disk_cfg.get("min_free_mb"), "hardware.disk.min_free_mb", min_value=1
        )
        low_battery_percent = ConfigValidator.require_int(
            battery_cfg.get("low_percent"),
            "hardware.battery.low_percent",
            min_value=1,
            max_value=100,
        )
        critical_battery_percent = ConfigValidator.require_int(
            battery_cfg.get("critical_percent"),
            "hardware.battery.critical_percent",
            min_value=1,
            max_value=100,
        )

        available_ram = psutil.virtual_memory().available / (1024 * 1024)
        disk_free = psutil.disk_usage(self.base_dir).free / (1024 * 1024)

        battery = getattr(psutil, "sensors_battery", lambda: None)()
        bat_percent = battery.percent if battery else 100
        power_plugged = battery.power_plugged if battery else True

        current_temp = None
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                core_temps = [e.current for name, es in temps.items() for e in es]
                if core_temps:
                    current_temp = max(core_temps)

        # Critical Exit
        if available_ram < critical_mb:
            self.log(f"💥 [RAM 耗盡] 可用僅 {available_ram:.0f}MB！強制停機！", "error")
            os._exit(1)
        elif disk_free < critical_disk_mb:
            self.log(f"💾 [空間耗盡] 磁碟空間剩餘 {disk_free:.0f}MB！強制停機！", "error")
            os._exit(1)
        elif not power_plugged and bat_percent < critical_battery_percent:
            self.log(f"🪫 [電力極低] 電量僅 {bat_percent}% 且未充電！", "error")
            os._exit(1)
        elif current_temp and current_temp >= critical_temp:
            self.log(f"🔥 [高溫危險] 溫度 {current_temp}°C！", "error")
            os._exit(1)

        # Graceful Warning
        if available_ram < warning_mb or (not power_plugged and bat_percent < low_battery_percent):
            if not self.stop_requested:
                reason = "RAM 偏低" if available_ram < warning_mb else "電力不足"
                self.log(f"🚨 [資源預警] {reason}，啟動暫停 (Pause) 儲存進度...", "warn")
                self.stop_requested = True
                self.pause_requested = True
        elif current_temp and current_temp >= warning_temp:
            if not self.stop_requested:
                self.log(f"🌡️ [高溫預警] 溫度 {current_temp}°C，暫停 (Pause) 儲存進度...", "warn")
                self.stop_requested = True
                self.pause_requested = True

        return self.stop_requested

    # ------------------------------------------------------------------ #
    #  Config & Prompt Loading                                             #
    # ------------------------------------------------------------------ #

    def get_prompt(self, section_title: str) -> str:
        """Parse prompt.md — format: ## <section_title>"""
        import re

        if not self.prompt_file or not os.path.exists(self.prompt_file):
            return ""
        with open(self.prompt_file, encoding="utf-8") as f:
            lines = f.readlines()

        prompt_lines = []
        capture = False
        for line in lines:
            if line.startswith(f"## {section_title}"):
                capture = True
                continue
            elif re.match(r"^## .+", line) and capture:
                # Any new ## heading terminates the current section
                break
            elif line.strip() == "---" and capture:
                # Horizontal rules also act as section separators
                break
            if capture:
                prompt_lines.append(line)
        return "".join(prompt_lines).strip()

    def get_config(self, phase_name: str, subject_name: str = None) -> Dict[str, Any]:
        """Read config.yaml profile."""
        return self.config_manager.get_profile(
            phase_name.lower().replace(" ", ""), subject_name=subject_name
        )

    # ------------------------------------------------------------------ #
    #  Task Management (audio-transcriber pattern; optional for other skills)     #
    # ------------------------------------------------------------------ #

    def get_tasks(
        self,
        prev_phase_key: str = None,
        force: bool = False,
        subject_filter: str = None,
        file_filter: str = None,
        single_mode: bool = False,
        resume_from: Dict[str, str] = None,
    ) -> List[Dict]:
        """
        收集待處理任務清單。
        audio-transcriber 使用，doc-parser 可不使用（改用 queue_manager）。
        """
        self.state_manager.sync_physical_files()
        self.state_manager.check_output_hashes(self.dirs)

        all_tasks: List[Dict] = []
        done_tasks: List[Dict] = []

        for subj, files in self.state_manager.state.items():
            if subject_filter and subj != subject_filter:
                continue
            for fname, status in files.items():
                if prev_phase_key and status.get(prev_phase_key) != "✅":
                    continue
                task = {"subject": subj, "filename": fname, "status": status}
                if status.get(self.phase_key) == "✅":
                    if force:
                        all_tasks.append(task)
                    else:
                        done_tasks.append(task)
                else:
                    all_tasks.append(task)

        all_tasks.sort(key=lambda t: (t["subject"], t["filename"]))
        done_tasks.sort(key=lambda t: (t["subject"], t["filename"]))

        if done_tasks:
            reprocess_set = self._batch_select_reprocess(done_tasks)
            skipped = len(done_tasks) - len(reprocess_set)
            if skipped > 0:
                self.log(f"⏭️  共 {skipped} 個已完成檔案被跳過。")
            all_tasks = sorted(
                all_tasks + list(reprocess_set.values()),
                key=lambda t: (t["subject"], t["filename"]),
            )

        if resume_from:
            cp_subj = resume_from.get("subject", "")
            cp_fname = resume_from.get("filename", "")
            start_idx = 0
            for i, t in enumerate(all_tasks):
                if t["subject"] == cp_subj and t["filename"] == cp_fname:
                    start_idx = i
                    break
            if start_idx > 0:
                self.log(f"➩️  斷點續傳：已跳過 {start_idx} 個先前完成的任務。")
            all_tasks = all_tasks[start_idx:]

        if file_filter:
            start_idx = 0
            for i, t in enumerate(all_tasks):
                if t["filename"] == file_filter:
                    start_idx = i
                    break

            if single_mode:
                if start_idx < len(all_tasks) and all_tasks[start_idx]["filename"] == file_filter:
                    all_tasks = [all_tasks[start_idx]]
                    self.log(f"🎯  單檔模式：僅執行 {file_filter}")
                else:
                    all_tasks = []
                    self.log(f"❌  單檔模式：找不到目標檔案 {file_filter}", "warn")
            else:
                if start_idx > 0:
                    self.log(f"➩️  指定起點：從 {file_filter} 開始執行。")
                all_tasks = all_tasks[start_idx:]

        return all_tasks

    def process_tasks(self, process_callback, **kwargs):
        """
        Generic task iteration loop with built-in health checks and checkpoints.
        process_callback should accept: (idx, task, total_tasks) and return True on success.
        """
        tasks = self.get_tasks(**kwargs)
        if not tasks:
            self.log(f"📋 {self.phase_name} 沒有待處理的檔案。")
            return

        self.log(f"📋 {self.phase_name} 共有 {len(tasks)} 個檔案待處理。")

        for idx, task in enumerate(tasks, 1):
            if self.check_system_health():
                break

            process_callback(idx, task, len(tasks))

            if self.stop_requested:
                if self.pause_requested and idx < len(tasks):
                    next_task = tasks[idx]
                    self.save_checkpoint(next_task["subject"], next_task["filename"])
                break

    def _batch_select_reprocess(self, done_tasks: List[Dict]) -> Dict[int, Dict]:
        """互動式批量選擇已完成任務是否重跑。"""
        from core.cli_menu import batch_select_tasks

        return batch_select_tasks(done_tasks, header=f"[{self.phase_key.upper()}] 已完成的檔案")

    # ------------------------------------------------------------------ #
    #  Checkpoint (delegates to StateManager)                             #
    # ------------------------------------------------------------------ #

    def save_checkpoint(self, subject: str, filename: str):
        self.state_manager.save_checkpoint(subject, filename, self.phase_key)
        self.log(f"💾 已儲存 Checkpoint：[{subject}] {filename} @ {self.phase_key.upper()}")

    def load_checkpoint(self) -> Optional[Dict]:
        return self.state_manager.load_checkpoint()

    def clear_checkpoint(self):
        self.state_manager.clear_checkpoint()

    # ------------------------------------------------------------------ #
    #  Utilities                                                           #
    # ------------------------------------------------------------------ #

    def create_spinner(self, desc: str):
        from tqdm import tqdm

        stop_tick = threading.Event()
        pbar = tqdm(total=100, desc=desc, bar_format="{l_bar}{bar}| [{elapsed}]")

        def ticker():
            while not stop_tick.wait(1.0):
                pbar.refresh()

        t = threading.Thread(target=ticker, daemon=True)
        t.start()
        return pbar, stop_tick, t

    def finish_spinner(self, pbar, stop_tick, t):
        stop_tick.set()
        t.join()
        pbar.n = 100
        pbar.bar_format = "{l_bar}{bar}| [完成: {elapsed}]"
        pbar.refresh()
        pbar.close()
