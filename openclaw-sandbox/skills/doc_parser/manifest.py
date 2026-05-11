"""skills/doc_parser/manifest.py — SkillManifest (#17 / M1)"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import DocParserOrchestrator

    DocParserOrchestrator().run(**kw)


MANIFEST = SkillManifest(
    skill_name="doc_parser",
    description="Parses PDF documents via Docling + OCR quality gate + VLM vision with adaptive intent-based prompt routing.",
    phases=["p0a_diagnostic", "p1a_engine", "p1b_vector_charts", "p1c_ocr_gate", "p1d_vlm_vision"],
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".pdf"],
    tags=["pdf", "ocr", "vlm", "docling"],
)
