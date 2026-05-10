import os
import re

files_to_fix = [
    "core/utils/diff_engine.py",
    "core/utils/file_utils.py",
    "core/utils/glossary_manager.py",
    "core/cli/cli_config_wizard.py",
    "core/state/memory_updater.py",
    "core/services/sm2.py",
    "skills/academic_library_agent/scripts/phases/p01_search_literature.py",
    "skills/feynman_simulator/scripts/phases/p01_feynman_debate.py",
    "skills/feynman_simulator/scripts/phases/p02_debate_synthesis.py",
    "skills/gemini_verifier_agent/scripts/phases/p01_ai_debate.py",
    "skills/student_researcher/scripts/phases/p02_synthesis.py",
    "skills/student_researcher/scripts/phases/p01_claim_extraction.py",
    "skills/proofreader/scripts/dashboard.py"
]

def add_import(content):
    if "from core.utils.atomic_writer import AtomicWriter" in content:
        return content
    # Find the last import
    lines = content.split('\n')
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            last_import_idx = i
    
    lines.insert(last_import_idx + 1, "from core.utils.atomic_writer import AtomicWriter")
    return '\n'.join(lines)

def process_file(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        content = f.read()
        
    original = content
    
    # Replace json.dump
    content = re.sub(
        r'with open\(([^,]+),\s*["\']w["\'].*?\) as (\w+):\s*json\.dump\(([^,]+),\s*\2,\s*ensure_ascii=False,\s*indent=2\)',
        r'AtomicWriter.write_json(\1, \3)',
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(
        r'with open\(([^,]+),\s*["\']w["\'].*?\) as (\w+):\s*json\.dump\(([^,]+),\s*\2.*?\)',
        r'AtomicWriter.write_json(\1, \3)',
        content,
        flags=re.DOTALL
    )

    # Replace simple f.write
    content = re.sub(
        r'with open\(([^,]+),\s*["\']w["\'].*?\) as (\w+):\s*\2\.write\(([^)]+)\)',
        r'AtomicWriter.write_text(\1, \3)',
        content,
        flags=re.DOTALL
    )

    if content != original:
        content = add_import(content)
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Refactored {filepath}")

for f in files_to_fix:
    process_file(f)

