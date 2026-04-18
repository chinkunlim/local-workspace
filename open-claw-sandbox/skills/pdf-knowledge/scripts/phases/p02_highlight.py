# -*- coding: utf-8 -*-
"""
p02_highlight.py — Phase 2: 重點標記 (Anti-Tampering)
======================================================
從 01_Processed/<subject>/<pdf_id>/raw_extracted.md 讀取原文，
使用 LLM 以 **bold**、==highlight==、`code` 等 Markdown 標記標注重點，
絕不刪除或改寫任何文字（Anti-Tampering 防竄改機制）。

輸出：02_Highlighted/<subject>/<pdf_id>/highlighted.md

設計參考：skills/voice-memo/scripts/phases/p04_highlight.py
"""

import os
import sys

# Internal Core Bootstrap
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

from core import PipelineBase, AtomicWriter

# Delegate to standalone skill
from skills.smart_highlighter.scripts.highlight import SmartHighlighter


class Phase2Highlight(PipelineBase):
    """
    Phase 2: 重點標記 (Anti-Tampering).

    Reads raw_extracted.md from 01_Processed, applies Markdown highlight/bold
    annotations to key concepts via LLM, and writes highlighted.md to
    02_Highlighted. The source text is NEVER modified — only annotations are added.

    The verbatim_threshold guard ensures the LLM cannot delete content:
    if the output is shorter than threshold * input length, the original
    chunk is used unchanged.
    """

    # Fallback threshold if not set in config.yaml
    DEFAULT_VERBATIM_THRESHOLD: float = 0.50

    def __init__(self) -> None:
        super().__init__(
            phase_key="phase2",
            phase_name="重點標記",
            skill_name="pdf-knowledge",
        )

    def run(self, subject: str, filename: str) -> bool:
        """
        Highlight key points in raw_extracted.md for one PDF.

        Args:
            subject: Subject folder the PDF belongs to.
            filename: The PDF filename.

        Returns:
            True on success, False on failure.
        """
        pdf_id = os.path.splitext(filename)[0]
        self.info(f"🖊️  [Phase 2] 啟動重點標記: [{subject}] {pdf_id}")

        # ── Paths ──────────────────────────────────────────────────────────
        raw_path = os.path.join(self.dirs["processed"], subject, pdf_id, "raw_extracted.md")
        out_dir = os.path.join(self.dirs["highlighted"], subject, pdf_id)
        out_path = os.path.join(out_dir, "highlighted.md")

        if not os.path.exists(raw_path):
            self.warning(f"⚠️  [Phase 2] 找不到 raw_extracted.md，跳過: {raw_path}")
            return False

        os.makedirs(out_dir, exist_ok=True)

        # ── Read source ────────────────────────────────────────────────────
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        self.info(f"📖 [Phase 2] 原文長度 {len(raw_text):,} 字元，委派給 SmartHighlighter")

        # ── Chunked LLM processing (Delegated) ─────────────────────────────
        highlighter = SmartHighlighter(profile="fast")
        highlighter.logger = self.logger
        
        final_doc = highlighter.run(markdown_text=raw_text, subject=subject)

        # ── Write output ───────────────────────────────────────────────────
        header = (
            f"<!-- highlighted.md — Phase 2 重點標記\n"
            f"     pdf_id : {pdf_id}\n"
            f"     subject: {subject}\n"
            f"     delegated: smart-highlighter\n"
            "-->\n\n"
        )
        AtomicWriter.write_text(out_path, header + final_doc)
        self.info(f"✅ [Phase 2] 重點標記完成: {out_path} ({len(final_doc):,} 字元)")

        return True


# ---------------------------------------------------------------------------- #
#  CLI Entry Point                                                              #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 2: PDF Highlight Key Points")
    parser.add_argument("pdf", help="The PDF path")
    args = parser.parse_args()

    filename = os.path.basename(args.pdf)
    success = Phase2Highlight().run(args.subject, filename)
    sys.exit(0 if success else 1)
