#!/usr/bin/env python3
"""
reset_files.py — 重置指定檔案的 P1 狀態，強制下一次執行時重新轉錄
用法: uv run skills/audio_transcriber/scripts/reset_files.py <subject> <filename> [<subject2> <filename2> ...]
範例: uv run skills/audio_transcriber/scripts/reset_files.py 114-2_物理實驗 L02.m4a 114-2_社會心理學 L03.m4a
"""

import os
import sys

from core.state.state_manager import StateManager

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "audio_transcriber")
)
OUTPUT_P1_DIR = os.path.join(DATA_DIR, "output", "01_transcribe")
OUTPUT_P1_TS_DIR = os.path.join(DATA_DIR, "output", "01_transcribe_ts")


def reset_file(sm: StateManager, subject: str, filename: str):
    stem = os.path.splitext(filename)[0]

    if subject not in sm.state or filename not in sm.state[subject]:
        print(f"  ⚠️  [{subject}] {filename} — 在 state 中找不到，跳過。")
        return

    record = sm.state[subject][filename]

    # 重置所有 phase 狀態
    for phase in sm.PHASES:
        if phase in record:
            record[phase] = "⏳"

    # 清除 lang（將由下次轉錄重新偵測與寫入）
    record.pop("lang", None)
    record.pop("note", None)
    record.pop("char_count", None)
    record.pop("output_hashes", None)

    print(f"  ✅ [{subject}] {filename} — state 已重置為 ⏳")

    # 刪除 P1 輸出檔
    for out_dir in [OUTPUT_P1_DIR, OUTPUT_P1_TS_DIR]:
        for ext in [".txt", ".md"]:
            path = os.path.join(out_dir, subject, stem + ext)
            if os.path.exists(path):
                os.remove(path)
                print(f"     🗑️  已刪除：{os.path.relpath(path)}")


def main():
    args = sys.argv[1:]
    if not args or len(args) % 2 != 0:
        print("用法: reset_files.py <subject> <filename> [<subject2> <filename2> ...]")
        print("範例: reset_files.py 114-2_物理實驗 L02.m4a 114-2_社會心理學 L03.m4a")
        sys.exit(1)

    pairs = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]

    sm = StateManager(base_dir=DATA_DIR, skill_name="audio_transcriber")

    print(f"🔄 重置 {len(pairs)} 個檔案的轉錄狀態...\n")
    for subject, filename in pairs:
        reset_file(sm, subject, filename)

    sm._save_state()
    sm._render_checklist()
    print("\n✅ state 已儲存，checklist.md 已重新渲染。")
    print("▶️  現在可以執行 uv run skills/audio_transcriber/scripts/run_all.py 重新轉錄。")


if __name__ == "__main__":
    main()
