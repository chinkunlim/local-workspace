# -*- coding: utf-8 -*-
"""
audit_tool.py — Cross-Phase Change Log Aggregator (Optional)

Reads Phase 2 (## 📋 彙整修改日誌) and Phase 3 (## 📋 Phase 3 修改日誌)
change logs from all processed files for a subject, and generates a
consolidated 校對總報告.md sorted by corrected term.

This allows reviewers to answer:
  - Was "輔療技" corrected consistently across all lectures?
  - How many times did Phase 3 denoise "那就是說"?
  - Are there contradictory corrections across different lectures?

Output: 02_proofread/<subject>/校對總報告.md

Usage:
  # Generate audit report for all subjects
  python3 audit_tool.py

  # Generate for a specific subject
  python3 audit_tool.py --subject 助人歷程

  # Show only entries that appear more than N times
  python3 audit_tool.py --min-count 2
"""
import sys, os
# Add scripts directory to sys.path so 'core' can be imported when running standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import os
import re
import glob
import argparse
import collections
from datetime import datetime
import subject_manager as sm


# ── log 條目正規表達式 ─────────────────────────────────────────────────────────
# 匹配格式：* **"原文"** → **"修正後"** — 理由
# 或：      * **"原文"** → **"修正後"**
LOG_ENTRY_RE = re.compile(
    r'\*\s+\*{1,2}[「""]?(.+?)[」""]?\*{1,2}\s*→\s*\*{1,2}[「""]?(.+?)[」""]?\*{1,2}'
    r'(?:\s*[—\-–]\s*(.+))?',
    re.UNICODE
)


def _extract_log_section(text: str, marker: str) -> str:
    """從檔案內容中提取指定日誌段落（marker 之後的內容）。"""
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].strip()


def _parse_log_entries(log_text: str) -> list[dict]:
    """解析日誌區塊中的所有 `* "原文" → "修正後"` 條目。"""
    entries = []
    for line in log_text.splitlines():
        m = LOG_ENTRY_RE.search(line)
        if m:
            before = m.group(1).strip()
            after  = m.group(2).strip()
            reason = m.group(3).strip() if m.group(3) else ""
            # 過濾 before == after 的無效條目
            if before and after and before != after:
                entries.append({"before": before, "after": after, "reason": reason})
    return entries


