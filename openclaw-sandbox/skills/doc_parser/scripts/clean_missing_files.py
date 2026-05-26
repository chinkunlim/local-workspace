import json
import os
from pathlib import Path

state_file = Path("data/doc_parser/state/.pipeline_state.json")
input_dir = Path("data/doc_parser/input")

if not state_file.exists():
    print("State file not found.")
    exit(0)

with open(state_file) as f:
    state = json.load(f)

to_remove = []

for subject, files in state.items():
    if not isinstance(files, dict):
        continue
    for filename in files:
        file_path = input_dir / subject / filename
        if not file_path.exists():
            print(f"Removing stale state entry: {subject}/{filename}")
            to_remove.append((subject, filename))

for subject, filename in to_remove:
    del state[subject][filename]
    if not state[subject]:
        del state[subject]

with open(state_file, "w") as f:
    json.dump(state, f, indent=4, ensure_ascii=False)

print(f"Removed {len(to_remove)} stale entries.")
