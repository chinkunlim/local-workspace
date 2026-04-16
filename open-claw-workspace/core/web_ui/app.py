# -*- coding: utf-8 -*-
"""
core/web_ui/app.py — Open Claw Central Dashboard API
======================================================
Flask backend for the unified web dashboard.

Routes:
  GET  /                         → Serves the SPA (index.html)
  GET  /api/status               → Aggregated system / pipeline status
  GET  /api/logs?cursor=N        → Streaming log tail
  POST /api/start                → Launch a skill pipeline
  POST /api/stop                 → Terminate the running task
  GET  /api/diff/phases          → Available diff pairs for a skill
  GET  /api/diff/subjects        → Subjects present in a phase pair
  GET  /api/diff/files           → Files present in both sides of a pair
  GET  /api/diff                 → Raw text content for client-side diff
"""

from __future__ import annotations

import os
import sys
import json
from flask import Flask, jsonify, request, render_template

# ── Bootstrap (single-line path fix — no hand-rolled sys.path blocks) ────────
# Workspace Root Resolver
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.web_ui.execution_manager import ExecutionManager
from core.path_builder import PathBuilder

# ── Flask app ─────────────────────────────────────────────────────────────────
app      = Flask(__name__)
exec_mgr = ExecutionManager()

# ── Workspace root (resolved once at startup) ─────────────────────────────────
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
)

# ── Path builders ─────────────────────────────────────────────────────────────
_pb_pdf   = PathBuilder(_workspace_root, "pdf-knowledge")
_pb_voice = PathBuilder(_workspace_root, "voice-memo")

_pdf_dirs   = _pb_pdf.phase_dirs
_voice_dirs = _pb_voice.phase_dirs

# Canonical paths used in diff routes
PDF_INBOX     = _pdf_dirs.get("inbox",      os.path.join(_workspace_root, "data", "pdf-knowledge",  "input", "01_Inbox"))
PDF_PROCESSED = _pdf_dirs.get("processed",  os.path.join(_workspace_root, "data", "pdf-knowledge",  "output", "02_Processed"))
PDF_FINAL     = _pdf_dirs.get("final",      os.path.join(_workspace_root, "data", "pdf-knowledge",  "output", "05_Final_Knowledge"))

VOICE_P1     = _voice_dirs.get("p1", os.path.join(_workspace_root, "data", "voice-memo", "output", "01_transcript"))
VOICE_P2     = _voice_dirs.get("p2", os.path.join(_workspace_root, "data", "voice-memo", "output", "02_proofread"))
VOICE_P3     = _voice_dirs.get("p3", os.path.join(_workspace_root, "data", "voice-memo", "output", "03_merged"))
VOICE_STATE  = _pb_voice.state_file

# ── Diff phase map ─────────────────────────────────────────────────────────────
# Maps (skill, phase_pair_key) → (from_dir, to_dir, label_from, label_to)
DIFF_PHASE_MAP: dict[str, dict[str, tuple[str, str, str, str]]] = {
    "voice-memo": {
        "p1_vs_p2": (VOICE_P1, VOICE_P2, "P1 Raw Transcript", "P2 AI Proofread"),
        "p2_vs_p3": (VOICE_P2, VOICE_P3, "P2 AI Proofread",   "P3 Merged Refined"),
    },
    "pdf-knowledge": {
        "raw_vs_final": (PDF_PROCESSED, PDF_FINAL, "Raw Extracted", "Final Knowledge"),
    },
}

# ── Script paths ───────────────────────────────────────────────────────────────
_PDF_SCRIPT   = os.path.join(_workspace_root, "skills", "pdf-knowledge", "scripts", "run_all.py")
_VOICE_SCRIPT = os.path.join(_workspace_root, "skills", "voice-memo",   "scripts", "run_all.py")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _count_pdfs_in_dir(directory: str) -> int:
    """Recursively count PDF files in *directory*."""
    if not os.path.isdir(directory):
        return 0
    total = 0
    for _, _, files in os.walk(directory):
        total += sum(1 for f in files if f.lower().endswith(".pdf"))
    return total


