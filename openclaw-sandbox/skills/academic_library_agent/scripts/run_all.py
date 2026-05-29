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
        include_process_all=True,
        include_clear=True,
    )
    args = parser.parse_args()
    PipelineBase.run_skill_pipeline(phases=[Phase1SearchLiterature], args=args)


if __name__ == "__main__":
    main()
