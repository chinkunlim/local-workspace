"""skills/interactive_reader/manifest.py — SkillManifest (#17 / M1)"""

import os
import sys

from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import InteractiveReaderOrchestrator

    InteractiveReaderOrchestrator().run(**kw)


MANIFEST = SkillManifest(
    skill_name="interactive_reader",
    description="Processes Obsidian wiki notes with interactive tag highlighting and annotation pipelines.",
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".md"],
    tags=["obsidian", "wiki", "reader", "annotation"],
)
