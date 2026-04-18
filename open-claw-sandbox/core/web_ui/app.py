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
from core.cli_runner import SkillRunner

# ── Flask app ─────────────────────────────────────────────────────────────────
app      = Flask(__name__)
exec_mgr = ExecutionManager()

# ── Workspace root (resolved once at startup) ─────────────────────────────────
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
)

# ── Path builders ─────────────────────────────────────────────────────────────
_pb_pdf   = PathBuilder(_workspace_root, "doc-parser")
_pb_voice = PathBuilder(_workspace_root, "audio-transcriber")

_pdf_dirs   = _pb_pdf.phase_dirs
_voice_dirs = _pb_voice.phase_dirs

# Canonical paths used in diff routes
PDF_INBOX     = _pdf_dirs.get("inbox",      os.path.join(_workspace_root, "data", "doc-parser",  "input"))
PDF_PROCESSED = _pdf_dirs.get("processed",  os.path.join(_workspace_root, "data", "doc-parser",  "output", "01_Processed"))
PDF_SYNTHESIS = _pdf_dirs.get("synthesis",  os.path.join(_workspace_root, "data", "doc-parser",  "output", "03_Synthesis"))

VOICE_P1     = _voice_dirs.get("p1", os.path.join(_workspace_root, "data", "audio-transcriber", "output", "01_transcript"))
VOICE_P2     = _voice_dirs.get("p2", os.path.join(_workspace_root, "data", "audio-transcriber", "output", "02_proofread"))
VOICE_P3     = _voice_dirs.get("p3", os.path.join(_workspace_root, "data", "audio-transcriber", "output", "03_merged"))
VOICE_STATE  = _pb_voice.state_file

# ── Diff phase map ─────────────────────────────────────────────────────────────
# Maps (skill, phase_pair_key) → (from_dir, to_dir, label_from, label_to)
DIFF_PHASE_MAP: dict[str, dict[str, tuple[str, str, str, str]]] = {
    "audio-transcriber": {
        "p1_vs_p2": (VOICE_P1, VOICE_P2, "P1 Raw Transcript", "P2 AI Proofread"),
        "p2_vs_p3": (VOICE_P2, VOICE_P3, "P2 AI Proofread",   "P3 Merged Refined"),
    },
    "doc-parser": {
        "raw_vs_final": (PDF_PROCESSED, PDF_SYNTHESIS, "Raw Extracted", "Synthesis Notes"),
    },
}

# ── Script paths ───────────────────────────────────────────────────────────────
_PDF_SCRIPT   = os.path.join(_workspace_root, "skills", "doc-parser",         "scripts", "run_all.py")
_VOICE_SCRIPT = os.path.join(_workspace_root, "skills", "audio-transcriber",  "scripts", "run_all.py")

# ── Skill alias normaliser ─────────────────────────────────────────────────────
_SKILL_ALIASES: dict[str, str] = {
    "voice": "audio-transcriber",
    "pdf":   "doc-parser",
    "audio-transcriber": "audio-transcriber",
    "doc-parser":        "doc-parser",
    "smart-highlighter": "smart-highlighter",
    "note-generator":    "note-generator",
}

def _normalise_skill(raw: str) -> str | None:
    return _SKILL_ALIASES.get(raw.strip().lower())


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


@app.route("/api/subjects", methods=["GET"])
def api_subjects():
    """Return list of subject folders for a given skill."""
    skill = request.args.get("skill", "voice")
    if skill == "pdf":
        input_dir = os.path.join(_workspace_root, "data", "doc-parser", "input")
    else:
        input_dir = os.path.join(_workspace_root, "data", "audio-transcriber", "input")
        
    if not os.path.isdir(input_dir):
        return jsonify({"subjects": []})
    
    subjects = sorted([d for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d)) and not d.startswith(".")])
    # Handle the fact that root-level files in pdf queue represent the "Default" subject
    if skill == "pdf":
        has_root_pdfs = any(f.lower().endswith(".pdf") for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)))
        if has_root_pdfs and "Default" not in subjects:
            subjects.insert(0, "Default")
            
    return jsonify({"subjects": subjects})

@app.route("/api/files", methods=["GET"])
def api_files():
    """Return list of files for a specific subject."""
    skill = request.args.get("skill", "voice")
    subject = request.args.get("subject", "")
    
    if skill == "pdf":
        input_dir = os.path.join(_workspace_root, "data", "doc-parser", "input")
        if subject and subject != "Default":
            input_dir = os.path.join(input_dir, subject)
        target_ext = ".pdf"
    else:
        input_dir = os.path.join(_workspace_root, "data", "audio-transcriber", "input")
        if subject:
            input_dir = os.path.join(input_dir, subject)
        target_ext = ".m4a"
        
    if not os.path.isdir(input_dir):
        return jsonify({"files": []})
        
    files = sorted([f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)) and f.lower().endswith(target_ext)])
    return jsonify({"files": files})


