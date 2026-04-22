import os

SKILLS_DIR = "skills"
FEATURE_TEXT = "\n- **全域標準化介面 (Global Standardization)**: 採用統一的 CLI 狀態與 DAG 追蹤面板，支援 macOS 原生系統通知 (osascript)，並具備 `KeyboardInterrupt` 優雅中斷保護。\n"

for root, dirs, files in os.walk(SKILLS_DIR):
    if "SKILL.md" in files:
        path = os.path.join(root, "SKILL.md")
        # Skip the root skills/SKILL.md
        if path == "skills/SKILL.md":
            continue

        with open(path, encoding="utf-8") as f:
            content = f.read()

        if "全域標準化介面" not in content:
            # Try to insert after ## Features or ## 功能特性
            if "## Features" in content:
                content = content.replace("## Features\n", "## Features\n" + FEATURE_TEXT)
            elif "## 核心特性" in content:
                content = content.replace("## 核心特性\n", "## 核心特性\n" + FEATURE_TEXT)
            else:
                # Append to the end if section not found
                content += "\n## 全域標準化\n" + FEATURE_TEXT

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated: {path}")
