import os
import glob
import yaml
import sys

skills_dir = 'openclaw-sandbox/skills'
dirs = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d)) and d != '__pycache__']

missing_files = []
invalid_yaml = []
missing_name_or_desc = []
safety_issues = []

for d in dirs:
    skill_md = os.path.join(skills_dir, d, 'SKILL.md')
    if not os.path.exists(skill_md):
        # Some skills might have it in docs/SKILL.md
        skill_md = os.path.join(skills_dir, d, 'docs', 'SKILL.md')
    
    if not os.path.exists(skill_md):
        missing_files.append(d)
        continue
        
    with open(skill_md, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if not content.startswith('---'):
        invalid_yaml.append(d)
        continue
        
    parts = content.split('---', 2)
    if len(parts) < 3:
        invalid_yaml.append(d)
        continue
        
    frontmatter = parts[1]
    body = parts[2]
    
    try:
        data = yaml.safe_load(frontmatter)
        if not data or 'name' not in data or 'description' not in data:
            missing_name_or_desc.append(d)
    except Exception as e:
        invalid_yaml.append(f"{d} ({str(e)})")
        
    # Check completeness and safety in body
    # e.g., usage examples, warnings, "safety", etc.
    if "python3" not in body and "uv run" not in body and "bash" not in body.lower():
        safety_issues.append(f"{d} (No execution examples)")

print("=== Check Results ===")
print(f"Missing SKILL.md: {missing_files}")
print(f"Invalid YAML: {invalid_yaml}")
print(f"Missing name/desc: {missing_name_or_desc}")
print(f"Potential Safety/Completeness Issues: {safety_issues}")

