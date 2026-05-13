"""
p01b_text_sanitizer.py — Phase 1b: Post-Extraction Text Sanitization
======================================================================
Runs AFTER p01a (raw_extracted.md is IMMUTABLE). This phase applies
purely structural, non-semantic text cleanup and writes sanitized.md.

Traceability: If content is missing, compare raw_extracted.md vs
sanitized.md to determine whether the fault is in Docling (Phase 1a)
or in the cleanup logic (this phase).

Operations:
  1. Header/Footer Purge  — remove repeating header/footer lines
  2. Hyphenation Repair   — merge end-of-line hyphenated words
"""

from collections import Counter
import os
import re
from typing import Optional

from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase


class Phase1bTextSanitizer(PipelineBase):
    """
    Phase 1b: Text Sanitization (non-semantic, structural cleanup only).
    Input:  output/01_processed/<subject>/<pdf_id>/raw_extracted.md
    Output: output/01_processed/<subject>/<pdf_id>/sanitized.md
    """

    # A line appearing on this fraction of pages is considered a header/footer
    HEADER_FOOTER_RATIO = 0.40
    # Minimum number of occurrences before a line is treated as header/footer
    HEADER_FOOTER_MIN_COUNT = 2

    def __init__(self) -> None:
        super().__init__(
            phase_key="p1b_s",
            phase_name="文字淨化",
            skill_name="doc_parser",
        )

    def run(
        self,
        force: bool = False,
        subject: str = None,
        file_filter: str = None,
        single_mode: bool = False,
        resume_from: str = None,
    ):
        """
        Execute sanitization on processed PDFs horizontally.
        """
        self.process_tasks(
            self._process_file,
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )

    def _process_file(self, idx: int, task: dict, total: int) -> Optional[bool]:
        subject = task["subject"]
        filename = task["filename"]
        pdf_id = os.path.splitext(filename)[0]
        raw_filename = f"{pdf_id}_raw_extracted.md"
        raw_path = os.path.join(self.dirs["processed"], subject, pdf_id, raw_filename)
        out_path = os.path.join(self.dirs["processed"], subject, pdf_id, "sanitized.md")

        if not os.path.exists(raw_path):
            self.warning(f"⚠️ [Phase 1b-S] 找不到 {raw_filename}: {raw_path}")
            self.state_manager.update_task(
                subject, filename, self.phase_key, "❌", note_tag="找不到 raw_extracted.md"
            )
            return False

        # Load scan_report to get page count for header/footer threshold
        page_count = self._get_page_count(subject, pdf_id)

        with open(raw_path, encoding="utf-8") as f:
            raw_text = f.read()

        # Strip the IMMUTABLE comment header before processing
        content = self._strip_immutable_header(raw_text)

        # Step 1: Header/Footer purge
        content, hf_removed = self._purge_headers_footers(content, page_count)

        # Step 2: Hyphenation repair
        content, hyph_fixed = self._repair_hyphenation(content)

        # Write sanitized output
        header = (
            "<!-- sanitized.md — Phase 1b output\n"
            f"     source: {raw_filename}\n"
            f"     hf_lines_removed: {hf_removed}\n"
            f"     hyphenations_fixed: {hyph_fixed}\n"
            "-->\n\n"
        )
        AtomicWriter.write_text(out_path, header + content)

        self.info(
            f"✅ [Phase 1b-S] 淨化完成 — "
            f"移除 {hf_removed} 行頁首/頁尾，修復 {hyph_fixed} 處連字號。"
        )
        self.state_manager.update_task(subject, filename, self.phase_key, "✅")
        return True

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _strip_immutable_header(self, text: str) -> str:
        """Remove the HTML comment IMMUTABLE block at the top of raw_extracted.md."""
        if text.startswith("<!--"):
            end = text.find("-->")
            if end != -1:
                return text[end + 3 :].lstrip("\n")
        return text

    def _get_page_count(self, subject: str, pdf_id: str) -> int:
        """Load page count from scan_report.json, default to 20 if unavailable."""
        import json

        report_path = os.path.join(self.dirs["processed"], subject, pdf_id, "scan_report.json")
        try:
            with open(report_path, encoding="utf-8") as f:
                return int(json.load(f).get("pages", 20))
        except Exception:
            return 20

    def _purge_headers_footers(self, text: str, page_count: int) -> tuple[str, int]:
        """
        Identify and remove repeating lines that appear on ≥40% of pages.
        These are almost always journal headers, footers, or page numbers.

        Returns (cleaned_text, number_of_lines_removed).
        """
        lines = text.split("\n")
        threshold = max(self.HEADER_FOOTER_MIN_COUNT, int(page_count * self.HEADER_FOOTER_RATIO))

        # Count stripped occurrences
        line_counts = Counter(line.strip() for line in lines if line.strip())

        # Also detect pure page number lines (e.g., "12", "— 12 —", "Page 12 of 20")
        _page_num_re = re.compile(
            r"^\s*(\u2014\s*)?\d+(\s*\u2014\s*|\s+of\s+\d+)?\s*$"
            r"|^\s*[Pp]age\s+\d+(\s+of\s+\d+)?\s*$",
            re.IGNORECASE,
        )

        cleaned = []
        removed = 0
        for line in lines:
            stripped = line.strip()
            # Purge repeating header/footer text
            if stripped and line_counts[stripped] >= threshold:
                removed += 1
                continue
            # Purge standalone page number lines
            if stripped and _page_num_re.match(stripped):
                removed += 1
                continue
            cleaned.append(line)

        return "\n".join(cleaned), removed

    def _repair_hyphenation(self, text: str) -> tuple[str, int]:
        """
        Merge end-of-line hyphenated words.
        e.g. "ex-\\ntraction" → "extraction"
             "multi-\\nmodal"  → "multimodal"

        Returns (repaired_text, count_of_repairs).
        """
        count = [0]

        def _replacer(m: re.Match) -> str:
            count[0] += 1
            return m.group(1) + m.group(2)

        # Match: word char, hyphen, newline, word char (standard Latin hyphenation)
        repaired = re.sub(r"(\w)-\n(\w)", _replacer, text)
        return repaired, count[0]


# ---------------------------------------------------------------------------- #
#  CLI Entry Point                                                              #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Phase 1b-S: Text Sanitizer")
    parser.add_argument("pdf", help="PDF filename (e.g. paper.pdf)")
    parser.add_argument("--subject", "-s", default="Default")
    args = parser.parse_args()

    sanitizer = Phase1bTextSanitizer()
    ok = sanitizer.run(args.subject, args.pdf)
    sys.exit(0 if ok else 1)
