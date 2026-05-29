import os
import shutil

smart_hl_dir = "data/smart_highlighter/input"
proofreader_out_dir = "data/proofreader/output/03_doc_completeness"

for subj in os.listdir(smart_hl_dir):
    subj_dir = os.path.join(smart_hl_dir, subj)
    if not os.path.isdir(subj_dir) or subj == "Default":
        continue

    for fname in os.listdir(subj_dir):
        if not fname.endswith(".md"):
            continue

        src_path = os.path.join(subj_dir, fname)
        dst_dir = os.path.join(proofreader_out_dir, subj)
        dst_path = os.path.join(dst_dir, fname)

        if not os.path.exists(dst_path):
            os.makedirs(dst_dir, exist_ok=True)
            # Use copy so they exist in both places (pre-HITL in smart_highlighter, and waiting for HITL in proofreader)
            shutil.copy2(src_path, dst_path)
            print(f"Restored to Dashboard: {subj}/{fname}")

print("Dashboard files restored successfully.")
