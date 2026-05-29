#!/usr/bin/env python3
"""
recover_state_from_logs.py
==========================
掃描指定 skill 的 pipeline.log，辨識已完成的任務並寫回 .pipeline_state.json，
最後由 StateManager 自動重新渲染 checklist.md。

使用方式:
  python recover_state_from_logs.py --skill <skill_name>
"""

import argparse
import json
import os
import re
import sys

from core.utils.bootstrap import ensure_core_path

ensure_core_path(__file__)

from core.state.state_manager import StateManager


def recover_skill_state(skill_name: str, force: bool = False):
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    skill_data_dir = os.path.join(workspace_root, "data", skill_name)
    log_file = os.path.join(skill_data_dir, "logs", "pipeline.log")

    if not os.path.exists(skill_data_dir):
        print(f"❌ 找不到技能資料夾: {skill_data_dir}")
        return

    print(f"🔍 開始復原技能 [{skill_name}] 的狀態...")

    manager = StateManager(skill_data_dir, skill_name=skill_name)
    # First sync physical inbox files so we have the base records
    manager.sync_physical_files()

    if not os.path.exists(log_file):
        print(f"⚠️ 找不到日誌檔: {log_file}，僅能根據 Inbox 同步基礎狀態。")
        manager._render_checklist()
        print("✅ checklist.md 重新渲染完成。")
        return

    # We look for typical completion signatures in the logs.
    # Pattern examples:
    # "✅ 已儲存 Checkpoint：[Subject] filename @ P1"
    # Or updating task logs. However, pipeline_base finishes tasks with:
    # "✅ 完成" but it might not have the file name.
    # The most reliable log is the checkpoint or update_task trace.
    # Actually, a simple way is to check the output folders. But the user requested log parsing.

    # Regex to match: ✅ 已儲存 Checkpoint：[Subject] filename @ PHASE_KEY
    checkpoint_pattern = re.compile(r"已儲存 Checkpoint：\[(.*?)\]\s+(.*?)\s+@\s+([A-Z0-9_]+)")

    recovered_count = 0
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            match = checkpoint_pattern.search(line)
            if match:
                subject, filename, phase_key = match.groups()
                phase_key = phase_key.lower()

                # Check if this task exists
                if subject in manager.state and filename in manager.state[subject]:
                    current_status = manager.state[subject][filename].get(phase_key)
                    if current_status != "✅":
                        manager.update_task(subject, filename, phase_key, "✅")
                        recovered_count += 1
                        print(f"  └─ 復原紀錄: [{subject}] {filename} -> {phase_key.upper()} = ✅")

    if recovered_count > 0:
        print(f"🎉 成功從日誌中復原 {recovered_count} 筆進度紀錄！")
    else:
        print("ℹ️ 日誌中無額外可復原的進度，或現有狀態已是最新。")

    # Force render checklist
    manager._render_checklist()
    print(f"✅ [{skill_name}] 的 checklist.md 已重新渲染完成。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="從 logs 中復原 pipeline_state 並更新 checklist.md"
    )
    parser.add_argument(
        "--skill", type=str, required=True, help="要復原的技能名稱 (例如: doc_parser)"
    )
    parser.add_argument("--all", action="store_true", help="復原所有技能")
    args = parser.parse_args()

    if args.all:
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        skills_dir = os.path.join(workspace_root, "skills")
        for skill in os.listdir(skills_dir):
            if os.path.isdir(os.path.join(skills_dir, skill)) and skill != "__pycache__":
                recover_skill_state(skill)
    else:
        recover_skill_state(args.skill)
