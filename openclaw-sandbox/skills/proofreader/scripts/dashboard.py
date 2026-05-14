"""
dashboard.py — Centralized Verification Dashboard for Proofreader
================================================================
Provides a persistent, non-blocking WebUI for Human-in-the-Loop verification.
It scans `data/proofreader/output/` for AI-corrected files, and pairs them
with the ground truth original files from `data/raw/`.
"""

import json
import os
import sys

# Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from flask import Flask, jsonify, render_template_string, request, send_file

from core.utils.atomic_writer import AtomicWriter

app = Flask(__name__)

# Resolve Paths
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RAW_DIR = os.path.join(WORKSPACE_ROOT, "data", "raw")
DOC_INPUT_DIR = os.path.join(WORKSPACE_ROOT, "data", "doc_parser", "input")
AUDIO_INPUT_DIR = os.path.join(WORKSPACE_ROOT, "data", "audio_transcriber", "input")
PROOFREADER_OUT_DIR = os.path.join(WORKSPACE_ROOT, "data", "proofreader", "output")


def find_original_media(subject: str, md_filename: str) -> str:
    """Attempt to find the original Ground Truth media for a given markdown output."""
    base_name = os.path.splitext(md_filename)[0]
    # Remove suffix like "_proofread" or similar
    if base_name.endswith("_proofread"):
        base_name = base_name.replace("_proofread", "")

    search_dirs = [
        os.path.join(DOC_INPUT_DIR, subject),
        os.path.join(AUDIO_INPUT_DIR, subject),
        os.path.join(RAW_DIR, subject),
    ]

    for subj_raw_dir in search_dirs:
        if not os.path.exists(subj_raw_dir):
            continue

        # Check common extensions
        for ext in [".pdf", ".png", ".jpg", ".jpeg", ".m4a", ".mp3", ".wav"]:
            cand_path = os.path.join(subj_raw_dir, base_name + ext)
            if os.path.exists(cand_path):
                return cand_path

            # Sometimes the base_name in audio has "_merged" or similar.
            # Fallback partial matching
            for f in os.listdir(subj_raw_dir):
                if f.endswith(ext) and (base_name in f or f.replace(ext, "") in base_name):
                    return os.path.join(subj_raw_dir, f)

    return ""


def get_media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return "pdf"
    elif ext in [".png", ".jpg", ".jpeg"]:
        return "image"
    elif ext in [".m4a", ".mp3", ".wav"]:
        return "audio"
    return "unknown"


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/files")
def list_files():
    """Scan all proofreader outputs and group by subject."""
    results = {}

    if not os.path.exists(PROOFREADER_OUT_DIR):
        return jsonify(results)

    # Phases to check
    phases = ["01_doc_proofread", "02_transcript_proofread", "03_doc_completeness"]

    for phase in phases:
        phase_dir = os.path.join(PROOFREADER_OUT_DIR, phase)
        if not os.path.exists(phase_dir):
            continue

        for subj in os.listdir(phase_dir):
            subj_dir = os.path.join(phase_dir, subj)
            if not os.path.isdir(subj_dir):
                continue

            if subj not in results:
                results[subj] = []

            for fname in os.listdir(subj_dir):
                if not fname.endswith(".md") or fname == "correction_log.md":
                    continue

                md_path = os.path.join(subj_dir, fname)
                orig_path = find_original_media(subj, fname)

                verified_path = os.path.join(PROOFREADER_OUT_DIR, "04_final_verified", subj, fname)
                is_verified = os.path.exists(verified_path)

                results[subj].append(
                    {
                        "id": f"{phase}/{subj}/{fname}",
                        "filename": fname,
                        "phase": phase,
                        "md_path": md_path,
                        "original_path": orig_path,
                        "media_type": get_media_type(orig_path) if orig_path else "unknown",
                        "verified": is_verified,
                    }
                )

    return jsonify(results)


