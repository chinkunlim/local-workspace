#!/bin/bash
cd /Users/limchinkun/Desktop/local-workspace/openclaw-sandbox

echo "=== Resetting doc_parser state ==="
python3 -c '
import json, os
path = "data/doc_parser/state/.pipeline_state.json"
if os.path.exists(path):
    with open(path, "r") as f:
        state = json.load(f)
    if "114-2_消費者心理學" in state:
        del state["114-2_消費者心理學"]
        with open(path, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
'

echo "=== Resetting proofreader state ==="
python3 -c '
import json, os
path = "data/proofreader/state/.pipeline_state.json"
if os.path.exists(path):
    with open(path, "r") as f:
        state = json.load(f)
    if "114-2_消費者心理學" in state:
        del state["114-2_消費者心理學"]
        with open(path, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
'

echo "=== Removing old doc_parser outputs ==="
rm -rf data/doc_parser/output/01_processed/114-2_消費者心理學/*

echo "=== Running doc_parser ==="
uv run skills/doc_parser/scripts/run_all.py --subject "114-2_消費者心理學"

echo "=== Running proofreader ==="
# Echo empty lines to bypass the dashboard prompt
echo -e "\n\n" | uv run skills/proofreader/scripts/run_all.py --subject "114-2_消費者心理學"

echo "=== DONE ==="
