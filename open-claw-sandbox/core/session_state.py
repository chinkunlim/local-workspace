# -*- coding: utf-8 -*-
"""
core/session_state.py — Unified Pipeline Control State Machine
==============================================================
Records 6 canonical session control states for every pipeline run.
Used by PipelineBase to persist state to state/session.json so that
any human or agent can inspect why a previous session stopped.

States:
    RUNNING       — actively processing items
    PAUSED        — gracefully paused (checkpoint saved, resumable)
    STOPPED       — stopped cleanly by user, no checkpoint
    FORCE_STOPPED — killed by second Ctrl+C or hardware emergency
    COMPLETED     — all queue items processed successfully
    FAILED        — unrecoverable crash / exception

Usage (via PipelineBase — do not call directly in phase scripts):
    from core.session_state import SessionState, write_session_state
    write_session_state(state_dir, SessionState.PAUSED, context={"phase": "p2"})
"""

from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from .atomic_writer import AtomicWriter


# ---------------------------------------------------------------------------
# State Enum
# ---------------------------------------------------------------------------

class SessionState(Enum):
    """Canonical pipeline control states.

    Transitions:
        RUNNING → PAUSED | STOPPED | FORCE_STOPPED | COMPLETED | FAILED
        PAUSED  → RUNNING  (on --resume)
    """
    RUNNING       = "running"
    PAUSED        = "paused"
    STOPPED       = "stopped"
    FORCE_STOPPED = "force_stopped"
    COMPLETED     = "completed"
    FAILED        = "failed"


# ---------------------------------------------------------------------------
# Persistence helper
# ---------------------------------------------------------------------------

SESSION_FILE = "session.json"


def write_session_state(
    state_dir: str,
    state: SessionState,
    *,
    context: Optional[Dict[str, Any]] = None,
    skill_name: str = "",
) -> None:
    """Atomically persist the current session state to state/session.json.

    Args:
        state_dir:  Absolute path to the skill's canonical ``state/`` directory.
        state:      One of the :class:`SessionState` enum values.
        context:    Optional dict of extra metadata (e.g. current phase, file).
        skill_name: Skill identifier for auditing (e.g. ``"pdf-knowledge"``).
    """
    os.makedirs(state_dir, exist_ok=True)
    payload: Dict[str, Any] = {
        "skill": skill_name,
        "state": state.value,
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if context:
        payload["context"] = context

    session_path = os.path.join(state_dir, SESSION_FILE)
    AtomicWriter.write_json(session_path, payload)


def read_session_state(state_dir: str) -> Optional[Dict[str, Any]]:
    """Read the last recorded session state, or None if not found.

    Args:
        state_dir: Absolute path to the skill's canonical ``state/`` directory.

    Returns:
        Parsed session.json dict, or None if the file does not exist.
    """
    import json
    session_path = os.path.join(state_dir, SESSION_FILE)
    if not os.path.exists(session_path):
        return None
    try:
        with open(session_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None
