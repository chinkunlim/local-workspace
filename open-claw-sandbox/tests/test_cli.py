import argparse

from core.cli import build_skill_parser


def test_build_skill_parser_default():
    parser = build_skill_parser("Test Parser")
    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.description == "Test Parser"

    # Should only have --help by default
    args = parser.parse_args([])
    assert not hasattr(args, "force")
    assert not hasattr(args, "subject")
    assert not hasattr(args, "process_all")


def test_build_skill_parser_all_flags():
    parser = build_skill_parser(
        "Test Parser All",
        include_subject=True,
        include_force=True,
        include_resume=True,
        include_interactive=True,
        include_start_phase=True,
        include_process_all=True,
        include_config=True,
        include_log_json=True,
    )

    args = parser.parse_args(
        [
            "--force",
            "--resume",
            "--interactive",
            "--subject",
            "Math",
            "--file",
            "test.pdf",
            "--single",
            "--from",
            "3",
            "--process-all",
            "--config",
            "custom.yaml",
            "--log-json",
        ]
    )

    assert args.force is True
    assert args.resume is True
    assert args.interactive is True
    assert args.subject == "Math"
    assert args.file == "test.pdf"
    assert args.single is True
    assert args.start_phase == 3
    assert args.process_all is True
    assert args.config == "custom.yaml"
    assert args.log_json is True
