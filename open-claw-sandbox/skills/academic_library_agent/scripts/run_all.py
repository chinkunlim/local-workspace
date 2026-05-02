import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from phases.p01_search_literature import Phase1SearchLiterature

from core import PipelineBase, SessionState, StateManager, build_skill_parser


class AcademicLibraryOrchestrator(PipelineBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="orchestrator",
            phase_name="Academic Library Agent 管線協調器",
            skill_name="academic_library_agent",
        )
        self._state_manager = StateManager(self.base_dir, skill_name="academic_library_agent")

    def run(self, args) -> None:
        self._state_manager.sync_physical_files()

        print(f"\n{'=' * 50}")
        print("🚀 開始執行 Phase 1: Search Literature...")
        print(f"{'=' * 50}")

        p_obj = Phase1SearchLiterature()
        p_obj.run(
            force=args.force,
            subject=args.subject,
            file_filter=args.file,
            single_mode=args.single,
            resume_from=None,
        )

        if not p_obj.stop_requested:
            self._write_session_state(SessionState.COMPLETED)
            print("🏁 Pipeline 執行完畢。")


def main() -> None:
    parser = build_skill_parser(
        "Academic Library Agent",
        include_subject=True,
        include_force=True,
        include_resume=False,
        include_interactive=False,
        include_start_phase=False,
    )
    args = parser.parse_args()
    AcademicLibraryOrchestrator().run(args)


if __name__ == "__main__":
    main()
