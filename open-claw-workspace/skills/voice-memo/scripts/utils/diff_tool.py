# -*- coding: utf-8 -*-
"""
diff_tool.py — Phase 2.5: HTML Side-by-Side Diff Report (Optional)

Compares 01_transcript/<subject>/<name>.md (raw Whisper output)
with 02_proofread/<subject>/<name>.md (Phase 2 corrected output)
and generates a visually styled HTML diff report for human verification.

This allows reviewers to:
  - See exactly what Phase 2 changed vs. the raw transcript
  - Spot over-corrections or under-corrections at a glance
  - Open the report directly in a browser (no dependencies)

Output: 02_proofread/<subject>/<name>.diff.html
        (co-located with the proofread file for easy access)

Usage:
  # Generate diffs for all subjects
  python3 diff_tool.py

  # Generate diffs for a specific subject only
  python3 diff_tool.py --subject 助人歷程

  # Generate for a specific file
  python3 diff_tool.py --subject 助人歷程 --file L01-1

  # Auto-open the first generated diff in the default browser
  python3 diff_tool.py --subject 助人歷程 --open
"""
import sys, os
# Add scripts directory to sys.path so 'core' can be imported when running standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import os
import glob
import difflib
import webbrowser
import argparse
import subject_manager as sm

# ── HTML 樣式（內嵌 CSS，無需外部依賴） ────────────────────────────────────────
HTML_STYLE = """
<style>
  :root {
    --bg: #1a1b26; --bg2: #24283b; --fg: #a9b1d6;
    --add: #1a3326; --del: #3b1a1a; --add-fg: #73daca; --del-fg: #f7768e;
    --border: #414868; --header: #2f3549; --title: #7dcfff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--fg); font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; padding: 20px; }
  h1 { color: var(--title); font-size: 18px; font-weight: 600; margin-bottom: 6px; }
  .meta { color: #565f89; font-size: 12px; margin-bottom: 20px; }
  .legend { display: flex; gap: 16px; margin-bottom: 16px; font-size: 12px; }
  .legend span { display: flex; align-items: center; gap: 6px; }
  .leg-del { color: var(--del-fg); }
  .leg-add { color: var(--add-fg); }
  table.diff { width: 100%; border-collapse: collapse; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
  .diff_header { background: var(--header); color: var(--title); padding: 8px 12px; font-weight: 600; text-align: center; font-size: 12px; }
  .diff_next td { background: var(--header); color: #565f89; font-size: 11px; text-align: center; padding: 2px; }
  td { padding: 3px 10px; vertical-align: top; white-space: pre-wrap; word-break: break-all; border-right: 1px solid var(--border); }
  td.diff_header { background: var(--header); }
  .diff_add td { background: var(--add); }
  .diff_chg td { background: var(--bg2); }
  .diff_sub td { background: var(--del); }
  span.diff_add { color: var(--add-fg); font-weight: 600; text-decoration: underline; }
  span.diff_sub { color: var(--del-fg); font-weight: 600; text-decoration: line-through; }
  span.diff_chg { color: #e0af68; }
  .stats { margin-top: 16px; padding: 12px 16px; background: var(--bg2); border-radius: 8px; border: 1px solid var(--border); font-size: 12px; }
  .stats b { color: var(--title); }
</style>
"""


def _strip_audit_log(text: str) -> str:
    """剝離 Phase 2 修改日誌，只保留正文用於 diff。"""
    markers = ["## 📋 彙整修改日誌", "## Explanation of Changes"]
    for m in markers:
        if m in text:
            text = text.split(m, 1)[0].rstrip().rstrip("-").strip()
    return text


