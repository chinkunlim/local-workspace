"""skills/note_generator/manifest.py — SkillManifest (#17 / M1)"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import PhaseNoteGenerator

    text = kw.pop("markdown_text", "")
    PhaseNoteGenerator().run_single(text, **kw)


MANIFEST = SkillManifest(
    skill_name="note_generator",
    description="Synthesizes Markdown text into structured study notes with YAML frontmatter and Mermaid mindmaps using Map-Reduce chunking.",
    phases=["synthesize"],
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".md"],
    tags=["notes", "synthesis", "mermaid", "map-reduce"],
)
