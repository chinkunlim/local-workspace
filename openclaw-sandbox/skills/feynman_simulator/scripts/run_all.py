import os
import sys

from phases.p01_feynman_debate import Phase1FeynmanDebate
from phases.p02_debate_synthesis import Phase2DebateSynthesis

from core import PipelineBase, build_skill_parser


def main() -> None:
    parser = build_skill_parser(
        "Feynman Simulator — AI-to-AI Socratic Debate",
        include_subject=True,
        include_force=True,
        include_resume=False,
        include_interactive=False,
        include_start_phase=True,
        include_process_all=True,
        include_clear=True,
    )
    args = parser.parse_args()
    PipelineBase.run_skill_pipeline(
        phases=[Phase1FeynmanDebate, Phase2DebateSynthesis],
        args=args,
        start_phase=getattr(args, "start_phase", 1),
    )


if __name__ == "__main__":
    main()
