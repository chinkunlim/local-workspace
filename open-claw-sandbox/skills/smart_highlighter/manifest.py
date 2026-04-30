"""skills/smart_highlighter/manifest.py — SkillManifest (#17 / M1)"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.skill_registry import SkillManifest


def _run(**kw):
    from scripts.highlight import SmartHighlighter

    text = kw.pop("markdown_text", "")
    SmartHighlighter().run(text, **kw)


MANIFEST = SkillManifest(
    skill_name="smart_highlighter",
    description="Applies Markdown bold/highlight annotations to text with anti-tampering verbatim guard. Stateless design.",
    phases=["highlight"],
    cli_entry="scripts/highlight.py",
    run_fn=_run,
    file_types=[".md"],
    tags=["highlight", "annotation", "markdown"],
)
