import os
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from phases.p01_compare import Phase1Compare
from phases.p02_anki import Phase2Anki

from core import PipelineBase, SessionState, StateManager, build_skill_parser


class AcademicOrchestrator(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="orchestrator",
            phase_name="Academic Assistant 管線協調器",
            skill_name="academic-edu-assistant",
        )
        self._state_manager = StateManager(self.base_dir, skill_name="academic-edu-assistant")

    def run(self, args):
        self._state_manager.sync_physical_files()

        # If --query is provided, Phase 1 handles it as a one-off task
        p1 = Phase1Compare()
        p2 = Phase2Anki()

        if p1.stop_requested or p2.stop_requested:
            return

        p1.run(
            force=args.force,
            subject=args.subject,
            file_filter=args.file,
            single_mode=args.single,
            query=getattr(args, "query", None),
        )

        if p1.stop_requested:
            return

        p2.run(
            force=args.force, subject=args.subject, file_filter=args.file, single_mode=args.single
        )

        if p2.stop_requested:
            if p2.pause_requested:
                self._write_session_state(SessionState.PAUSED)
            else:
                self._write_session_state(SessionState.STOPPED)
        else:
            self._write_session_state(SessionState.COMPLETED)

        print("🏁 Academic Assistant 執行完畢。")


def main():
    parser = build_skill_parser(
        "Academic Education Assistant",
        include_subject=True,
        include_force=True,
        include_process_all=True,
    )
    parser.add_argument("--query", type=str, help="直接指定查詢字串來進行 RAG 交叉比對 (Option B)")
    args = parser.parse_args()
    AcademicOrchestrator().run(args)


if __name__ == "__main__":
    main()
