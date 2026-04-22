"""
core/cli_menu.py — Unified Interactive Menu for Open Claw Pipelines
===================================================================
提供所有 Skill 共用的終端機互動介面，包含安全的 Ctrl+C 攔截機制，
支援複雜的範圍選取 (如 1,3,5 或 1-5)。
"""

import signal
import sys
from typing import Dict, List


class SafeInputContext:
    """
    Temporarily disables the pipeline's SIGINT handler so input() can catch KeyboardInterrupt directly.
    This prevents the 'can't re-enter readline' crash when pressing Ctrl+C inside an input prompt.
    """

    def __enter__(self):
        self.old_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.default_int_handler)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.signal(signal.SIGINT, self.old_sigint)


def parse_selection_range(raw: str, max_idx: int) -> set:
    """Parse a string like '1,3, 5-7' into a set of 0-based indices."""
    selected = set()
    tokens = raw.replace(",", " ").split()
    for tok in tokens:
        if "-" in tok:
            parts = tok.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start, end = int(parts[0]), int(parts[1])
                for i in range(start, end + 1):
                    if 1 <= i <= max_idx:
                        selected.add(i - 1)
        elif tok.isdigit():
            i = int(tok)
            if 1 <= i <= max_idx:
                selected.add(i - 1)
    return selected


def batch_select_tasks(tasks: List[Dict], header: str = "已完成的檔案") -> Dict[int, Dict]:
    """
    Interactive terminal menu for selecting tasks to re-process.
    Supports range selection, select all, skip all.
    """
    selected: set[int] = set()

    def render():
        print("\n" + "═" * 56)
        print(f"   ⚠️  偵測到 {len(tasks)} 個 {header}")
        print("═" * 56)
        for i, task in enumerate(tasks, 1):
            mark = "●" if (i - 1) in selected else "○"
            print(f"  [{i:>2}] {mark} {task['subject']} / {task['filename']}")
        print("-" * 56)
        print("   數字/範圍 (如 1,3,5 或 1-5) = 切換選取")
        print("   A = 全選  |  S = 全部跳過")
        if selected:
            print(f"   已選取 {len(selected)} 個 → 按 [Enter] 確認執行")
        else:
            print("   按 [Enter] 或 S = 略過全部")
        print("-" * 56)

    render()

    while True:
        with SafeInputContext():
            try:
                raw = input("   > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n   [強制退出]")
                sys.exit(0)

        if raw == "s":
            print(f"   ⏭️  已選擇跳過全部 {len(tasks)} 個檔案。")
            return {}
        elif raw == "":
            if not selected:
                print(f"   ⏭️  未選取任何項目，跳過全部 {len(tasks)} 個檔案。")
                return {}
            else:
                chosen = {i: tasks[i] for i in sorted(selected)}
                print(f"   ✅ 確認處理 {len(chosen)} 個檔案。")
                return chosen
        elif raw == "a":
            selected = set(range(len(tasks)))
            render()
            print(f"   ✅ 已全選全部 {len(tasks)} 個檔案。")
            return {i: tasks[i] for i in sorted(selected)}
        else:
            parsed = parse_selection_range(raw, len(tasks))
            if not parsed:
                print("   ⚠️  無法辨識指令，請輸入正確的數字、範圍或 A/S。")
            else:
                for idx in parsed:
                    if idx in selected:
                        selected.discard(idx)
                    else:
                        selected.add(idx)
                render()