@app.route("/api/start", methods=["POST"])
def api_start():
    """
    Launch a skill pipeline subprocess.

    Request body (JSON):
        skill   : "pdf" | "voice"   (required)
        subject : str               (optional — restrict to one subject folder)
        force   : bool              (optional — overwrite completed phases)
        resume  : bool              (optional — audio-transcriber: auto-answer resume prompt with C)
    """
    data    = request.get_json(force=True) or {}
    skill  = _normalise_skill(data.get("skill", ""))
    subject = data.get("subject", "").strip()
    file    = data.get("file", "").strip()
    single  = bool(data.get("single", False))
    force   = bool(data.get("force", False))
    resume  = bool(data.get("resume", False))

    if skill == "audio-transcriber":
        cmd = SkillRunner.run_audio_transcriber(subject=subject, file=file, single=single, force=force, resume=resume)
        ok = exec_mgr.enqueue_task("Audio Transcriber Pipeline", cmd, cwd=_workspace_root)

    elif skill == "doc-parser":
        cmd = SkillRunner.run_doc_parser(subject=subject, file=file, single=single, force=force, resume=resume)
        ok = exec_mgr.enqueue_task("Doc Parser Pipeline", cmd, cwd=_workspace_root)

    else:
        return jsonify({"success": False, "error": f"Invalid skill '{skill}'. Use 'audio-transcriber' or 'doc-parser'."}), 400

    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Another task with the same name is already running or queued."}), 409


@app.route("/api/highlight", methods=["POST"])
def api_highlight():
    """
    Re-run smart-highlighter on an existing Phase output file.

    Request body (JSON):
        skill   : "audio-transcriber" | "doc-parser"  (required)
        subject : str  (required)
        file_id : str  (required — stem for voice, pdf_id folder for doc-parser)
    """
    data    = request.get_json(force=True) or {}
    skill   = _normalise_skill(data.get("skill", ""))
    subject = data.get("subject", "").strip()
    file_id = data.get("file_id", "").strip()

    if skill not in ("audio-transcriber", "doc-parser") or not subject or not file_id:
        return jsonify({"success": False, "error": "Missing or invalid skill / subject / file_id."}), 400

    try:
        input_path, output_path = SkillRunner.resolve_highlight_paths(skill, subject, file_id)
    except FileNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    cmd = SkillRunner.run_smart_highlighter(input_file=input_path, output_file=output_path, subject=subject)
    task_name = f"Smart Highlighter [{skill}/{subject}/{file_id}]"
    ok = exec_mgr.enqueue_task(task_name, cmd, cwd=_workspace_root)

    if ok:
        return jsonify({"success": True, "input": input_path, "output": output_path})
    return jsonify({"success": False, "error": "Same task already queued."}), 409


@app.route("/api/synthesize", methods=["POST"])
def api_synthesize():
    """
    Re-run note-generator on an existing highlighted Phase output file.

    Request body (JSON):
        skill   : "audio-transcriber" | "doc-parser"  (required)
        subject : str  (required)
        file_id : str  (required)
    """
    data    = request.get_json(force=True) or {}
    skill   = _normalise_skill(data.get("skill", ""))
    subject = data.get("subject", "").strip()
    file_id = data.get("file_id", "").strip()

    if skill not in ("audio-transcriber", "doc-parser") or not subject or not file_id:
        return jsonify({"success": False, "error": "Missing or invalid skill / subject / file_id."}), 400

    try:
        input_path, output_path = SkillRunner.resolve_synthesize_paths(skill, subject, file_id)
    except FileNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    cmd = SkillRunner.run_note_generator(input_file=input_path, output_file=output_path, subject=subject, label=file_id)
    task_name = f"Note Generator [{skill}/{subject}/{file_id}]"
    ok = exec_mgr.enqueue_task(task_name, cmd, cwd=_workspace_root)

    if ok:
        return jsonify({"success": True, "input": input_path, "output": output_path})
    return jsonify({"success": False, "error": "Same task already queued."}), 409