def run_audit(target_subjects=None, min_count: int = 1):
    """
    為所有（或指定）科目生成跨 Phase 校對總報告。
    
    Args:
        target_subjects: 指定科目列表，None 表示全部。
        min_count: 只顯示出現次數 >= min_count 的條目。
    """
    sm.log_msg("📊 啟動 audit_tool：生成跨 Phase 校對彙整報告...")

    all_subjects = []
    for base_dir in [sm.PROOFREAD_DIR, sm.MERGED_DIR]:
        if os.path.isdir(base_dir):
            all_subjects += [
                d for d in os.listdir(base_dir)
                if os.path.isdir(os.path.join(base_dir, d))
            ]
    all_subjects = list(set(all_subjects))

    subjects = [s for s in target_subjects if s in all_subjects] if target_subjects else all_subjects

    if not subjects:
        sm.log_msg("📋 沒有找到可處理的科目。")
        return

    for subj in sorted(subjects):
        sm.log_msg(f"🔎 處理科目：{subj}")
        # key: (before, after) → {"count": N, "reasons": [...], "phases": [...], "files": [...]}
        aggregated: dict[tuple, dict] = collections.defaultdict(
            lambda: {"count": 0, "reasons": [], "phases": [], "files": []}
        )

        # ── Phase 2 日誌 ──────────────────────────────────────────────────
        p2_dir = os.path.join(sm.PROOFREAD_DIR, subj)
        if os.path.isdir(p2_dir):
            for fpath in sorted(glob.glob(os.path.join(p2_dir, "*.md"))):
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                log_text = _extract_log_section(content, "## 📋 彙整修改日誌")
                if not log_text:
                    log_text = _extract_log_section(content, "## Explanation of Changes")
                fname = os.path.basename(fpath)
                for entry in _parse_log_entries(log_text):
                    key = (entry["before"], entry["after"])
                    aggregated[key]["count"] += 1
                    aggregated[key]["files"].append(fname)
                    aggregated[key]["phases"].append("P2")
                    if entry["reason"] and entry["reason"] not in aggregated[key]["reasons"]:
                        aggregated[key]["reasons"].append(entry["reason"])

        # ── Phase 3 日誌 ──────────────────────────────────────────────────
        p3_dir = os.path.join(sm.MERGED_DIR, subj)
        if os.path.isdir(p3_dir):
            for fpath in sorted(glob.glob(os.path.join(p3_dir, "*.md"))):
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                log_text = _extract_log_section(content, "## 📋 Phase 3 修改日誌")
                fname = os.path.basename(fpath)
                for entry in _parse_log_entries(log_text):
                    key = (entry["before"], entry["after"])
                    aggregated[key]["count"] += 1
                    aggregated[key]["files"].append(fname)
                    aggregated[key]["phases"].append("P3")
                    if entry["reason"] and entry["reason"] not in aggregated[key]["reasons"]:
                        aggregated[key]["reasons"].append(entry["reason"])

        if not aggregated:
            sm.log_msg(f"⚠️  [{subj}] 沒有找到任何修改日誌條目。", "warn")
            continue

        # ── 過濾 & 排序 ───────────────────────────────────────────────────
        filtered = {
            k: v for k, v in aggregated.items()
            if v["count"] >= min_count
        }
        # 按出現次數降序，再按 before 字母順序
        sorted_entries = sorted(
            filtered.items(),
            key=lambda x: (-x[1]["count"], x[0][0])
        )

        # ── 生成報告 ──────────────────────────────────────────────────────
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"# 校對總報告 — {subj}",
            f"",
            f"> 生成時間：{now_str}  ",
            f"> 最低出現次數篩選：{min_count}  ",
            f"> 資料來源：Phase 2（`02_proofread/`）+ Phase 3（`03_merged/`）",
            f"",
            f"---",
            f"",
            f"## 統計摘要",
            f"",
            f"| 指標 | 數值 |",
            f"| :-- | --: |",
            f"| 總修改條目（去重後） | {len(filtered):,} 筆 |",
            f"| 跨檔案重複修改（出現 ≥2 次） | {sum(1 for v in filtered.values() if v['count'] >= 2):,} 筆 |",
            f"| Phase 2 條目 | {sum(1 for v in filtered.values() if 'P2' in v['phases']):,} 筆 |",
            f"| Phase 3 條目 | {sum(1 for v in filtered.values() if 'P3' in v['phases']):,} 筆 |",
            f"",
            f"---",
            f"",
            f"## 修改條目彙整（按出現次數排序）",
            f"",
            f"| # | 原文 | → 修正後 | 次數 | Phase | 涉及檔案 | 修改理由 |",
            f"| --: | :-- | :-- | :--: | :-- | :-- | :-- |",
        ]

        for rank, ((before, after), info) in enumerate(sorted_entries, 1):
            phases_str = " ".join(sorted(set(info["phases"])))
            files_str  = "、".join(sorted(set(info["files"])))
            reason_str = "；".join(info["reasons"]) if info["reasons"] else "—"
            lines.append(
                f"| {rank} | `{before}` | `{after}` | {info['count']} | {phases_str} | {files_str} | {reason_str} |"
            )

        lines += [
            f"",
            f"---",
            f"",
            f"## 使用說明",
            f"",
            f"- **重複次數高** → 表示同一術語在多份逐字稿中被修正，確認正確性後可加入 `glossary.json` 固化。",
            f"- **P2 + P3 均出現** → 同一問題在 ASR 和去噪兩個階段都有處理，需人工確認兩次修正是否一致。",
            f"- **次數 = 1 且無理由** → 可能是邊緣修正，優先核查。",
        ]

        # 寫入輸出
        out_dir  = os.path.join(sm.PROOFREAD_DIR, subj)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "校對總報告.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        sm.log_msg(f"✅ 報告已生成：{out_path}（{len(filtered)} 筆條目）")

    sm.log_msg("🏁 audit_tool 執行完畢。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cross-phase change log aggregator: generates 校對總報告.md per subject"
    )
    parser.add_argument("--subject", "-s", nargs="+", metavar="SUBJECT",
                        help="Target specific subject(s). Default: all.")
    parser.add_argument("--min-count", "-n", type=int, default=1, metavar="N",
                        help="Only include entries appearing >= N times. Default: 1.")
    args = parser.parse_args()

    run_audit(
        target_subjects=args.subject,
        min_count=args.min_count
    )
