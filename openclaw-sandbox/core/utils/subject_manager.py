"""
core/subject_manager.py
=======================
Generalized CLI interaction and subject hierarchy helpers.
This core module replaces the skill-specific subject_managers to ensure DRY
principles across the entire Open Claw architecture.
"""

from __future__ import annotations

import os

from rich import print


def ask_reprocess(subject: str, item_id: str, phase_label: str) -> bool:
    """
    Interactively ask the user whether to overwrite a completed phase output.

    Args:
        subject:     The subject folder name (e.g. "AI_Papers" or "助人歷程").
        item_id:     The specific item identifier (e.g. "paper" or "L02").
        phase_label: Human-readable phase label (e.g. "P1a" or "P2").

    Returns:
        True  → user confirmed overwrite.
        False → user declined; caller should skip.
    """
    display = f"[{subject}] {item_id} ({phase_label})"
    print(f"\n❓ {display} 已完成。")
    choice = input("   是否重新處理並覆寫？(y/N): ").strip().lower()
    return choice == "y"


def should_process_task(
    task: dict,
    current_phase_key: str,
    previous_phase_key: str | None = None,
    force: bool = False,
) -> bool:
    """
    Decide whether a task should be processed for *current_phase_key*.

    Rules:
    1. If the previous phase is not yet complete (≠ ✅), skip.
    2. If the current phase is already complete AND force=False, ask the user.
    3. If force=True, always process.

    Args:
        task:               Task dict with keys "subject", "filename", "status".
        current_phase_key:  Phase key to check (e.g. "p1b" or "p2").
        previous_phase_key: Phase key that must already be ✅ (optional).
        force:              Skip interactive prompt and always reprocess.

    Returns:
        True if the task should be (re-)processed, False to skip.
    """
    status = task.get("status", {})

    if previous_phase_key and status.get(previous_phase_key) != "✅":
        return False

    if status.get(current_phase_key) == "✅":
        if force:
            return True

        item_id = os.path.splitext(task.get("filename", "unknown"))[0]
        return ask_reprocess(task.get("subject", "unknown"), item_id, current_phase_key.upper())

    return True


def get_target_path(base_dir: str, subject: str, filename: str, target_suffix: str = ".md") -> str:
    """
    Construct the canonical output path for a given subject + source filename.

    If target_suffix has no extension dot but acts as a filename (like "raw_extracted.md" in doc_parser),
    this generates `base_dir/subject/item_id/target_suffix`.
    If target_suffix acts as an extension (like ".md" in audio_transcriber),
    this generates `base_dir/subject/item_id<target_suffix>`.

    Args:
        base_dir: Phase output directory.
        subject:  Subject folder name.
        filename: Source filename (basename).
        target_suffix: Goal filename or extension.

    Returns:
        Absolute path
    """
    item_id = os.path.splitext(filename)[0]

    # Heuristic: if it starts with a dot, it's a file extension replacement
    if target_suffix.startswith("."):
        return os.path.join(base_dir, subject, f"{item_id}{target_suffix}")
    else:
        # It's a full subpath/filename creation
        return os.path.join(base_dir, subject, item_id, target_suffix)