@app.route("/api/rerun/files", methods=["GET"])
def api_rerun_files():
    """
    Return file IDs available for Re-run (highlight or synthesize).

    Query params:
        skill   : "audio-transcriber" | "doc-parser"  (required)
        subject : str                                  (required)
        mode    : "highlight" | "synthesize"           (required)

    For highlight mode  → scans the Phase 3 (merged) or Phase 1 (processed) output dir
    For synthesize mode → scans the Phase 4 (highlighted) or Phase 2 (highlighted) output dir
    """
    skill   = _normalise_skill(request.args.get("skill", ""))
    subject = request.args.get("subject", "").strip()
    mode    = request.args.get("mode", "highlight").strip()

    if skill not in ("audio-transcriber", "doc-parser") or not subject:
        return jsonify({"files": [], "error": "Missing skill or subject"}), 400

    base = os.path.join(_workspace_root, "data")

    if skill == "audio-transcriber":
        scan_dir = os.path.join(
            base, "audio-transcriber", "output",
            "03_merged" if mode == "highlight" else "04_highlighted",
            subject,
        )
        # Files are <stem>.md — return stems as file_id
        if not os.path.isdir(scan_dir):
            return jsonify({"files": []})
        files = sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(scan_dir)
            if f.endswith(".md") and not f.startswith(".")
        )
    else:  # doc-parser
        # For doc-parser the file_id is a sub-folder name (pdf_id)
        scan_dir = os.path.join(
            base, "doc-parser", "output",
            "01_processed" if mode == "highlight" else "02_highlighted",
            subject,
        )
        if not os.path.isdir(scan_dir):
            return jsonify({"files": []})
        files = sorted(
            d for d in os.listdir(scan_dir)
            if os.path.isdir(os.path.join(scan_dir, d)) and not d.startswith(".")
        )

    return jsonify({"files": files, "skill": skill, "subject": subject, "mode": mode})


@app.route("/api/rerun/subjects", methods=["GET"])
def api_rerun_subjects():
    """
    Return subjects that have output files for a given skill + mode.
    mode: "highlight" | "synthesize"
    """
    skill = _normalise_skill(request.args.get("skill", ""))
    mode  = request.args.get("mode", "highlight").strip()

    if skill not in ("audio-transcriber", "doc-parser"):
        return jsonify({"subjects": []}), 400

    base = os.path.join(_workspace_root, "data")
    if skill == "audio-transcriber":
        scan_dir = os.path.join(
            base, "audio-transcriber", "output",
            "03_merged" if mode == "highlight" else "04_highlighted",
        )
    else:
        scan_dir = os.path.join(
            base, "doc-parser", "output",
            "01_processed" if mode == "highlight" else "02_highlighted",
        )

    subjects = _list_subdirs(scan_dir)
    return jsonify({"subjects": subjects})


@app.route("/api/queue", methods=["GET"])
def api_queue():
    """Return the current Job Queue status."""
    return jsonify(exec_mgr.get_queue_status())



@app.route("/api/status/skills", methods=["GET"])
def api_status_skills():
    """Return a summary of each skill's output file counts."""
    def _count_md(directory: str) -> int:
        if not os.path.isdir(directory):
            return 0
        return sum(1 for _, _, files in os.walk(directory) for f in files if f.endswith(".md"))

    base = os.path.join(_workspace_root, "data")
    return jsonify({
        "audio-transcriber": {
            "transcripts":   _count_md(os.path.join(base, "audio-transcriber", "output", "01_transcript")),
            "highlighted":   _count_md(os.path.join(base, "audio-transcriber", "output", "04_highlighted")),
            "synthesized":   _count_md(os.path.join(base, "audio-transcriber", "output", "05_notion_synthesis")),
        },
        "doc-parser": {
            "processed":  _count_md(os.path.join(base, "doc-parser", "output", "01_processed")),
            "highlighted": _count_md(os.path.join(base, "doc-parser", "output", "02_highlighted")),
            "synthesized": _count_md(os.path.join(base, "doc-parser", "output", "03_synthesis")),
        },
    })


@app.route("/api/stop", methods=["POST"])
def api_stop():
    exec_mgr.terminate_task()
    return jsonify({"success": True})

@app.route("/api/pause", methods=["POST"])
def api_pause():
    exec_mgr.pause_task()
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

    if skill == "audio-transcriber":
        from_stems = {os.path.splitext(f)[0] for f in os.listdir(from_dir) if f.endswith(".md")} \
                     if os.path.isdir(from_dir) else set()
        to_stems   = {os.path.splitext(f)[0] for f in os.listdir(to_dir)   if f.endswith(".md")} \
                     if os.path.isdir(to_dir)   else set()
        common = sorted(from_stems & to_stems)
        return jsonify({"files": [{"id": s, "label": s + ".md"} for s in common]})

    if skill == "doc-parser" and phase_pair == "raw_vs_final":
        processed_subj = os.path.join(PDF_PROCESSED, subject)
        final_subj     = os.path.join(PDF_SYNTHESIS, subject)
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

    if skill == "audio-transcriber":
        text_a = _read_text(os.path.join(cfg[0], subject, file_id + ".md"))
        text_b = _read_text(os.path.join(cfg[1], subject, file_id + ".md"))

    elif skill == "doc-parser" and phase_pair == "raw_vs_final":
        text_a = _read_text(os.path.join(PDF_PROCESSED, subject, file_id, "raw_extracted.md"))
        text_b = _read_text(os.path.join(PDF_SYNTHESIS, subject, file_id, "content.md"))

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
