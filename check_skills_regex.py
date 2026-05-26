import os
import re

skills_dir = 'openclaw-sandbox/skills'
dirs = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d)) and d != '__pycache__']

missing_files = []
wrong_location = []
invalid_yaml = []
missing_fields = []
safety_warnings = []

for d in dirs:
    skill_md = os.path.join(skills_dir, d, 'SKILL.md')
    if not os.path.exists(skill_md):
        if os.path.exists(os.path.join(skills_dir, d, 'docs', 'SKILL.md')):
            wrong_location.append(d)
            skill_md = os.path.join(skills_dir, d, 'docs', 'SKILL.md')
        else:
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
    
    if not re.search(r'^name:\s+', frontmatter, re.MULTILINE):
        missing_fields.append(f"{d} (missing name)")
    if not re.search(r'^description:\s+', frontmatter, re.MULTILINE):
        missing_fields.append(f"{d} (missing description)")
        
    # Completeness/Safety checks in body
    has_quick_start = "Quick Start" in body or "Commands" in body or "run_all.py" in body
    has_safety = "Hallucination" in body or "Anti-Tampering" in body or "Safety" in body or "Zero Temperature" in body or "guard" in body.lower()
    
    if not has_quick_start:
        safety_warnings.append(f"{d} (No execution/Quick Start instructions)")
    if not has_safety:
        safety_warnings.append(f"{d} (No safety/hallucination checks mentioned)")

print("=== Check Results ===")
print(f"Missing SKILL.md: {missing_files}")
print(f"SKILL.md in wrong location (e.g. docs/): {wrong_location}")
print(f"Missing YAML Frontmatter: {invalid_yaml}")
print(f"Missing name/desc in frontmatter: {missing_fields}")
print(f"Completeness/Safety Warnings: {safety_warnings}")

