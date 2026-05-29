from phases.p00_semantic_router import Phase0SemanticRouter
from phases.p01_claim_extraction import Phase1ClaimExtraction
from phases.p02_synthesis import Phase2Synthesis

from core import PipelineBase, build_skill_parser


def main() -> None:
    parser = build_skill_parser(
        "Student Researcher Agent",
        include_subject=True,
        include_force=True,
        include_resume=False,
        include_interactive=False,
        include_start_phase=False,
        include_process_all=True,
        include_clear=True,
    )
    args = parser.parse_args()
    PipelineBase.run_skill_pipeline(
        phases=[Phase0SemanticRouter, Phase1ClaimExtraction, Phase2Synthesis],
        args=args,
        start_phase=getattr(args, "start_phase", 1),
    )


if __name__ == "__main__":
    main()
