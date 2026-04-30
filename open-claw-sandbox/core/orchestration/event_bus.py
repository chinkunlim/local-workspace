"""
core/event_bus.py — Lightweight In-Process Pub/Sub Event Bus (P1-1)
===================================================================
Provides a decoupled Pub/Sub mechanism for skill phase chaining.

Design:
  - Zero external dependencies (stdlib only).
  - Thread-safe subscriber registration and event publication.
  - Each handler runs in its own daemon thread to avoid blocking the publisher.
  - Skill manifests register subscribers at import time via EventBus.subscribe().

Lifecycle:
  1. A Phase script publishes a DomainEvent after completing its work.
  2. EventBus fans out to all registered handlers (non-blocking, daemon threads).
  3. Handlers may enqueue follow-up tasks via task_queue.enqueue().

Example:
    # Publishing (in p02_proofread.py after final write):
    from core.event_bus import DomainEvent, EventBus
    EventBus.publish(DomainEvent(
        name="ProofreadCompleted",
        source_skill="audio-transcriber",
        payload={"subject": subj, "output_path": out_path},
    ))

    # Subscribing (in note_generator/manifest.py):
    from core.event_bus import EventBus
    EventBus.subscribe("ProofreadCompleted", my_handler)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import threading
from typing import Any, Callable, Dict, List

_logger = logging.getLogger("OpenClaw.EventBus")


# ---------------------------------------------------------------------------
# Data Contract
# ---------------------------------------------------------------------------


@dataclass
class DomainEvent:
    """A domain event published by a pipeline phase.

    Attributes:
        name:         Event identifier (e.g. "TranscriptionCompleted").
        source_skill: Skill that emitted the event.
        payload:      Arbitrary data passed to subscribers.
        timestamp:    ISO-8601 UTC timestamp (auto-filled).
    """

    name: str
    source_skill: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

# Well-known event names (not exhaustive — skills may define their own)
TRANSCRIPTION_COMPLETED = "TranscriptionCompleted"
PROOFREAD_COMPLETED = "ProofreadCompleted"
DOC_PARSED = "DocParsed"
NOTE_GENERATED = "NoteGenerated"
KNOWLEDGE_COMPILED = "KnowledgeCompiled"


class EventBus:
    """Thread-safe in-process Pub/Sub bus.

    All methods are class-level so that no instance management is required.
    Subscribers receive a copy of the DomainEvent in a separate daemon thread.
    """

    _handlers: Dict[str, List[Callable[[DomainEvent], None]]] = defaultdict(list)
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def subscribe(cls, event_name: str, handler: Callable[[DomainEvent], None]) -> None:
        """Register a handler for a specific event name.

        Args:
            event_name: The event identifier to listen for.
            handler:    Callable that receives a DomainEvent.
        """
        with cls._lock:
            cls._handlers[event_name].append(handler)
        _logger.debug("[EventBus] Subscribed '%s' → %s", event_name, handler.__qualname__)

    @classmethod
    def unsubscribe(cls, event_name: str, handler: Callable[[DomainEvent], None]) -> bool:
        """Remove a specific handler. Returns True if it was found and removed."""
        with cls._lock:
            handlers = cls._handlers.get(event_name, [])
            try:
                handlers.remove(handler)
                return True
            except ValueError:
                return False

    @classmethod
    def publish(cls, event: DomainEvent) -> int:
        """Publish an event to all registered subscribers.

        Each handler is dispatched in its own daemon thread so the publisher
        is never blocked by slow downstream processing.

        Args:
            event: The DomainEvent to publish.

        Returns:
            Number of handlers that were invoked.
        """
        with cls._lock:
            handlers = list(cls._handlers.get(event.name, []))

        if not handlers:
            _logger.debug(
                "[EventBus] Event '%s' published but no subscribers registered.", event.name
            )
            return 0

        _logger.info(
            "[EventBus] Publishing '%s' (source: %s) → %d handler(s)",
            event.name,
            event.source_skill,
            len(handlers),
        )

        for handler in handlers:
            t = threading.Thread(
                target=cls._safe_call,
                args=(handler, event),
                daemon=True,
                name=f"EventBus-{event.name}-{handler.__qualname__}",
            )
            t.start()

        return len(handlers)

    @classmethod
    def _safe_call(cls, handler: Callable[[DomainEvent], None], event: DomainEvent) -> None:
        """Invoke handler, catching and logging any exception so one bad handler
        never prevents others from running."""
        try:
            handler(event)
        except Exception as exc:
            _logger.error(
                "[EventBus] Handler %s raised an exception for event '%s': %s",
                handler.__qualname__,
                event.name,
                exc,
                exc_info=True,
            )

    @classmethod
    def reset(cls) -> None:
        """Clear all subscriptions. Intended for use in tests only."""
        with cls._lock:
            cls._handlers.clear()
