import glob
import json
import os
import re

state_file = "data/audio_transcriber/state/.pipeline_state.json"
smart_hl_dir = "data/smart_highlighter/input"

with open(state_file, encoding="utf-8") as f:
    state = json.load(f)

for subj in state:
    if subj == "Default":
        continue

    # Check if this subject exists in smart_highlighter/input
    subj_dir = os.path.join(smart_hl_dir, subj)
    if not os.path.exists(subj_dir):
        continue

    # Get all .md files in the subject dir
    md_files = glob.glob(os.path.join(subj_dir, "*.md"))
    completed_prefixes = [os.path.splitext(os.path.basename(f))[0] for f in md_files]

    for fname, record in state[subj].items():
        # fname is like L14-1.m4a or L02.m4a
        base_prefix = os.path.splitext(fname)[0]  # L14-1

        # Strip trailing -1, -2 etc if it exists to match L14
        match = re.match(r"(.*?)(-\d+)?$", base_prefix)
        group_prefix = match.group(1) if match else base_prefix

        if group_prefix in completed_prefixes or base_prefix in completed_prefixes:
            # It's completed!
            record["p1"] = "✅"
            record["p2"] = "✅"
            record["p3"] = "✅"
            record["note"] = "✅ 已手動修復 (從後續管線回推)"

with open(state_file, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print("State fixed successfully.")
