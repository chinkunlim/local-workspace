#!/usr/bin/env python3
"""
backfill_lang.py — 從 system.log 回填語言偵測結果到 .pipeline_state.json，並重新渲染 checklist.md
"""

import json
import os
import re
import sys

# 確保可以 import core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from core.state.state_manager import StateManager

LOG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "audio_transcriber", "logs", "system.log"
)
LOG_PATH = os.path.abspath(LOG_PATH)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "audio_transcriber")
DATA_DIR = os.path.abspath(DATA_DIR)


def parse_log(log_path):
    """
    從 log 解析每個檔案最後一次的語言偵測結果。
    回傳 dict: {(subject, filename): lang}
    """
    results = {}
    current_subj = None
    current_fname = None

    # 正則：正在處理
    re_processing = re.compile(r"正在處理：\[(.+?)\] (.+?)$")
    # 正則：語言偵測結果（包含被強制切換的）
    re_lang_final = re.compile(r"語言偵測結果：\[(.+?)\]")

    with open(log_path, encoding="utf-8") as f:
        for line in f:
            m = re_processing.search(line)
            if m:
                current_subj = m.group(1).strip()
                current_fname = m.group(2).strip()
                continue

            m = re_lang_final.search(line)
            if m and current_subj and current_fname:
                detected = m.group(1).strip()
                # 套用與 p01_transcribe.py 相同的語言過濾邏輯
                lang = "en" if detected not in ("zh", "en") else detected
                results[(current_subj, current_fname)] = lang

    return results


def main():
    print(f"📂 讀取 log：{LOG_PATH}")
    lang_map = parse_log(LOG_PATH)
    print(f"✅ 從 log 解析到 {len(lang_map)} 筆語言記錄。")

    sm = StateManager(base_dir=DATA_DIR, skill_name="audio_transcriber")

    updated = 0
    not_found = 0

    for (subj, fname), lang in lang_map.items():
        if subj in sm.state and fname in sm.state[subj]:
            sm.state[subj][fname]["lang"] = lang
            updated += 1
        else:
            not_found += 1

    if updated > 0:
        sm._save_state()
        sm._render_checklist()
        print(f"✅ 已回填 {updated} 筆語言資料並重新渲染 checklist.md。")
    else:
        print("⚠️ 沒有找到任何匹配的記錄，state 未變更。")

    if not_found > 0:
        print(f"ℹ️  {not_found} 筆 log 記錄在 state 中找不到對應檔案（可能已移除或路徑不符）。")

    # 統計
    print("\n📊 語言分布統計（回填後）：")
    lang_counts = {}
    for subj_data in sm.state.values():
        for file_data in subj_data.values():
            l = file_data.get("lang", "—")
            lang_counts[l] = lang_counts.get(l, 0) + 1
    for l, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        print(f"   [{l}]: {count} 筆")


if __name__ == "__main__":
    main()
