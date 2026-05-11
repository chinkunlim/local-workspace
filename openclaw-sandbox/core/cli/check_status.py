"""
core/check_status.py — 全系統狀態報告產生器
==========================================
提供給 Telegram Bot 或是 CLI 使用，一次性輸出所有核心 Skill 的進度儀表板。
"""

import os
import sys

# 確保 core 模組可被引入
_core_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(_core_dir, "..")))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

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
    print(get_full_status_report())
