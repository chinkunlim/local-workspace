import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from phases.p01_claim_extraction import Phase1ClaimExtraction
from phases.p02_synthesis import Phase2Synthesis

from core import PipelineBase, SessionState, StateManager, build_skill_parser


class StudentResearcherOrchestrator(PipelineBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="orchestrator",
            phase_name="Student Researcher 管線協調器",
            skill_name="student_researcher",
        )
        self._state_manager = StateManager(self.base_dir, skill_name="student_researcher")

    def run(self, args) -> None:
        self._state_manager.sync_physical_files()

        phases = {1: Phase1ClaimExtraction, 2: Phase2Synthesis}

        any_stopped = False
        for p_num in range(args.start_phase, 3):
            print(f"\n{'=' * 50}")
            print(f"🚀 開始執行 Phase {p_num}...")
            print(f"{'=' * 50}")

            p_obj = phases[p_num]()
            p_obj.run(
                force=args.force,
                subject=args.subject,
                file_filter=args.file,
                single_mode=args.single,
                resume_from=None,
            )

            if p_obj.stop_requested:
                any_stopped = True
                self._write_session_state(SessionState.STOPPED)
                break

        if not any_stopped:
            self._write_session_state(SessionState.COMPLETED)
            print("🏁 Pipeline 執行完畢。")


def main() -> None:
    parser = build_skill_parser(
        "Student Researcher Agent",
        include_subject=True,
        include_force=True,
        include_resume=False,
        include_interactive=False,
        include_start_phase=True,
    )
    args = parser.parse_args()
    StudentResearcherOrchestrator().run(args)


if __name__ == "__main__":
    main()
