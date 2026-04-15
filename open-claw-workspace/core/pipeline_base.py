# -*- coding: utf-8 -*-
"""
PipelineBase — OpenClaw Shared Base Class (V2.2)
=================================================
共用所有 Skill 的 OOP 基底。

關鍵升級（V2.2）：
- 新增 `skill_name` keyword 參數（預設 "voice-memo"，保持向後相容）
- `base_dir` 動態對應 `data/{skill_name}/`
- 所有現有 voice-memo phase 腳本無需修改即可繼續運行

用法（voice-memo，不需改動）:
    super().__init__("p1", "Transcription")   # skill_name 預設 voice-memo

用法（pdf-knowledge）:
    super().__init__("phase1a", "PDF Diagnostic", skill_name="pdf-knowledge")
"""

import os
import signal
import sys
import psutil
import threading
from typing import Dict, Any, List, Optional

from .state_manager import StateManager
from .llm_client import OllamaClient


class PipelineBase:
    def __init__(
        self,
        phase_key: str,
        phase_name: str,
        skill_name: str = "voice-memo",   # ← V2.2 新增，向後相容預設值
        logger=None,
    ):
        self.phase_key = phase_key
        self.phase_name = phase_name
        self.skill_name = skill_name
        self.logger = logger

        # Determine workspace root
        # __file__ is core/pipeline_base.py → parent is core/ → parent is workspace root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_workspace = os.path.abspath(os.path.join(script_dir, ".."))
        self.workspace_root = os.environ.get("WORKSPACE_DIR", default_workspace)

        # Dynamic base_dir: data/{skill_name}/
        self.base_dir = os.path.join(self.workspace_root, "data", skill_name)

        # Phase directories (voice-memo convention; pdf-knowledge subclasses may override)
        self.dirs = {
            "p0": os.path.join(self.base_dir, "raw_data"),
            "p1": os.path.join(self.base_dir, "01_transcript"),
            "p2": os.path.join(self.base_dir, "02_proofread"),
            "p3": os.path.join(self.base_dir, "03_merged"),
            "p4": os.path.join(self.base_dir, "04_highlighted"),
            "p5": os.path.join(self.base_dir, "05_notion_synthesis"),
        }

        # For skills that have their own prompt file next to their scripts
        # (pdf-knowledge scripts set self.prompt_file themselves if they need one)
        self.config_dir = os.path.join(self.workspace_root, "skills", self.skill_name, "config")
        self.prompt_file = os.path.join(self.config_dir, "prompt.md")
        self.config_file = os.path.join(self.config_dir, "config.yaml")
        self.log_file = os.path.join(self.base_dir, "system.log")

        # Ensure base_dir and log parent exist before logging
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        self.state_manager = StateManager(self.base_dir)
        self.llm = OllamaClient()
        self.stop_requested = False
        self.pause_requested = False

        self._setup_logging()
        self._setup_signals()

    # ------------------------------------------------------------------ #
    #  Logging                                                             #
    # ------------------------------------------------------------------ #

    def _setup_logging(self):
        import logging
        from logging.handlers import RotatingFileHandler

        logger_name = f"OpenClaw.{self.skill_name}"
        logger = logging.getLogger(logger_name)
        if not logger.handlers:
            log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            file_handler = RotatingFileHandler(
                self.log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            file_handler.setFormatter(log_formatter)
            logger.setLevel(logging.INFO)
            logger.propagate = False
            logger.addHandler(file_handler)
        self.logger = logger

    def log(self, msg: str, level: str = "info"):
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
                self.logger.error(msg, exc_info=False)

    def info(self, msg: str):
        self.log(msg, level="info")

    def warning(self, msg: str):
        self.log(msg, level="warn")

    def error(self, msg: str):
        self.log(msg, level="error")

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
                os._exit(1)

            if choice == "p":
                self.pause_requested = True
                print("💾 已選擇暫停，處理完目前檔案後將儲存進度。")
            else:
                self.pause_requested = False
                print("🛑 已選擇停止，處理完目前檔案後將退出（不儲存進度）。")

        signal.signal(signal.SIGINT, handle_interrupt)

    # ------------------------------------------------------------------ #
    #  Hardware Health Check                                               #
    # ------------------------------------------------------------------ #

    def check_system_health(self) -> bool:
        """Monitor RAM, Disk, Temp. Return True if graceful stop is needed."""
        # Apple Silicon (darwin): Unified Memory + efficient Swap means lower thresholds
        # are needed to avoid false-positive pauses on 16GB machines running 14B models.
        warning_mb, critical_mb = (500, 200) if sys.platform == "darwin" else (4000, 2048)
        warning_temp, critical_temp = 85, 95

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
        elif disk_free < 200:
            self.log(f"💾 [空間耗盡] 磁碟空間剩餘 {disk_free:.0f}MB！強制停機！", "error")
            os._exit(1)
        elif not power_plugged and bat_percent < 5:
            self.log(f"🪫 [電力極低] 電量僅 {bat_percent}% 且未充電！", "error")
            os._exit(1)
        elif current_temp and current_temp >= critical_temp:
            self.log(f"🔥 [高溫危險] 溫度 {current_temp}°C！", "error")
            os._exit(1)

        # Graceful Warning
        if available_ram < warning_mb or (not power_plugged and bat_percent < 15):
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
        with open(self.prompt_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        prompt_lines = []
        capture = False
        for line in lines:
            if line.startswith(f"## {section_title}"):
                capture = True
                continue
            elif re.match(r"^## Phase \d", line) and capture:
                break
            if capture:
                prompt_lines.append(line)
        return "".join(prompt_lines).strip()

    def get_config(self, phase_name: str, subject_name: str = None) -> Dict[str, Any]:
        """Read config.yaml profile."""
        import yaml
        if not os.path.exists(self.config_file):
            return {}
        with open(self.config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        phase_config = data.get(phase_name.lower().replace(" ", ""), {})
        active = phase_config.get("active_profile", "default")

        if subject_name:
            overrides = phase_config.get("subject_overrides", {})
            if subject_name in overrides:
                active = overrides[subject_name]

        return phase_config.get("profiles", {}).get(active, {})

    # ------------------------------------------------------------------ #
    #  Task Management (voice-memo pattern; optional for other skills)     #
    # ------------------------------------------------------------------ #

    def get_tasks(
        self,
        prev_phase_key: str = None,
        force: bool = False,
        subject_filter: str = None,
        resume_from: Dict[str, str] = None,
    ) -> List[Dict]:
        """
        收集待處理任務清單。
        voice-memo 使用，pdf-knowledge 可不使用（改用 queue_manager）。
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

        return all_tasks

    def _batch_select_reprocess(self, done_tasks: List[Dict]) -> Dict[int, Dict]:
        """互動式批量選擇已完成任務是否重跑。"""
        selected: set = set()

        def render_list():
            print("\n" + "═" * 56)
            print(f"   ⚠️  偵測到 {len(done_tasks)} 個 [{self.phase_key.upper()}] 已完成的檔案")
            print("═" * 56)
            for i, task in enumerate(done_tasks, 1):
                mark = "●" if (i - 1) in selected else "○"
                print(f"  [{i:>2}] {mark} {task['subject']} / {task['filename']}")
            print("-" * 56)
            print("   輸入指令：數字 (1,3) = 切換選取 | A = 全選 | S/Enter = 全部跳過")
            print("-" * 56)

        render_list()

        while True:
            try:
                raw = input("   > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("   [已跳過全部已完成檔案]")
                return {}

            if raw == "s":
                print(f"   ⏭️  已選擇跳過全部 {len(done_tasks)} 個已完成檔案。")
                return {}
            elif raw == "":
                if not selected:
                    print(f"   ⏭️  未選取任何項目，跳過全部 {len(done_tasks)} 個已完成檔案。")
                    return {}
                else:
                    chosen = {i: done_tasks[i] for i in sorted(selected)}
                    print(f"   ✅ 確認重新處理 {len(chosen)} 個檔案。")
                    return chosen
            elif raw == "a":
                selected = set(range(len(done_tasks)))
                render_list()
                print(f"   ✅ 已全選，將重新處理全部 {len(done_tasks)} 個已完成檔案。")
                return {i: done_tasks[i] for i in sorted(selected)}
            else:
                tokens = raw.replace(",", " ").split()
                valid = True
                parsed = []
                for tok in tokens:
                    if tok.isdigit():
                        idx = int(tok) - 1
                        if 0 <= idx < len(done_tasks):
                            parsed.append(idx)
                        else:
                            print(f"   ⚠️  編號 {tok} 超出範圍，請重新輸入。")
                            valid = False
                            break
                    else:
                        print(f"   ⚠️  無法辨識指令：{tok}。請輸入數字、A 或 S/Enter。")
                        valid = False
                        break

                if valid and parsed:
                    for idx in parsed:
                        if idx in selected:
                            selected.discard(idx)
                        else:
                            selected.add(idx)
                    render_list()

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


