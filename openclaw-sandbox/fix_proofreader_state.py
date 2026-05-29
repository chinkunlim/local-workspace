import glob
import json
import os

state_file = "data/proofreader/state/.pipeline_state.json"
smart_hl_dir = "data/smart_highlighter/input"

# Ensure state file exists
if not os.path.exists(state_file):
    state = {}
else:
    with open(state_file, encoding="utf-8") as f:
        state = json.load(f)

# Scan smart_highlighter/input for all subjects
for subj in os.listdir(smart_hl_dir):
    subj_dir = os.path.join(smart_hl_dir, subj)
    if not os.path.isdir(subj_dir) or subj == "Default":
        continue

    if subj not in state:
        state[subj] = {}

    # Get all .md files that have successfully passed proofreader and are waiting in smart_highlighter
    md_files = glob.glob(os.path.join(subj_dir, "*.md"))
    for f in md_files:
        fname = os.path.basename(f)
        if fname not in state[subj]:
            state[subj][fname] = {}

        # Mark as completed
        state[subj][fname]["p1"] = "✅"
        state[subj][fname]["p2"] = "✅"
        state[subj][fname]["p3"] = "✅"
        state[subj][fname]["note"] = "✅ 已手動修復 (從後續管線回推)"

with open(state_file, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print("Proofreader state fixed successfully.")
