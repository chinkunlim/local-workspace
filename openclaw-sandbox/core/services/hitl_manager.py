"""
core/hitl_manager.py — Human-in-the-Loop (HITL) Intervention Protocol (#14)
=============================================================================
Strategic scaffold for pausing pipeline execution and requesting human
confirmation via Telegram or CLI when confidence scores are low or when
unrecognised terminology is encountered.

CURRENT STATUS: Scaffold / Interface Definition
  The HITLEvent dataclass and serialisation protocol are fully defined.
  The actual Telegram emission and resume-from-checkpoint wiring is
  deferred to P3 implementation once telegram_bot.py integration is finalised.

Lifecycle:
  1. A Phase script creates a HITLEvent and calls HITLManager.trigger().
  2. HITLManager serialises pipeline state via session_state.py and emits
     an event to the Telegram bot.
  3. User replies via Telegram (approve / correct / skip).
  4. HITLManager deserialises the state and resumes the pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, Optional
import uuid

from core.utils.log_manager import build_logger

logger = build_logger(__name__, console=True)

from core.utils.atomic_writer import AtomicWriter

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class HITLPendingInterrupt(Exception):  # noqa: N818
    """Raised when a HITL event is triggered, pausing pipeline execution."""

    def __init__(self, trace_id: str, message: str):
        super().__init__(message)
        self.trace_id = trace_id


# ---------------------------------------------------------------------------
# Data Contracts

# ---------------------------------------------------------------------------


@dataclass
class HITLEvent:
    """Describes an intervention request emitted mid-pipeline."""

    phase: str  # e.g. "p2_proofread", "p01c_ocr_gate"
    reason: str  # Human-readable explanation of why HITL was triggered
    payload: Dict[str, Any]  # Contextual data (e.g., the ambiguous text chunk)
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_name: str = "unknown"
    subject: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolution: Optional[str] = None  # Filled in after user responds


# ---------------------------------------------------------------------------
# HITL Manager
# ---------------------------------------------------------------------------


class HITLManager:
    """Manages Human-in-the-Loop intervention events.

    Serialises pipeline state on trigger and provides a resume interface
    for the pipeline to continue after human confirmation.
    """

    PENDING_DIR_NAME = "state/hitl_pending"

    def __init__(self, base_dir: str, telegram_bot=None):
        """
        Args:
            base_dir:     The skill's data base directory (for state persistence).
            telegram_bot: Optional TelegramBot instance for async notification.
        """
        self.base_dir = base_dir
        self.telegram_bot = telegram_bot
        self.pending_dir = os.path.join(base_dir, self.PENDING_DIR_NAME)
        os.makedirs(self.pending_dir, exist_ok=True)

    def trigger(self, event: HITLEvent, session_state_data: Optional[Dict] = None) -> str:
        """Trigger a HITL intervention.

        Serialises the event to disk and (if configured) notifies the user
        via Telegram. The pipeline should suspend after calling this.

        Args:
            event:              The HITLEvent describing the intervention.
            session_state_data: Optional pipeline state snapshot for resumption.

        Returns:
            Path to the persisted event file (used to poll for resolution).
        """
        event_path = os.path.join(self.pending_dir, f"{event.trace_id}.json")
        payload = asdict(event)
        if session_state_data:
            payload["_session_snapshot"] = session_state_data

        AtomicWriter.write_json(event_path, payload)

        logger.info(
            f"⏸️  [HITL] 已暫停 — Phase: {event.phase} | 原因: {event.reason}\n"
            f"   事件 ID: {event.trace_id}\n"
            f"   等待確認：{event_path}"
        )

        # TODO (P3) #14: emit to telegram_bot
        if self.telegram_bot:
            msg = (
                f"⚠️ *OpenClaw HITL 介入*\n"
                f"Phase: `{event.phase}`\n"
                f"原因: {event.reason}\n"
                f"Trace ID: `{event.trace_id}`\n"
                f"請回覆 `/hitl approve {event.trace_id}` 或 `/hitl skip {event.trace_id}`"
            )
            try:
                self.telegram_bot.send_message(msg)
            except Exception:
                pass  # HITL notification must never crash the pipeline

        raise HITLPendingInterrupt(event.trace_id, f"HITL event triggered: {event.trace_id}")

    def resolve(self, trace_id: str, resolution: str) -> Optional[Dict]:
        """Mark a pending event as resolved and return the session snapshot.

        Args:
            trace_id:   The event's trace ID.
            resolution: User's decision (e.g., "approve", "skip", "correct:new_text").

        Returns:
            The session snapshot dict if available, else None.
        """
        event_path = os.path.join(self.pending_dir, f"{trace_id}.json")
        if not os.path.exists(event_path):
            return None

        with open(event_path, encoding="utf-8") as f:
            payload = json.load(f)

        payload["resolution"] = resolution
        snapshot = payload.pop("_session_snapshot", None)

        resolved_path = event_path.replace(".json", ".resolved.json")
        AtomicWriter.write_json(resolved_path, payload)
        os.remove(event_path)

        return snapshot

    def list_pending(self) -> list:
        """Return a list of all unresolved HITLEvent IDs."""
        return [
            f.replace(".json", "")
            for f in os.listdir(self.pending_dir)
            if f.endswith(".json") and not f.endswith(".resolved.json")
        ]
