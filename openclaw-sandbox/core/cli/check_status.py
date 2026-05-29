"""
core/check_status.py — 全系統狀態報告產生器
==========================================
提供給 Telegram Bot 或是 CLI 使用，一次性輸出所有核心 Skill 的進度儀表板。
"""

import os

# from core.utils.log_manager import build_logger
# logger = build_logger(__name__, console=True)
from core.utils.workspace import get_workspace_root

_workspace_root = get_workspace_root()

from core.state.state_manager import StateManager
from core.utils.path_builder import PathBuilder


def get_full_status_report() -> str:
    """產生包含多個 Skill 的聯合儀表板報告。"""
    report_lines = []

    # 定義使用者偏好的管線顯示順序
    preferred_order = [
        "audio_transcriber",
        "doc_parser",
        "proofreader",
        "smart_highlighter",
        "note_generator",
        "knowledge_compiler",
        "researcher_agent",
    ]

    # 動態掃描所有有狀態的 Skill
    data_dir = os.path.join(_workspace_root, "data")
    found_skills = set()
    if os.path.isdir(data_dir):
        for d in os.listdir(data_dir):
            if d == "_global_":
                continue
            state_file = os.path.join(data_dir, d, "state", ".pipeline_state.json")
            if os.path.isfile(state_file):
                found_skills.add(d)

    # 確保基本順序，根據 preferred_order 排序
    skills_to_check = []
    for skill in preferred_order:
        if skill in found_skills:
            skills_to_check.append(skill)
            found_skills.remove(skill)

    # 如果還有其他的，就按字母順序加在後面
    skills_to_check.extend(sorted(found_skills))

    # 如果還是空的，就放預設的
    if not skills_to_check:
        skills_to_check = [
            "audio_transcriber",
            "doc_parser",
            "proofreader",
            "smart_highlighter",
            "note_generator",
        ]

    for skill in skills_to_check:
        try:
            pb = PathBuilder(_workspace_root, skill)
            sm = StateManager(pb.base_dir, skill_name=skill)

            # 從 StateManager 獲取儀表板文字
            dashboard_text = sm.get_dashboard_text()
            if dashboard_text:
                report_lines.append(dashboard_text)
        except Exception as e:
            report_lines.append(f"⚠️ 無法讀取 {skill} 狀態: {e}\n")

    if not report_lines:
        return "目前沒有任何排隊中的任務或已初始化的狀態。"

    return "\n".join(report_lines)


if __name__ == "__main__":
    print(get_full_status_report())
