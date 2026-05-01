import os

replacements = [
    (".claude_profile.md", "AI_PROFILE.md")
]

skip_dirs = {".git", "data", "models", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache", "logs"}

modified_files = []

for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for file in files:
        if file.endswith((".py", ".md", ".json", ".yaml", ".toml", ".sh", ".txt")):
            path = os.path.join(root, file)
            if path.endswith("update_profile_name.py"):
                continue
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements:
                new_content = new_content.replace(old, new)
                
            if new_content != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                modified_files.append(path)

print("Modified files:")
for f in modified_files:
    print(f)