def _count_subject_dirs(directory: str) -> int:
    """Count second-level subdirectories in *directory* (subject → pdf_id)."""
    if not os.path.isdir(directory):
        return 0
    return sum(
        len([dd for dd in os.listdir(os.path.join(directory, s))
             if os.path.isdir(os.path.join(directory, s, dd))])
        for s in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, s))
    )


def _list_subdirs(directory: str) -> list[str]:
    """Return sorted list of immediate subdirectory names."""
    if not os.path.isdir(directory):
        return []
    return sorted(d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d)))


def _read_text(path: str) -> str | None:
    """Read a UTF-8 text file; return None if it does not exist."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _get_pdf_status() -> dict:
    return {
        "inbox":     _count_pdfs_in_dir(PDF_INBOX),
        "completed": _count_subject_dirs(PDF_PROCESSED),
    }


def _get_voice_status() -> dict:
    counts: dict[str, int] = {"p1": 0, "p2": 0, "p3": 0, "p4": 0, "p5": 0}
    if not os.path.exists(VOICE_STATE):
        return counts
    try:
        with open(VOICE_STATE, "r", encoding="utf-8") as fh:
            state: dict = json.load(fh)
    except Exception:
        return counts
    for subj_data in state.values():
        if not isinstance(subj_data, dict):
            continue
        for record in subj_data.values():
            if not isinstance(record, dict):
                continue
            for phase_key in counts:
                if record.get(phase_key) == "✅":
                    counts[phase_key] += 1
    return counts


# ─────────────────────────────────────────────────────────────────────────────
# Routes — Core
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "system": exec_mgr.get_status(),
        "pdf":    _get_pdf_status(),
        "voice":  _get_voice_status(),
    })


@app.route("/api/logs", methods=["GET"])
def api_logs():
    cursor = int(request.args.get("cursor", 0))
    return jsonify(exec_mgr.get_logs(cursor))


@app.route("/api/start", methods=["POST"])
def api_start():
    """
    Launch a skill pipeline subprocess.

    Request body (JSON):
        skill   : "pdf" | "voice"   (required)
        subject : str               (optional — restrict to one subject folder)
        force   : bool              (optional — overwrite completed phases)
    """
    data    = request.get_json(force=True) or {}
    skill   = data.get("skill", "")
    subject = data.get("subject", "").strip()
    force   = bool(data.get("force", False))

    if skill == "pdf":
        cmd = ["python3", _PDF_SCRIPT, "--process-all"]
        if subject:
            cmd += ["--subject", subject]
        ok = exec_mgr.start_task("PDF Queue Manager", cmd, cwd=_workspace_root)

    elif skill == "voice":
        cmd = ["python3", _VOICE_SCRIPT]
        if subject:
            cmd += ["--subject", subject]
        if force:
            cmd += ["--force"]
        ok = exec_mgr.start_task("Voice Memo Pipeline", cmd, cwd=_workspace_root)

    else:
        return jsonify({"success": False, "error": "Invalid skill. Use 'pdf' or 'voice'."}), 400

    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Another task is already running."}), 409


@app.route("/api/stop", methods=["POST"])
def api_stop():
    exec_mgr.terminate_task()
    return jsonify({"success": True})


# ─────────────────────────────────────────────────────────────────────────────
# Routes — Diff / Review Board
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/diff/phases", methods=["GET"])
def api_diff_phases():
    """Return available phase-comparison pairs for a skill."""
    skill = request.args.get("skill", "")
    if skill not in DIFF_PHASE_MAP:
        return jsonify({"phases": []})
    phases = [
        {"key": k, "label": f"{v[2]}  →  {v[3]}"}
        for k, v in DIFF_PHASE_MAP[skill].items()
    ]
    return jsonify({"phases": phases})


@app.route("/api/diff/subjects", methods=["GET"])
def api_diff_subjects():
    """Return subject folders available in the 'from' directory of a phase pair."""
    skill      = request.args.get("skill", "")
    phase_pair = request.args.get("phase", "")
    if skill not in DIFF_PHASE_MAP or phase_pair not in DIFF_PHASE_MAP[skill]:
        return jsonify({"subjects": []})
    from_dir = DIFF_PHASE_MAP[skill][phase_pair][0]
    return jsonify({"subjects": _list_subdirs(from_dir)})


@app.route("/api/diff/files", methods=["GET"])
def api_diff_files():
    """List files present in BOTH sides of a phase pair for the given subject."""
    skill      = request.args.get("skill", "")
    phase_pair = request.args.get("phase", "")
    subject    = request.args.get("subject", "")

    if not subject or skill not in DIFF_PHASE_MAP or phase_pair not in DIFF_PHASE_MAP[skill]:
        return jsonify({"files": []})

    cfg      = DIFF_PHASE_MAP[skill][phase_pair]
    from_dir = os.path.join(cfg[0], subject)
    to_dir   = os.path.join(cfg[1], subject)

    if skill == "voice-memo":
        from_stems = {os.path.splitext(f)[0] for f in os.listdir(from_dir) if f.endswith(".md")} \
                     if os.path.isdir(from_dir) else set()
        to_stems   = {os.path.splitext(f)[0] for f in os.listdir(to_dir)   if f.endswith(".md")} \
                     if os.path.isdir(to_dir)   else set()
        common = sorted(from_stems & to_stems)
        return jsonify({"files": [{"id": s, "label": s + ".md"} for s in common]})

    if skill == "pdf-knowledge" and phase_pair == "raw_vs_final":
        processed_subj = os.path.join(PDF_PROCESSED, subject)
        final_subj     = os.path.join(PDF_FINAL,     subject)
        p_ids = {d for d in os.listdir(processed_subj) if os.path.isdir(os.path.join(processed_subj, d))} \
                if os.path.isdir(processed_subj) else set()
        f_ids = {d for d in os.listdir(final_subj)     if os.path.isdir(os.path.join(final_subj,     d))} \
                if os.path.isdir(final_subj)     else set()
        common = sorted(p_ids & f_ids)
        return jsonify({"files": [{"id": pdf_id, "label": pdf_id} for pdf_id in common]})

    return jsonify({"files": []})


@app.route("/api/diff", methods=["GET"])
def api_diff():
    """Return raw text of both source files for client-side diff rendering."""
    skill      = request.args.get("skill", "")
    phase_pair = request.args.get("phase", "")
    subject    = request.args.get("subject", "")
    file_id    = request.args.get("file", "")

    if not all([skill, phase_pair, subject, file_id]):
        return jsonify({"error": "Missing one or more required parameters: skill, phase, subject, file"}), 400

    if skill not in DIFF_PHASE_MAP or phase_pair not in DIFF_PHASE_MAP[skill]:
        return jsonify({"error": f"Unknown skill/phase combination: {skill} / {phase_pair}"}), 400

    cfg     = DIFF_PHASE_MAP[skill][phase_pair]
    label_a = cfg[2]
    label_b = cfg[3]

    if skill == "voice-memo":
        text_a = _read_text(os.path.join(cfg[0], subject, file_id + ".md"))
        text_b = _read_text(os.path.join(cfg[1], subject, file_id + ".md"))

    elif skill == "pdf-knowledge" and phase_pair == "raw_vs_final":
        text_a = _read_text(os.path.join(PDF_PROCESSED, subject, file_id, "raw_extracted.md"))
        text_b = _read_text(os.path.join(PDF_FINAL,     subject, file_id, "content.md"))

    else:
        text_a = text_b = None

    missing = []
    if text_a is None:
        missing.append(label_a)
    if text_b is None:
        missing.append(label_b)
    if missing:
        return jsonify({"error": f"File(s) not found: {', '.join(missing)}"}), 404

    return jsonify({
        "label_a": label_a,
        "label_b": label_b,
        "text_a":  text_a,
        "text_b":  text_b,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    host = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.environ.get("DASHBOARD_PORT", "5001"))
    print(f"🌐 Open Claw Dashboard → http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
