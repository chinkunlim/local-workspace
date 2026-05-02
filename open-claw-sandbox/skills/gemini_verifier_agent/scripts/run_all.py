import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from phases.p01_ai_debate import Phase1AIDebate

from core import PipelineBase, SessionState, StateManager, build_skill_parser


class GeminiVerifierOrchestrator(PipelineBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="orchestrator",
            phase_name="Gemini Verifier Agent 管線協調器",
            skill_name="gemini_verifier_agent",
        )
        self._state_manager = StateManager(self.base_dir, skill_name="gemini_verifier_agent")

    def run(self, args) -> None:
        self._state_manager.sync_physical_files()

        print(f"\n{'=' * 50}")
        print("🚀 開始執行 Phase 1: AI Debate...")
        print(f"{'=' * 50}")

        p_obj = Phase1AIDebate()
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
        "Gemini Verifier Agent",
        include_subject=True,
        include_force=True,
        include_resume=False,
        include_interactive=False,
        include_start_phase=False,
    )
    args = parser.parse_args()
    GeminiVerifierOrchestrator().run(args)


if __name__ == "__main__":
    main()
