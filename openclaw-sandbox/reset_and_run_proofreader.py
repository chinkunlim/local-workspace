import json
import os

state_file = "data/proofreader/state/.pipeline_state.json"

if os.path.exists(state_file):
    with open(state_file) as f:
        state = json.load(f)

    for subj in state:
        for fname in state[subj]:
            # Reset only those that were marked as ✅ by our previous fix
            if state[subj][fname].get("note") == "✅ 已手動修復 (從後續管線回推)":
                state[subj][fname]["p1"] = "⏳"
                state[subj][fname]["p2"] = "⏳"
                state[subj][fname]["p3"] = "⏳"
                state[subj][fname]["note"] = "Reset for regenerating intermediate files"

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print("State reset successfully.")
