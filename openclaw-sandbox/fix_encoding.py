import re

files_to_fix = {
    "skills/doc_parser/scripts/clean_missing_files.py": r"open\(state_file\)",
    "skills/doc_parser/scripts/phases/p01a_engine.py": r"open\(path\)",
    "skills/doc_parser/scripts/phases/p01b_vector_charts.py": r"open\(report_path\)",
    "skills/doc_parser/scripts/phases/p01c_ocr_gate.py": r"open\(report_path\)",
}

for filepath, pattern in files_to_fix.items():
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Replace open(var) with open(var, encoding="utf-8")
    new_content = re.sub(pattern, lambda m: m.group(0)[:-1] + ', encoding="utf-8")', content)

    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed {filepath}")
