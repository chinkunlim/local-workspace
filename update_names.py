import os

replacements = [
    ("AI_Master_Guide_Final.md", "INFRA_SETUP.md"),
    ("CODING_GUIDELINES_FINAL.md", "CODING_GUIDELINES.md"),
    ("audio-transcriber", "audio_transcriber"),
    ("doc-parser", "doc_parser"),
    ("academic-edu-assistant", "academic_edu_assistant"),
    ("knowledge-compiler", "knowledge_compiler"),
    ("telegram-kb-agent", "telegram_kb_agent"),
    ("inbox-manager", "inbox_manager"),
    ("interactive-reader", "interactive_reader")
]

skip_dirs = {".git", "data", "models", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache", "logs", "open-webui", "litellm", "pipelines"}

modified_files = []

for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for file in files:
        if file.endswith((".py", ".md", ".json", ".yaml", ".toml", ".sh", ".txt")):
            path = os.path.join(root, file)
            # Exclude this script
            if path.endswith("update_names.py"):
                continue
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements:
                # Be careful not to replace text in URLs blindly, but in our case these are our own folders.
                new_content = new_content.replace(old, new)
                
            if new_content != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                modified_files.append(path)

print("Modified files:")
for f in modified_files:
    print(f)
