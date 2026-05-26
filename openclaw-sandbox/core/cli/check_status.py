"""
core/check_status.py — 全系統狀態報告產生器
==========================================
提供給 Telegram Bot 或是 CLI 使用，一次性輸出所有核心 Skill 的進度儀表板。
"""

import os
import sys

from core.utils.log_manager import build_logger

logger = build_logger(__name__, console=True)

from core.utils.workspace import get_workspace_root

_workspace_root = get_workspace_root()

from core.state.state_manager import StateManager
from core.utils.path_builder import PathBuilder


def get_full_status_report() -> str:
    """產生包含多個 Skill 的聯合儀表板報告。"""
    report_lines = []

    # 定義要檢查的 Skill 列表
    skills_to_check = ["doc_parser", "audio_transcriber"]

    for skill in skills_to_check:
        try:
            pb = PathBuilder(_workspace_root, skill)
            sm = StateManager(pb.base_dir, skill_name=skill)

            # 從 StateManager 獲取儀表板文字
            dashboard_text = sm.get_dashboard_text()
            report_lines.append(dashboard_text)
        except Exception as e:
            report_lines.append(f"⚠️ 無法讀取 {skill} 狀態: {e}\n")

    return "\n".join(report_lines)


if __name__ == "__main__":
    logger.info(get_full_status_report())
