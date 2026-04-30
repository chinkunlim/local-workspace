"""
core/cli_runner.py — Shared Service Layer for Skill Command Construction
========================================================================
Encapsulates the subprocess command-list construction for all 4 skills.

Both the Flask WebUI (app.py routes) and future CLI tools import from
here — ensuring a single source of truth for how each Skill is invoked.

Usage:
    from core.cli.cli_runner import SkillRunner

    cmd = SkillRunner.run_audio_transcriber(subject="AI_Papers", force=True)
    exec_mgr.enqueue_task("Audio Transcriber Pipeline", cmd, cwd=workspace_root)
"""

from __future__ import annotations

import os
import sys

_core_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(_core_dir, "..")))
# Ensure workspace root is on sys.path so `from core.xxx` always resolves
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

from core.utils.path_builder import PathBuilder

# Cached PathBuilder instances (one per skill)
_pb_cache: dict[str, PathBuilder] = {}


def _pb(skill: str) -> PathBuilder:
    if skill not in _pb_cache:
        _pb_cache[skill] = PathBuilder(_workspace_root, skill)
    return _pb_cache[skill]


class SkillRunner:
    """
    Stateless factory for building subprocess command lists for each Skill.
    All methods return a ``list[str]`` suitable for ``subprocess.Popen`` or
    ``ExecutionManager.enqueue_task()``.
    """

    # ------------------------------------------------------------------
    # audio_transcriber
    # ------------------------------------------------------------------

    @staticmethod
    def run_audio_transcriber(
        *,
        subject: str = "",
        file: str = "",
        single: bool = False,
        force: bool = False,
        resume: bool = False,
        start_phase: int = 1,
    ) -> list[str]:
        """Build command to run the full audio_transcriber pipeline."""
        script = os.path.join(
            _workspace_root, "skills", "audio_transcriber", "scripts", "run_all.py"
        )
        cmd = [sys.executable, script]
        if subject:
            cmd += ["--subject", subject]
        if file:
            cmd += ["--file", file]
        if single:
            cmd += ["--single"]
        if force:
            cmd += ["--force"]
        if resume:
            cmd += ["--resume"]
        if start_phase > 1:
            cmd += ["--from", str(start_phase)]
        return cmd

    # ------------------------------------------------------------------
    # doc_parser
    # ------------------------------------------------------------------

    @staticmethod
    def run_doc_parser(
        *,
        subject: str = "",
        file: str = "",
        single: bool = False,
        force: bool = False,
        resume: bool = False,
    ) -> list[str]:
        """Build command to run the full doc_parser pipeline."""
        script = os.path.join(_workspace_root, "skills", "doc_parser", "scripts", "run_all.py")
        cmd = [sys.executable, script, "--process-all"]
        if subject:
            cmd += ["--subject", subject]
        if file:
            cmd += ["--file", file]
        if single:
            cmd += ["--single"]
        if force:
            cmd += ["--force"]
        if resume:
            cmd += ["--resume"]
        return cmd

    # ------------------------------------------------------------------
    # smart-highlighter  (Re-run on an existing file)
    # ------------------------------------------------------------------

    @staticmethod
    def run_smart_highlighter(
        *,
        input_file: str,
        output_file: str,
        subject: str = "Default",
        profile: str = "",
    ) -> list[str]:
        """
        Build command to run smart-highlighter against an existing Markdown file.

        Args:
            input_file:  Absolute path to the source .md file.
            output_file: Absolute path where the highlighted output is written.
            subject:     Subject label (used for config profile selection).
            profile:     Optional config profile override.
        """
        script = os.path.join(
            _workspace_root, "skills", "smart-highlighter", "scripts", "highlight.py"
        )
        cmd = [
            sys.executable,
            script,
            "--input-file",
            input_file,
            "--output-file",
            output_file,
            "--subject",
            subject,
        ]
        if profile:
            cmd += ["--profile", profile]
        return cmd

    # ------------------------------------------------------------------
    # note-generator  (Re-run on an existing file)
    # ------------------------------------------------------------------

    @staticmethod
    def run_note_generator(
        *,
        input_file: str,
        output_file: str,
        subject: str = "Default",
        label: str = "document",
        profile: str = "",
    ) -> list[str]:
        """
        Build command to run note-generator against an existing Markdown file.

        Args:
            input_file:  Absolute path to the highlighted .md input.
            output_file: Absolute path where the synthesized note is written.
            subject:     Subject label.
            label:       Document label for YAML frontmatter.
            profile:     Optional config profile override.
        """
        script = os.path.join(
            _workspace_root, "skills", "note-generator", "scripts", "synthesize.py"
        )
        cmd = [
            sys.executable,
            script,
            "--input-file",
            input_file,
            "--output-file",
            output_file,
            "--subject",
            subject,
            "--label",
            label,
        ]
        if profile:
            cmd += ["--profile", profile]
        return cmd

    # ------------------------------------------------------------------
    # Path auto-discovery helpers
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_highlight_paths(skill: str, subject: str, file_id: str) -> tuple[str, str]:
        """
        Auto-discover input/output paths for a smart-highlighter Re-run via PathBuilder.

        audio_transcriber: input = p3 (03_merged), output = p4 (04_highlighted)
        doc_parser:        input = p1 processed raw_extracted.md, output = p2 highlighted

        Raises:
            FileNotFoundError: If the input file does not exist.
        """
        pb = _pb(skill)
        dirs = pb.phase_dirs

        if skill == "audio_transcriber":
            input_path = os.path.join(
                dirs.get("p3", os.path.join(_workspace_root, "data", skill, "output", "03_merged")),
                subject,
                f"{file_id}.md",
            )
            output_path = os.path.join(
                dirs.get(
                    "p4", os.path.join(_workspace_root, "data", skill, "output", "04_highlighted")
                ),
                subject,
                f"{file_id}.md",
            )
        elif skill == "doc_parser":
            input_path = os.path.join(
                dirs.get(
                    "p1b", os.path.join(_workspace_root, "data", skill, "output", "01_processed")
                ),
                subject,
                file_id,
                "raw_extracted.md",
            )
            output_path = os.path.join(
                dirs.get(
                    "p2a", os.path.join(_workspace_root, "data", skill, "output", "02_highlighted")
                ),
                subject,
                file_id,
                "highlighted.md",
            )
        else:
            raise ValueError(f"Unknown skill: {skill!r}")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        return input_path, output_path

    @staticmethod
    def resolve_synthesize_paths(skill: str, subject: str, file_id: str) -> tuple[str, str]:
        """
        Auto-discover input/output paths for a note-generator Re-run via PathBuilder.

        audio_transcriber: input = p4 (04_highlighted), output = p5 (05_notion_synthesis)
        doc_parser:        input = p2 (02_highlighted), output = p3 (03_synthesis)

        Raises:
            FileNotFoundError: If the input file does not exist.
        """
        pb = _pb(skill)
        dirs = pb.phase_dirs

        if skill == "audio_transcriber":
            input_path = os.path.join(
                dirs.get(
                    "p4", os.path.join(_workspace_root, "data", skill, "output", "04_highlighted")
                ),
                subject,
                f"{file_id}.md",
            )
            output_path = os.path.join(
                dirs.get(
                    "p5",
                    os.path.join(_workspace_root, "data", skill, "output", "05_notion_synthesis"),
                ),
                subject,
                f"{file_id}.md",
            )
        elif skill == "doc_parser":
            input_path = os.path.join(
                dirs.get(
                    "p2a", os.path.join(_workspace_root, "data", skill, "output", "02_highlighted")
                ),
                subject,
                file_id,
                "highlighted.md",
            )
            output_path = os.path.join(
                dirs.get(
                    "p2b", os.path.join(_workspace_root, "data", skill, "output", "03_synthesis")
                ),
                subject,
                file_id,
                "content.md",
            )
        else:
            raise ValueError(f"Unknown skill: {skill!r}")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        return input_path, output_path
