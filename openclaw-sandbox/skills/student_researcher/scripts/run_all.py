import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

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
        include_start_phase=True,
    )
    args = parser.parse_args()
    PipelineBase.run_skill_pipeline(
        phases=[Phase1ClaimExtraction, Phase2Synthesis],
        args=args,
        start_phase=getattr(args, "start_phase", 1),
    )


if __name__ == "__main__":
    main()
