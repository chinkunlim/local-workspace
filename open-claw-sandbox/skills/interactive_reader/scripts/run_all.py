import os
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from phases.p01_interactive import Phase1Interactive

from core import PipelineBase, SessionState, StateManager, build_skill_parser


class ReaderOrchestrator(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="orchestrator",
            phase_name="Interactive Reader 管線協調器",
            skill_name="interactive_reader",
        )
        self._state_manager = StateManager(self.base_dir, skill_name="interactive_reader")

    def startup_check(self) -> bool:
        print("=" * 50)
        print("✈️  進行啟動前置檢查 (Preflight Check)...")
        print("✅ 前置檢查通過。")
        return True

    def _check_and_resume(self) -> dict | None:
        cp = self._state_manager.load_checkpoint()
        if not cp:
            return None
        saved_at = cp.get("saved_at", "不明")
        print("\n" + "═" * 56)
        print("📌 偵測到上次暫停的斷點 (Checkpoint)")
        print(f"   時間：{saved_at}")
        print(f"   科目：{cp.get('subject', '?')}")
        print(f"   檔案：{cp.get('filename', '?')}")
        print(f"   Phase：{cp.get('phase_key', '?').upper()}")
        print("═" * 56)
        print("請選擇：")
        print("  [C] Continue — 從上次斷點繼續")
        print("  [N] New       — 全新開始（清除 Checkpoint）")
        try:
            choice = input("請輸入 (C/N) [Enter = C]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n已選擇全新開始。")
            self._state_manager.clear_checkpoint()
            return None
        if choice == "n":
            self._state_manager.clear_checkpoint()
            print("🗑️  Checkpoint 已清除，全新開始。")
            return None
        print("➩️  從斷點繼續。")
        return cp

    def run(self, args):
        if not self.startup_check():
            sys.exit(1)
        self._state_manager.sync_physical_files()

        resume_from = None
        if getattr(args, "resume", False):
            resume_from = self._state_manager.load_checkpoint()
        elif not getattr(args, "force", False):
            resume_from = self._check_and_resume()

        self._state_manager.print_dashboard()

        p1 = Phase1Interactive()

        if p1.stop_requested:
            return

        p1.run(
            force=args.force,
            subject=args.subject,
            file_filter=getattr(args, "file", None),
            single_mode=getattr(args, "single", False),
            resume_from=resume_from,
        )

        if p1.stop_requested:
            if p1.pause_requested:
                self._write_session_state(SessionState.PAUSED)
            else:
                self._write_session_state(SessionState.STOPPED)
        else:
            self._write_session_state(SessionState.COMPLETED)

        print("🏁 Interactive Reader 執行完畢。")


def main():
    parser = build_skill_parser("Interactive Reader", include_subject=True, include_force=True)
    args = parser.parse_args()
    ReaderOrchestrator().run(args)


if __name__ == "__main__":
    try:
        main()
        print("🏁 Pipeline 執行完畢。")
        try:
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Pipeline 執行完畢" with title "Open-Claw"',
                ],
                check=False,
            )
        except Exception:
            pass
    except KeyboardInterrupt:
        print("\n🛑 使用者手動中斷執行 (KeyboardInterrupt)")
        try:
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Execution Interrupted" with title "Open-Claw"',
                ],
                check=False,
            )
        except Exception:
            pass
        import sys

        sys.exit(130)
