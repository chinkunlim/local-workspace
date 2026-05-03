import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from phases.p01_search_literature import Phase1SearchLiterature

from core import PipelineBase, build_skill_parser


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
    PipelineBase.run_skill_pipeline(phases=[Phase1SearchLiterature], args=args)


if __name__ == "__main__":
    main()