def generate_diff(subj: str, base_name: str, auto_open: bool = False) -> str | None:
    """
    為單個檔案生成 HTML diff 報告。
    Returns: 輸出 HTML 路徑，或 None（若來源不存在）。
    """
    transcript_path = os.path.join(sm.TRANSCRIPT_DIR, subj, f"{base_name}.md")
    proofread_path  = os.path.join(sm.PROOFREAD_DIR,  subj, f"{base_name}.md")

    if not os.path.exists(transcript_path):
        sm.log_msg(f"⚠️  找不到原始逐字稿：{transcript_path}", "warn")
        return None
    if not os.path.exists(proofread_path):
        sm.log_msg(f"⚠️  找不到校對稿：{proofread_path}", "warn")
        return None

    with open(transcript_path, "r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines(keepends=True)
    with open(proofread_path, "r", encoding="utf-8") as f:
        proofread_text = _strip_audit_log(f.read())
        proofread_lines = proofread_text.splitlines(keepends=True)

    # 生成 HTML diff（內嵌樣式、無 legend 覆蓋）
    differ = difflib.HtmlDiff(
        tabsize=4,
        wrapcolumn=80,
        linejunk=None,
        charjunk=difflib.IS_CHARACTER_JUNK
    )
    diff_table = differ.make_table(
        fromlines=raw_lines,
        tolines=proofread_lines,
        fromdesc=f"原始逐字稿　{base_name}.md",
        todesc=f"Phase 2 校對稿　{base_name}.md",
        context=True,
        numlines=3
    )

    # 統計
    additions = sum(1 for l in proofread_lines if l not in raw_lines)
    deletions = sum(1 for l in raw_lines if l not in proofread_lines)
    raw_chars = sum(len(l) for l in raw_lines)
    pro_chars = sum(len(l) for l in proofread_lines)
    reduction = ((raw_chars - pro_chars) / raw_chars * 100) if raw_chars else 0

    stats_html = f"""
<div class='stats'>
  <b>統計</b>　
  原始：{raw_chars:,} 字元 &nbsp;→&nbsp; 校對後：{pro_chars:,} 字元
  &nbsp;|&nbsp; 淨變化：{reduction:+.1f}%
  &nbsp;|&nbsp; 新增行：{additions} &nbsp; 刪除行：{deletions}
  <br><small style='color:#565f89;margin-top:4px;display:block;'>
    ⚠️ 此報告為草稿。若 Phase 2 校對稿有修改日誌，它已被自動剝離，僅顯示正文差異。
  </small>
</div>
"""
    full_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<title>Diff Report — [{subj}] {base_name}</title>
{HTML_STYLE}
</head>
<body>
<h1>📋 校對對比報告</h1>
<div class='meta'>科目：{subj} &nbsp;|&nbsp; 檔案：{base_name}.md &nbsp;|&nbsp; 左：原始逐字稿　右：Phase 2 校對稿</div>
<div class='legend'>
  <span><span class='leg-del'>■</span> 刪除 / 修改前</span>
  <span><span class='leg-add'>■</span> 新增 / 修改後</span>
</div>
{diff_table}
{stats_html}
</body>
</html>"""

    out_path = os.path.join(sm.PROOFREAD_DIR, subj, f"{base_name}.diff.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    sm.log_msg(f"✅ Diff 報告已生成：{out_path}")

    if auto_open:
        webbrowser.open(f"file://{os.path.abspath(out_path)}")

    return out_path


def run_diff_tool(target_subjects=None, target_file=None, auto_open=False):
    """為所有（或指定）科目的校對稿生成 HTML diff 報告。"""
    sm.log_msg("🔍 啟動 diff_tool：生成原始 vs 校對稿對比報告...")

    if not os.path.isdir(sm.PROOFREAD_DIR):
        sm.log_msg(f"❌ 找不到 02_proofread 目錄：{sm.PROOFREAD_DIR}", "error")
        return

    all_subjects = [
        d for d in os.listdir(sm.PROOFREAD_DIR)
        if os.path.isdir(os.path.join(sm.PROOFREAD_DIR, d))
    ]

    subjects = [s for s in target_subjects if s in all_subjects] if target_subjects else all_subjects

    if not subjects:
        sm.log_msg("📋 沒有找到可處理的科目。")
        return

    generated = []
    for subj in subjects:
        proofread_dir = os.path.join(sm.PROOFREAD_DIR, subj)
        # 只處理 .md 檔（排除 .diff.html）
        md_files = sorted([
            os.path.splitext(os.path.basename(f))[0]
            for f in glob.glob(os.path.join(proofread_dir, "*.md"))
        ])

        if target_file:
            md_files = [f for f in md_files if f == target_file]
            if not md_files:
                sm.log_msg(f"⚠️  [{subj}] 找不到指定檔案：{target_file}.md", "warn")
                continue

        for base_name in md_files:
            out = generate_diff(subj, base_name, auto_open=(auto_open and not generated))
            if out:
                generated.append(out)

    sm.log_msg(f"🏁 完成！共生成 {len(generated)} 份 diff 報告。")
    if generated:
        sm.log_msg(f"   位置：{os.path.dirname(generated[0])}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 2.5: Generate HTML side-by-side diff reports (transcript vs. proofread)"
    )
    parser.add_argument("--subject", "-s", nargs="+", metavar="SUBJECT",
                        help="Target specific subject(s).")
    parser.add_argument("--file", "-f", metavar="BASENAME",
                        help="Target a specific file basename (without .md). E.g. L01-1")
    parser.add_argument("--open", dest="auto_open", action="store_true",
                        help="Auto-open the first generated report in the default browser.")
    args = parser.parse_args()

    run_diff_tool(
        target_subjects=args.subject,
        target_file=args.file,
        auto_open=args.auto_open
    )
