"""skills/academic_edu_assistant/manifest.py — SkillManifest (#17 / M1)"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import AcademicAssistantOrchestrator

    AcademicAssistantOrchestrator().run(**kw)


MANIFEST = SkillManifest(
    skill_name="academic_edu_assistant",
    description="RAG cross-comparison of lecture notes vs reference materials, then auto-generates Anki flashcards with optional AnkiConnect push.",
    phases=["p1_compare", "p2_anki"],
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".md", ".pdf"],
    tags=["anki", "rag", "flashcards", "education"],
)
