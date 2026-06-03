"""skills/doc_parser/manifest.py — SkillManifest (#17 / M1)"""

from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import DocParserOrchestrator

    DocParserOrchestrator().run(**kw)


MANIFEST = SkillManifest(
    skill_name="doc_parser",
    description="Parses PDF documents via Docling + OCR quality gate + VLM vision with adaptive intent-based prompt routing.",
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".pdf", ".pptx", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"],
    tags=["pdf", "ocr", "vlm", "docling"],
)
