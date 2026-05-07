"""
dashboard.py — Centralized Verification Dashboard for Proofreader
================================================================
Provides a persistent, non-blocking WebUI for Human-in-the-Loop verification.
It scans `data/proofreader/output/` for AI-corrected files, and pairs them
with the ground truth original files from `data/raw/`.
"""

import json
import os

from flask import Flask, jsonify, render_template_string, request, send_file

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
    phases = ["00_doc_proofread", "01_transcript_proofread", "02_doc_completeness"]

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

                results[subj].append(
                    {
                        "id": f"{phase}/{subj}/{fname}",
                        "filename": fname,
                        "phase": phase,
                        "md_path": md_path,
                        "original_path": orig_path,
                        "media_type": get_media_type(orig_path) if orig_path else "unknown",
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

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

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


HTML_TEMPLATE = """
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
        .pane-header { padding: 10px; background: #1e1e1e; border-bottom: 1px solid #333; font-size: 12px; font-weight: bold; color: #888; text-transform: uppercase; text-align: center; }
        .pane-content { flex: 1; display: flex; justify-content: center; align-items: center; background: #1e1e1e; overflow: hidden; }

        /* Embedded Media */
        iframe.pdf-viewer { width: 100%; height: 100%; border: none; }
        img.image-viewer { max-width: 100%; max-height: 100%; object-fit: contain; }
        .audio-container { width: 80%; text-align: center; }
        .empty-state { color: #666; font-size: 14px; }

        /* Editor */
        #editor { width: 100%; height: 100%; }

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
            <div class="pane">
                <div class="pane-header">Original File (Ground Truth)</div>
                <div class="pane-content" id="mediaViewer">
                    <div class="empty-state">No original file selected</div>
                </div>
            </div>

            <!-- Right: Markdown Editor -->
            <div class="pane">
                <div class="pane-header">Ollama Output (Markdown)</div>
                <div class="pane-content">
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

            // Load Files
            loadFiles();
        });

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
                        if (f.phase.includes('00')) { badgeClass += ' p0'; badgeText = 'Doc'; }
                        if (f.phase.includes('01')) { badgeClass += ' p1'; badgeText = 'Tx'; }
                        if (f.phase.includes('02')) { badgeClass += ' p2'; badgeText = 'Comp'; }

                        item.innerHTML = `
                            <span title="${f.filename}">${f.filename}</span>
                            <span class="${badgeClass}">${badgeText}</span>
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
