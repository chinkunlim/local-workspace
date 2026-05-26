import os
import re

files_to_update = [
    "docs/STRUCTURE.md",
    "docs/CODING_GUIDELINES.md",
    "docs/DEVELOPMENT_MANUAL.md",
    "docs/INDEX.md",
    "openclaw-sandbox/skills/SKILL.md"
]

for file_path in files_to_update:
    if not os.path.exists(file_path):
        print(f"Skipping {file_path}, not found.")
        continue
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    original = content
    
    if "INDEX.md" in file_path:
        # Replace [Claude](.../docs/PROJECT_RULES.md) with [Rules](.../docs/SKILL_RULE.md)
        content = re.sub(
            r'\[Claude\]\(([^)]*?/docs/)PROJECT_RULES\.md\)', 
            r'[Rules](\1SKILL_RULE.md)', 
            content
        )
    elif "STRUCTURE.md" in file_path:
        # Replace `└── PROJECT_RULES.md               ← AI collaboration context for this skill`
        content = content.replace(
            "└── PROJECT_RULES.md               ← AI collaboration context for this skill",
            "└── SKILL_RULE.md                  ← AI collaboration context for this skill"
        )
    elif "CODING_GUIDELINES.md" in file_path:
        content = content.replace(
            "| **Skill** | `openclaw-sandbox/skills/<skill>/docs/` | Skill owner | `ARCHITECTURE.md`, `PROJECT_RULES.md`, `DECISIONS.md` |",
            "| **Skill** | `openclaw-sandbox/skills/<skill>/docs/` | Skill owner | `ARCHITECTURE.md`, `SKILL_RULE.md`, `DECISIONS.md` |"
        )
    elif "DEVELOPMENT_MANUAL.md" in file_path:
        content = content.replace(
            "ARCHITECTURE.md, PROJECT_RULES.md, and DECISIONS.md",
            "ARCHITECTURE.md, SKILL_RULE.md, and DECISIONS.md"
        )
    elif "SKILL.md" in file_path:
        content = content.replace(
            "├── PROJECT_RULES.md         # AI collaboration context & constraints",
            "├── SKILL_RULE.md            # AI collaboration context & constraints"
        )

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {file_path}")
    else:
        print(f"No changes made to {file_path}")

