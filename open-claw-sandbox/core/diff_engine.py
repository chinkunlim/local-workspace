"""
core/diff_engine.py — Open Claw Universal Diff & Audit Engine
=============================================================
Provides skill-agnostic text comparison and change-log aggregation.

Replaces:
    audio-transcriber/scripts/utils/diff_tool.py
    audio-transcriber/scripts/utils/audit_tool.py

Design:
    - Zero coupling to any skill.  Callers pass raw file paths.
    - DiffEngine: line-based HTML diff + structured dict result.
    - AuditEngine: scans markdown change-log sections and aggregates
      correction entries across files.
    - Both classes are usable standalone (CLI) or as library imports.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from datetime import datetime
import difflib
import glob
import os
import re
from typing import Dict, List, Optional, Tuple
import webbrowser

# ──────────────────────────────────────────────────────────────────────────────
#  Data containers
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class DiffResult:
    file_a: str  # absolute path
    file_b: str  # absolute path
    label_a: str = ""
    label_b: str = ""
    text_a: str = ""
    text_b: str = ""
    html_report: str = ""
    additions: int = 0
    deletions: int = 0
    char_delta: float = 0.0  # percentage (negative = shrinkage)
    success: bool = True
    error: str = ""


@dataclass
class AuditEntry:
    before: str
    after: str
    count: int = 0
    reasons: List[str] = field(default_factory=list)
    phases: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
#  Shared HTML CSS (dark-mode, VSCode-flavour)
# ──────────────────────────────────────────────────────────────────────────────

_HTML_STYLE = """
<style>
  :root {
    --bg: #1a1b26; --bg2: #24283b; --fg: #a9b1d6;
    --add: #1a3326; --del: #3b1a1a;
    --add-fg: #73daca; --del-fg: #f7768e;
    --border: #414868; --header: #2f3549; --title: #7dcfff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--fg);
         font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
         font-size: 13px; padding: 20px; }
  h1  { color: var(--title); font-size: 18px; font-weight: 600; margin-bottom: 6px; }
  .meta  { color: #565f89; font-size: 12px; margin-bottom: 16px; }
  .stats { margin-top: 16px; padding: 12px 16px; background: var(--bg2);
           border-radius: 8px; border: 1px solid var(--border); font-size: 12px; }
  .stats b { color: var(--title); }
  table.diff { width: 100%; border-collapse: collapse;
               border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
  .diff_header { background: var(--header); color: var(--title);
                 padding: 8px 12px; font-weight: 600; text-align: center; font-size: 12px; }
  .diff_next td { background: var(--header); color: #565f89;
                  font-size: 11px; text-align: center; padding: 2px; }
  td  { padding: 3px 10px; vertical-align: top; white-space: pre-wrap;
        word-break: break-all; border-right: 1px solid var(--border); }
  td.diff_header { background: var(--header); }
  .diff_add td { background: var(--add); }
  .diff_sub td { background: var(--del); }
  .diff_chg td { background: var(--bg2); }
  span.diff_add { color: var(--add-fg); font-weight: 600; text-decoration: underline; }
  span.diff_sub { color: var(--del-fg); font-weight: 600; text-decoration: line-through; }
</style>
"""


# ──────────────────────────────────────────────────────────────────────────────
#  DiffEngine
# ──────────────────────────────────────────────────────────────────────────────


class DiffEngine:
    """
    Skill-agnostic side-by-side diff generator.

    Usage::
        engine = DiffEngine()
        result = engine.diff_files("/path/to/a.md", "/path/to/b.md",
                                   label_a="Phase 1", label_b="Phase 2")
        if result.html_report:
            engine.write_html(result, "/path/to/out.diff.html")
    """

    def __init__(self, context_lines: int = 3, wrap_columns: int = 100):
        self.context_lines = context_lines
        self.wrap_columns = wrap_columns

    # --- public API ----------------------------------------------------------

    def diff_files(
        self,
        path_a: str,
        path_b: str,
        label_a: str = "",
        label_b: str = "",
        strip_log_marker: Optional[str] = None,
    ) -> DiffResult:
        """
        Compare two text files and return a DiffResult.

        Args:
            path_a: Absolute path to the 'before' file.
            path_b: Absolute path to the 'after'  file.
            label_a: Human-readable label for file_a.
            label_b: Human-readable label for file_b.
            strip_log_marker: If provided, everything from this string onward
                              in file_b is stripped before comparison (useful
                              for audio-transcriber audit-log footers).
        """
        r = DiffResult(
            file_a=path_a,
            file_b=path_b,
            label_a=label_a or os.path.basename(path_a),
            label_b=label_b or os.path.basename(path_b),
        )

        if not os.path.exists(path_a):
            r.success, r.error = False, f"File not found: {path_a}"
            return r
        if not os.path.exists(path_b):
            r.success, r.error = False, f"File not found: {path_b}"
            return r

        with open(path_a, encoding="utf-8") as f:
            r.text_a = f.read()
        with open(path_b, encoding="utf-8") as f:
            raw_b = f.read()

        if strip_log_marker and strip_log_marker in raw_b:
            raw_b = raw_b.split(strip_log_marker, 1)[0].rstrip().rstrip("-").strip()
        r.text_b = raw_b

        lines_a = r.text_a.splitlines(keepends=True)
        lines_b = r.text_b.splitlines(keepends=True)

        r.additions = sum(1 for l in lines_b if l not in lines_a)
        r.deletions = sum(1 for l in lines_a if l not in lines_b)
        chars_a, chars_b = sum(len(l) for l in lines_a), sum(len(l) for l in lines_b)
        r.char_delta = ((chars_b - chars_a) / chars_a * 100) if chars_a else 0.0

        r.html_report = self._build_html(r, lines_a, lines_b)
        return r

    def write_html(self, result: DiffResult, out_path: str, auto_open: bool = False) -> str:
        """Write result.html_report to disk and optionally open in browser."""
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result.html_report)
        if auto_open:
            webbrowser.open(f"file://{os.path.abspath(out_path)}")
        return out_path

    # --- private helpers -----------------------------------------------------

    def _build_html(self, r: DiffResult, lines_a: List[str], lines_b: List[str]) -> str:
        differ = difflib.HtmlDiff(
            tabsize=4,
            wrapcolumn=self.wrap_columns,
            linejunk=None,
            charjunk=difflib.IS_CHARACTER_JUNK,
        )
        table = differ.make_table(
            fromlines=lines_a,
            tolines=lines_b,
            fromdesc=r.label_a,
            todesc=r.label_b,
            context=True,
            numlines=self.context_lines,
        )
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        stats = (
            f"<div class='stats'><b>統計</b>&nbsp;"
            f"原始：{sum(len(l) for l in lines_a):,} 字元 &nbsp;→&nbsp;"
            f"輸出：{sum(len(l) for l in lines_b):,} 字元"
            f"&nbsp;|&nbsp; 淨變化：{r.char_delta:+.1f}%"
            f"&nbsp;|&nbsp; 新增行：{r.additions} &nbsp; 刪除行：{r.deletions}</div>"
        )
        return (
            f"<!DOCTYPE html><html lang='zh-TW'><head>"
            f"<meta charset='utf-8'><title>Diff — {r.label_a} vs {r.label_b}</title>"
            f"{_HTML_STYLE}</head><body>"
            f"<h1>📋 Diff Report</h1>"
            f"<div class='meta'>生成時間：{now} &nbsp;|&nbsp; "
            f"左：{r.label_a} &nbsp;|&nbsp; 右：{r.label_b}</div>"
            f"{table}{stats}</body></html>"
        )


# ──────────────────────────────────────────────────────────────────────────────
#  AuditEngine  (generalised from audio-transcriber audit_tool)
# ──────────────────────────────────────────────────────────────────────────────

# Matches: * **"原文"** → **"修正後"** — 理由
_LOG_ENTRY_RE = re.compile(
    r'\*\s+\*{1,2}[「""]?(.+?)[」""]?\*{1,2}\s*→\s*\*{1,2}[「""]?(.+?)[」""]?\*{1,2}'
    r"(?:\s*[—\-–]\s*(.+))?",
    re.UNICODE,
)


class AuditEngine:
    """
    Scans markdown files for correction-log sections and aggregates entries.

    Usage::
        engine = AuditEngine()
        entries = engine.aggregate_directory(
            directory="/path/to/02_proofread/助人歷程",
            log_marker="## 📋 彙整修改日誌",
            phase_tag="P2",
        )
        report_md = engine.render_report(entries, subject="助人歷程")
    """

    def aggregate_directory(
        self,
        directory: str,
        log_marker: str,
        phase_tag: str,
        min_count: int = 1,
    ) -> Dict[Tuple[str, str], AuditEntry]:
        """
        Scan all .md files in a directory, parse change-log sections,
        and return aggregated AuditEntry dict keyed by (before, after).
        """
        aggregated: Dict[Tuple[str, str], AuditEntry] = {}

        if not os.path.isdir(directory):
            return {}

        for fpath in sorted(glob.glob(os.path.join(directory, "*.md"))):
            fname = os.path.basename(fpath)
            with open(fpath, encoding="utf-8") as f:
                content = f.read()

            log_text = self._extract_section(content, log_marker)
            for entry in self._parse_entries(log_text):
                key = (entry["before"], entry["after"])
                if key not in aggregated:
                    aggregated[key] = AuditEntry(before=entry["before"], after=entry["after"])
                ae = aggregated[key]
                ae.count += 1
                ae.files.append(fname)
                ae.phases.append(phase_tag)
                if entry["reason"] and entry["reason"] not in ae.reasons:
                    ae.reasons.append(entry["reason"])

        return {k: v for k, v in aggregated.items() if v.count >= min_count}

    def render_report(
        self,
        entries: Dict[Tuple[str, str], AuditEntry],
        subject: str,
        min_count: int = 1,
    ) -> str:
        """Generate a markdown audit report string."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        sorted_entries = sorted(entries.items(), key=lambda x: (-x[1].count, x[0][0]))

        lines = [
            f"# 校對總報告 — {subject}",
            "",
            f"> 生成時間：{now}  ",
            f"> 最低出現次數：{min_count}  ",
            "",
            "---",
            "",
            "## 統計摘要",
            "",
            "| 指標 | 數值 |",
            "| :-- | --: |",
            f"| 總修改條目（去重後） | {len(entries):,} 筆 |",
            f"| 跨檔案重複修改（≥2 次） | {sum(1 for v in entries.values() if v.count >= 2):,} 筆 |",
            "",
            "---",
            "",
            "## 修改彙整（按頻率排序）",
            "",
            "| # | 原文 | → 修正後 | 次數 | Phase | 涉及檔案 | 修改理由 |",
            "| --: | :-- | :-- | :--: | :-- | :-- | :-- |",
        ]
        for rank, ((before, after), ae) in enumerate(sorted_entries, 1):
            phases_str = " ".join(sorted(set(ae.phases)))
            files_str = "、".join(sorted(set(ae.files)))
            reason_str = "；".join(ae.reasons) if ae.reasons else "—"
            lines.append(
                f"| {rank} | `{before}` | `{after}` | {ae.count} | {phases_str} | {files_str} | {reason_str} |"
            )

        return "\n".join(lines) + "\n"

    # --- private -------------------------------------------------------------

    @staticmethod
    def _extract_section(text: str, marker: str) -> str:
        if marker not in text:
            return ""
        return text.split(marker, 1)[1].strip()

    @staticmethod
    def _parse_entries(log_text: str) -> List[dict]:
        entries = []
        for line in log_text.splitlines():
            m = _LOG_ENTRY_RE.search(line)
            if m:
                before = m.group(1).strip()
                after = m.group(2).strip()
                reason = m.group(3).strip() if m.group(3) else ""
                if before and after and before != after:
                    entries.append({"before": before, "after": after, "reason": reason})
        return entries


# ──────────────────────────────────────────────────────────────────────────────
#  CLI entry point (standalone usage)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Open Claw Diff Engine — CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # diff subcommand
    d = sub.add_parser("diff", help="Side-by-side diff between two files")
    d.add_argument("file_a", help="'Before' file path")
    d.add_argument("file_b", help="'After'  file path")
    d.add_argument("--label-a", default="Before")
    d.add_argument("--label-b", default="After")
    d.add_argument("--out", help="Output HTML path (default: adjacent to file_b)")
    d.add_argument("--open", dest="auto_open", action="store_true")
    d.add_argument(
        "--strip-log",
        metavar="MARKER",
        default=None,
        help="Strip everything from this markdown marker onward in file_b",
    )

    # audit subcommand
    a = sub.add_parser("audit", help="Aggregate correction logs in a directory")
    a.add_argument("directory", help="Directory containing .md files")
    a.add_argument("--marker", default="## 📋 彙整修改日誌")
    a.add_argument("--phase", default="P?", help="Phase tag label (e.g. P2)")
    a.add_argument("--subject", default="Unknown Subject")
    a.add_argument("--min-count", type=int, default=1)
    a.add_argument("--out", help="Output .md report path")

    args = parser.parse_args()

    if args.command == "diff":
        engine = DiffEngine()
        result = engine.diff_files(
            args.file_a,
            args.file_b,
            label_a=args.label_a,
            label_b=args.label_b,
            strip_log_marker=args.strip_log,
        )
        if not result.success:
            print(f"❌ {result.error}", file=sys.stderr)
            sys.exit(1)
        out = args.out or (os.path.splitext(args.file_b)[0] + ".diff.html")
        engine.write_html(result, out, auto_open=args.auto_open)
        print(f"✅ Diff 報告已生成: {out}")
        print(
            f"   新增行: {result.additions}, 刪除行: {result.deletions}, 字元淨變化: {result.char_delta:+.1f}%"
        )

    elif args.command == "audit":
        audit_engine = AuditEngine()
        entries = audit_engine.aggregate_directory(
            args.directory, args.marker, args.phase, args.min_count
        )
        report = audit_engine.render_report(entries, args.subject, args.min_count)
        if args.out:
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"✅ Audit 報告已生成: {args.out}")
        else:
            print(report)
