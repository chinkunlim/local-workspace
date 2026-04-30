import os
import re

SKILLS_DIR = "skills"
MAPPINGS = {
    "audio-transcriber": "語音轉錄",
    "doc-parser": "文件解析",
    "academic-edu-assistant": "學術教育助手",
    "interactive-reader": "互動式閱讀器",
    "knowledge-compiler": "知識庫編譯",
    "note_generator": "筆記生成",
    "smart_highlighter": "智慧標注",
    "inbox-manager": "收件匣管理",
    "telegram-kb-agent": "Telegram 知識庫代理",
}

for skill_folder in os.listdir(SKILLS_DIR):
    md_path = os.path.join(SKILLS_DIR, skill_folder, "SKILL.md")
    if os.path.exists(md_path) and skill_folder in MAPPINGS:
        zh_name = MAPPINGS[skill_folder]
        target_text = f"**全域標準化介面 (Global Standardization)**: 採用統一的 CLI 狀態與 DAG 追蹤面板 (`📊 {zh_name}狀態與 DAG 追蹤面板`)"

        with open(md_path, encoding="utf-8") as f:
            content = f.read()

        # Replace the old appended text if exists
        content = re.sub(
            r"\*\*全域標準化介面 \(Global Standardization\)\*\*: 採用統一的 CLI 狀態與 DAG 追蹤面板.*?(，|。|\n)",
            target_text + r"\1",
            content,
        )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {md_path} with {zh_name}")