@app.route("/api/content", methods=["GET"])
def get_content():
    path = request.args.get("path")
    if not path or not os.path.exists(path):
        return "File not found", 404

    # Security check to ensure it stays in workspace
    if WORKSPACE_ROOT not in os.path.abspath(path):
        return "Access denied", 403

    # If verified version exists, load it instead of the raw output
    subj = os.path.basename(os.path.dirname(path))
    fname = os.path.basename(path)
    verified_path = os.path.join(PROOFREADER_OUT_DIR, "04_final_verified", subj, fname)
    if os.path.exists(verified_path):
        path = verified_path

    with open(path, encoding="utf-8") as f:
        return f.read()


@app.route("/api/save", methods=["POST"])
def save_content():
    data = request.json
    path = data.get("path")
    content = data.get("content")

    if not path or not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    if WORKSPACE_ROOT not in os.path.abspath(path):
        return jsonify({"error": "Access denied"}), 403

    subj = os.path.basename(os.path.dirname(path))
    fname = os.path.basename(path)
    final_path = os.path.join(PROOFREADER_OUT_DIR, "04_final_verified", subj, fname)

    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    AtomicWriter.write_text(final_path, content)

    return jsonify({"status": "success"})


@app.route("/media/<path:filepath>")
def serve_media(filepath):
    # Flask <path:filepath> strips the leading slash, so we add it back if absolute
    full_path = (
        "/" + filepath
        if filepath.startswith("Users/") or filepath.startswith("Library/")
        else filepath
    )
    # Fallback to direct absolute path if missing slash
    if not full_path.startswith("/") and os.path.exists("/" + full_path):
        full_path = "/" + full_path

    if not os.path.exists(full_path):
        return "Media not found", 404

    if WORKSPACE_ROOT not in os.path.abspath(full_path):
        return "Access denied", 403

    return send_file(full_path)


HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Open Claw | Verification Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #1e1e1e; color: #d4d4d4; margin: 0; padding: 0; display: flex; height: 100vh; overflow: hidden; }

        /* Sidebar */
        .sidebar { width: 300px; background: #252526; border-right: 1px solid #333; display: flex; flex-direction: column; }
        .sidebar-header { padding: 15px; border-bottom: 1px solid #333; background: #2d2d30; }
        .sidebar-header h2 { margin: 0; font-size: 16px; color: #fff; }
        .file-list { flex: 1; overflow-y: auto; padding: 10px; }
        .subject-group { margin-bottom: 15px; }
        .subject-title { font-size: 12px; font-weight: bold; color: #9cdcfe; text-transform: uppercase; margin-bottom: 5px; padding-left: 5px; }
        .file-item { padding: 8px 10px; cursor: pointer; border-radius: 4px; font-size: 13px; color: #ccc; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: space-between; }
        .file-item:hover { background: #2a2d2e; }
        .file-item.active { background: #37373d; color: #fff; border-left: 3px solid #007acc; }
        .badge { font-size: 10px; padding: 2px 5px; border-radius: 3px; background: #4d4d4d; }
        .badge.p0 { background: #007acc; }
        .badge.p1 { background: #cca700; }
        .badge.p2 { background: #4CAF50; }
        .badge.verified { background: #009688; }

        /* Main Area */
        .main-area { flex: 1; display: flex; flex-direction: column; }
        .toolbar { height: 50px; background: #2d2d30; border-bottom: 1px solid #333; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
        .toolbar-title { font-size: 14px; color: #fff; font-weight: 500; }
        .btn { background: #007acc; color: white; border: none; padding: 6px 14px; border-radius: 3px; cursor: pointer; font-size: 13px; font-weight: 500; }
        .btn:hover { background: #005999; }
        .btn:disabled { background: #555; cursor: not-allowed; }
        .btn-success { background: #4CAF50; }

        /* Split View */
        .split-view { display: flex; flex: 1; min-height: 0; }
        .pane { flex: 1; display: flex; flex-direction: column; border-right: 1px solid #333; }
        .pane-header { padding: 10px; background: #1e1e1e; border-bottom: 1px solid #333; font-size: 12px; font-weight: bold; color: #888; text-transform: uppercase; text-align: center; display: flex; justify-content: space-between; align-items: center; }
        .pane-content { flex: 1; display: flex; flex-direction: column; background: #1e1e1e; overflow: hidden; }

        /* Toolbars inside Editor Pane */
        .action-toolbar { background: #333; padding: 10px; display: none; align-items: center; justify-content: space-between; border-bottom: 1px solid #444; }
        .action-toolbar.visible { display: flex; }
        .action-group { display: flex; align-items: center; gap: 10px; }
        .btn-sm { padding: 4px 10px; font-size: 12px; }
        .btn-outline { background: transparent; border: 1px solid #007acc; color: #007acc; }
        .btn-outline:hover { background: #007acc; color: #fff; }

        /* Embedded Media */
        iframe.pdf-viewer { width: 100%; height: 100%; border: none; }
        img.image-viewer { max-width: 100%; max-height: 100%; object-fit: contain; }
        .audio-container { width: 80%; margin: auto; text-align: center; }
        .empty-state { color: #666; font-size: 14px; margin: auto; }

        /* Editor */
        #editor { flex: 1; width: 100%; }

        /* Toast */
        .toast { position: fixed; bottom: 20px; right: 20px; background: #4CAF50; color: white; padding: 10px 20px; border-radius: 4px; display: none; font-size: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 1000; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>Verification Queue</h2>
        </div>
        <div class="file-list" id="fileList">
            <div class="empty-state" style="padding: 20px; text-align: center;">Loading...</div>
        </div>
    </div>

    <div class="main-area">
        <div class="toolbar">
            <div class="toolbar-title" id="currentTitle">Select a file to review</div>
            <div>
                <button class="btn" id="saveBtn" disabled onclick="saveCurrentFile()">Save & Mark Completed</button>
            </div>
        </div>

        <div class="split-view">
            <!-- Left: Ground Truth -->
            <div class="pane" id="leftPane">
                <div class="pane-header">Original File (Ground Truth)</div>
                <div class="pane-content" id="mediaViewer" style="justify-content: center;">
                    <div class="empty-state">No original file selected</div>
                </div>
            </div>

            <!-- Right: Markdown Editor -->
            <div class="pane">
                <div class="pane-header">
                    <span>Ollama Output (Markdown)</span>
                    <span style="font-size: 10px; color: #666; font-weight: normal;">(Hint: Select text + Ctrl+E for Smart Replace)</span>
                </div>
                <div class="pane-content">
                    <div class="action-toolbar" id="resolutionToolbar">
                        <div class="action-group">
                            <span id="resolutionStatus" style="font-size: 13px; color: #ffcc00; font-weight: bold;"></span>
                        </div>
                        <div class="action-group">
                            <button class="btn btn-sm" onclick="resolveChoice('original')">Keep Original</button>
                            <button class="btn btn-sm" onclick="resolveChoice('ai')">Keep AI</button>
                        </div>
                    </div>
                    <div class="action-toolbar" id="replaceToolbar">
                        <div class="action-group">
                            <span style="font-size: 13px; font-weight: bold; color: #4dc9f6;">Smart Replace</span>
                            <input type="text" id="replaceTarget" disabled style="background: #1e1e1e; border: 1px solid #444; color: #ccc; padding: 4px; border-radius: 3px;" />
                            <span style="font-size: 12px;">with</span>
                            <input type="text" id="replaceInput" placeholder="New text..." style="background: #1e1e1e; border: 1px solid #007acc; color: #fff; padding: 4px; border-radius: 3px; outline: none;" />
                            <span id="replaceCount" style="font-size: 12px; color: #888; margin-left: 10px;"></span>
                        </div>
                        <div class="action-group">
                            <button class="btn btn-sm" onclick="doSmartReplace()">Replace (Y)</button>
                            <button class="btn btn-sm btn-outline" onclick="skipSmartReplace()">Skip (N)</button>
                            <button class="btn btn-sm btn-outline" onclick="endSmartReplace()">Done (Esc)</button>
                        </div>
                    </div>
                    <div id="editor"></div>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">Saved Successfully!</div>

    <!-- RequireJS & Monaco Editor -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.41.0/min/vs/loader.min.js"></script>
    <script>
        let editorInstance = null;
        let currentFile = null;

        // Initialize Monaco
        require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.41.0/min/vs' } });
        require(['vs/editor/editor.main'], function() {
            editorInstance = monaco.editor.create(document.getElementById('editor'), {
                value: "Select a file from the sidebar to begin.",
                language: 'markdown',
                theme: 'vs-dark',
                wordWrap: 'on',
                minimap: { enabled: false },
                fontSize: 14,
                lineHeight: 1.6,
                readOnly: true,
                automaticLayout: true
            });

            // Keybindings for Smart Replace Mode
            editorInstance.onKeyDown(function (e) {
                if (document.getElementById('replaceToolbar').classList.contains('visible')) {
                    if (document.activeElement.tagName === 'INPUT') return; // Don't steal keystrokes if typing
                    if (e.keyCode === monaco.KeyCode.KeyY) { e.preventDefault(); doSmartReplace(); }
                    if (e.keyCode === monaco.KeyCode.KeyN) { e.preventDefault(); skipSmartReplace(); }
                    if (e.keyCode === monaco.KeyCode.Escape) { e.preventDefault(); endSmartReplace(); }
                }
            });

            // Load Files
            loadFiles();
        });

        // ----------------------------------------------------
        // ProofreadChoice Resolution Logic
        // ----------------------------------------------------
        let choices = [];
        let currentChoiceIndex = 0;

        function parseChoices() {
            let text = editorInstance.getValue();
            let regex = /<ProofreadChoice>\s*<Original>([\s\S]*?)<\/Original>\s*<AI>([\s\S]*?)<\/AI>\s*<\/ProofreadChoice>/g;
            choices = [];
            let match;
            while ((match = regex.exec(text)) !== null) {
                choices.push({
                    start: match.index,
                    end: match.index + match[0].length,
                    original: match[1].trim(),
                    ai: match[2].trim()
                });
            }

            const toolbar = document.getElementById('resolutionToolbar');
            if (choices.length > 0) {
                toolbar.classList.add('visible');
                currentChoiceIndex = 0;
                focusChoice();
            } else {
                toolbar.classList.remove('visible');
            }
        }

        function focusChoice() {
            if (currentChoiceIndex >= choices.length) {
                document.getElementById('resolutionToolbar').classList.remove('visible');
                return;
            }
            document.getElementById('resolutionStatus').innerText = `Decision ${currentChoiceIndex + 1} of ${choices.length}`;

            let choice = choices[currentChoiceIndex];
            let pos = editorInstance.getModel().getPositionAt(choice.start);
            let endPos = editorInstance.getModel().getPositionAt(choice.end);

            let range = new monaco.Range(pos.lineNumber, pos.column, endPos.lineNumber, endPos.column);
            editorInstance.setSelection(range);
            editorInstance.revealRangeInCenter(range);
        }

        function resolveChoice(type) {
            let choice = choices[currentChoiceIndex];
            let replacement = type === 'original' ? choice.original : choice.ai;

            let pos = editorInstance.getModel().getPositionAt(choice.start);
            let endPos = editorInstance.getModel().getPositionAt(choice.end);
            let range = new monaco.Range(pos.lineNumber, pos.column, endPos.lineNumber, endPos.column);

            editorInstance.executeEdits("resolution", [{
                range: range,
                text: replacement,
                forceMoveMarkers: true
            }]);

            // Re-parse since offsets changed
            parseChoices();
        }

        // ----------------------------------------------------
        // Smart Global Replace Logic
        // ----------------------------------------------------
        let replaceMatches = [];
        let currentReplaceIndex = 0;

        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'e') {
                e.preventDefault();
                startSmartReplace();
            }
        });

        // Enter key inside input
        document.getElementById('replaceInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.blur();
                editorInstance.focus();
                doSmartReplace();
            }
        });

        function startSmartReplace() {
            let selection = editorInstance.getSelection();
            if (selection.isEmpty()) {
                alert("Please select a word in the editor to replace.");
                return;
            }

            let model = editorInstance.getModel();
            let text = model.getValueInRange(selection);

            document.getElementById('replaceTarget').value = text;
            document.getElementById('replaceInput').value = '';
            document.getElementById('replaceToolbar').classList.add('visible');
            document.getElementById('replaceInput').focus();

            let matches = model.findMatches(text, false, false, false, null, true);
            matches.sort((a, b) => a.range.getStartPosition().isBefore(b.range.getStartPosition()) ? -1 : 1);

            currentReplaceIndex = 0;
            for (let i = 0; i < matches.length; i++) {
                if (matches[i].range.containsRange(selection)) {
                    currentReplaceIndex = i;
                    break;
                }
            }
            replaceMatches = matches;
            updateReplaceUI();
        }

        function updateReplaceUI() {
            if (currentReplaceIndex >= replaceMatches.length) {
                endSmartReplace();
                return;
            }
            document.getElementById('replaceCount').innerText = `Match ${currentReplaceIndex + 1} of ${replaceMatches.length}`;
            let match = replaceMatches[currentReplaceIndex];
            editorInstance.setSelection(match.range);
            editorInstance.revealRangeInCenter(match.range);
        }

        function doSmartReplace() {
            let newVal = document.getElementById('replaceInput').value;
            if (!newVal) { alert("Please enter replacement text first!"); return; }

            let match = replaceMatches[currentReplaceIndex];
            editorInstance.executeEdits("smart-replace", [{
                range: match.range,
                text: newVal,
                forceMoveMarkers: true
            }]);

            let target = document.getElementById('replaceTarget').value;
            replaceMatches = editorInstance.getModel().findMatches(target, false, false, false, null, true);
            replaceMatches.sort((a, b) => a.range.getStartPosition().isBefore(b.range.getStartPosition()) ? -1 : 1);

            updateReplaceUI();
        }

        function skipSmartReplace() {
            currentReplaceIndex++;
            updateReplaceUI();
        }

        function endSmartReplace() {
            document.getElementById('replaceToolbar').classList.remove('visible');
            editorInstance.focus();
        }

        // ----------------------------------------------------
        // File Loading & Saving
        // ----------------------------------------------------
        async function loadFiles() {
            try {
                const res = await fetch('/api/files');
                const data = await res.json();

                const fileListEl = document.getElementById('fileList');
                fileListEl.innerHTML = '';

                if (Object.keys(data).length === 0) {
                    fileListEl.innerHTML = '<div class="empty-state" style="text-align: center; padding: 20px;">No pending verifications found.</div>';
                    return;
                }

                for (const [subj, files] of Object.entries(data)) {
                    const group = document.createElement('div');
                    group.className = 'subject-group';
                    group.innerHTML = `<div class="subject-title">${subj}</div>`;

                    files.forEach(f => {
                        const item = document.createElement('div');
                        item.className = 'file-item';
                        // Use a safe hash or simple replace for IDs since btoa fails on Unicode
                        const safeId = f.id.replace(/[^a-zA-Z0-9]/g, '_');
                        item.id = `item-${safeId}`;

                        let badgeClass = 'badge';
                        let badgeText = 'N/A';
                        if (f.phase.includes('01')) { badgeClass += ' p0'; badgeText = 'Doc'; }
                        if (f.phase.includes('02')) { badgeClass += ' p1'; badgeText = 'Tx'; }
                        if (f.phase.includes('03')) { badgeClass += ' p2'; badgeText = 'Comp'; }

                        let verifiedBadge = f.verified ? `<span class="badge verified">✅ Verified</span>` : '';

                        item.innerHTML = `
                            <span title="${f.filename}">${f.filename}</span>
                            <div>${verifiedBadge} <span class="${badgeClass}">${badgeText}</span></div>
                        `;

                        item.onclick = () => selectFile(f, item.id);
                        group.appendChild(item);
                    });

                    fileListEl.appendChild(group);
                }
            } catch (e) {
                console.error('Failed to load files', e);
            }
        }

        async function selectFile(fileData, itemId) {
            // Update UI Selection
            document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
            document.getElementById(itemId).classList.add('active');

            document.getElementById('currentTitle').innerText = fileData.filename;
            document.getElementById('saveBtn').disabled = true;
            document.getElementById('saveBtn').innerText = 'Loading...';

            document.getElementById('resolutionToolbar').classList.remove('visible');
            document.getElementById('replaceToolbar').classList.remove('visible');

            // Render Media View
            const viewer = document.getElementById('mediaViewer');
            if (!fileData.original_path) {
                viewer.innerHTML = '<div class="empty-state">No original file found for this document.</div>';
            } else {
                const mediaUrl = '/media' + encodeURI(fileData.original_path);
                if (fileData.media_type === 'pdf') {
                    viewer.innerHTML = `<iframe class="pdf-viewer" src="${mediaUrl}#toolbar=0"></iframe>`;
                } else if (fileData.media_type === 'image') {
                    viewer.innerHTML = `<img class="image-viewer" src="${mediaUrl}" alt="Original File">`;
                } else if (fileData.media_type === 'audio') {
                    viewer.innerHTML = `
                        <div class="audio-container">
                            <h3 style="color:#fff; margin-bottom: 20px;">Source Audio</h3>
                            <audio controls style="width: 100%;"><source src="${mediaUrl}" type="audio/mp4"></audio>
                        </div>
                    `;
                } else {
                    viewer.innerHTML = '<div class="empty-state">Unsupported media type.</div>';
                }
            }

            // Render Editor
            editorInstance.updateOptions({ readOnly: true });
            editorInstance.setValue("Loading content...");

            try {
                const res = await fetch(`/api/content?path=${encodeURIComponent(fileData.md_path)}`);
                if (res.ok) {
                    const content = await res.text();
                    editorInstance.setValue(content);
                    editorInstance.updateOptions({ readOnly: false });
                    document.getElementById('saveBtn').disabled = false;
                    document.getElementById('saveBtn').innerText = 'Save & Mark Completed';
                    currentFile = fileData;

                    setTimeout(() => parseChoices(), 100);
                } else {
                    editorInstance.setValue("Failed to load content.");
                }
            } catch (e) {
                editorInstance.setValue("Error loading content: " + e);
            }
        }

        async function saveCurrentFile() {
            if (!currentFile || !editorInstance) return;

            const btn = document.getElementById('saveBtn');
            btn.disabled = true;
            btn.innerText = 'Saving...';

            try {
                const res = await fetch('/api/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        path: currentFile.md_path,
                        content: editorInstance.getValue()
                    })
                });

                if (res.ok) {
                    btn.classList.add('btn-success');
                    btn.innerText = 'Saved!';

                    currentFile.verified = true;
                    loadFiles(); // Refresh badges

                    // Show toast
                    const toast = document.getElementById('toast');
                    toast.style.display = 'block';
                    setTimeout(() => {
                        toast.style.display = 'none';
                        btn.classList.remove('btn-success');
                        btn.innerText = 'Save & Mark Completed';
                        btn.disabled = false;
                    }, 2000);
                } else {
                    throw new Error('Save failed');
                }
            } catch (e) {
                alert('Error saving: ' + e);
                btn.innerText = 'Save & Mark Completed';
                btn.disabled = false;
            }
        }

        // Listen for Cmd+S / Ctrl+S
        window.addEventListener('keydown', function(e) {
            if ((window.navigator.platform.match("Mac") ? e.metaKey : e.ctrlKey) && e.key === 's') {
                e.preventDefault();
                saveCurrentFile();
            }
        }, false);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Start the OpenClaw Verification Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Port to run the dashboard on")
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 OpenClaw Verification Dashboard")
    print(f"👉 Local URL: http://localhost:{args.port}")
    print("=" * 60)

    app.run(host="0.0.0.0", port=args.port, debug=False)
