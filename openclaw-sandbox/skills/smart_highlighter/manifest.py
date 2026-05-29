"""skills/smart_highlighter/manifest.py — SkillManifest (#17 / M1)"""

import os
import sys

from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import PhaseHighlight

    text = kw.pop("markdown_text", "")
    PhaseHighlight().run_single(text, **kw)


MANIFEST = SkillManifest(
    skill_name="smart_highlighter",
    description="Applies Markdown bold/highlight annotations to text with anti-tampering verbatim guard. Stateless design.",
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".md"],
    tags=["highlight", "annotation", "markdown"],
)
