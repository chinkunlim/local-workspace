"""skills/knowledge_compiler/manifest.py — SkillManifest (#17 / M1)"""

from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import KnowledgeCompilerOrchestrator

    KnowledgeCompilerOrchestrator().run(**kw)


MANIFEST = SkillManifest(
    skill_name="knowledge_compiler",
    description="Compiles Markdown notes into interconnected knowledge graphs with bidirectional Obsidian links.",
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".md"],
    tags=["knowledge-graph", "obsidian", "compile", "links"],
)
