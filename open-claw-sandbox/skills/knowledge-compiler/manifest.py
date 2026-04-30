"""skills/knowledge-compiler/manifest.py — SkillManifest (#17 / M1)"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import KnowledgeCompilerOrchestrator

    KnowledgeCompilerOrchestrator().run(**kw)


MANIFEST = SkillManifest(
    skill_name="knowledge-compiler",
    description="Compiles Markdown notes into interconnected knowledge graphs with bidirectional Obsidian links.",
    phases=["p1_compile"],
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".md"],
    tags=["knowledge-graph", "obsidian", "compile", "links"],
)
