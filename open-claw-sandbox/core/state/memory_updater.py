"""
core/memory_updater.py — Long-Term Semantic Memory & Adaptive Glossary (#15)
=============================================================================
Strategic scaffold for persisting user corrections across sessions and
automatically updating skill glossaries and vector DB memories.

CURRENT STATUS: Scaffold / Interface Definition
  CorrectionEvent, GlossaryPatcher, and the update lifecycle are fully
  defined. Vector DB integration (infra/open-webui/vector_db/) is
  deferred to P3 once the embedding pipeline is stabilised.

Lifecycle:
  1. A Phase script (e.g., p02_proofread) detects a user correction via HITL
     resolution payload and creates a CorrectionEvent.
  2. MemoryUpdater.record() persists the event to corrections.jsonl.
  3. MemoryUpdater.apply_to_glossary() patches the skill's glossary.json
     with the new canonical term.
  4. (Future P3) MemoryUpdater.sync_vector_db() upserts a new embedding
     to prevent future semantic duplicates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
from typing import Optional
from core.utils.atomic_writer import AtomicWriter

_logger = logging.getLogger("OpenClaw.MemoryUpdater")

# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------


@dataclass
class CorrectionEvent:
    """Records a single user-confirmed term correction."""

    wrong_term: str
    correct_term: str
    skill_name: str
    subject: Optional[str] = None
    context: Optional[str] = None  # P3: text snippet around the term
    phase: str = "unknown"
    source: str = "hitl"  # "hitl" | "manual" | "auto"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Memory Updater
# ---------------------------------------------------------------------------


class MemoryUpdater:
    """Manages cross-session corrections and adaptive glossary updates.

    Provides deterministic, file-backed persistence for user corrections
    so that the system learns from each interaction without retraining.
    """

    CORRECTIONS_FILE = "state/corrections.jsonl"

    def __init__(self, base_dir: str):
        """
        Args:
            base_dir: The skill's data base directory.
        """
        self.base_dir = base_dir
        self.corrections_path = os.path.join(base_dir, self.CORRECTIONS_FILE)
        os.makedirs(os.path.dirname(self.corrections_path), exist_ok=True)

    def record(self, event: CorrectionEvent) -> None:
        """Append a CorrectionEvent to the persistent corrections log.

        Uses append mode for JSONL (one JSON object per line) so that
        concurrent writes from multiple pipeline phases do not corrupt state.
        """
        with open(self.corrections_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    def apply_to_glossary(self, glossary_path: str, event: CorrectionEvent) -> bool:
        """Patch a glossary.json file with a new correction.

        Reads the existing glossary, inserts/updates the wrong→correct mapping,
        and atomically rewrites the file. This is idempotent and safe to
        call multiple times with the same event.

        Args:
            glossary_path: Absolute path to the target glossary.json.
            event:         The correction to apply.

        Returns:
            True if the glossary was updated, False if no change was needed.
        """
        if os.path.exists(glossary_path):
            with open(glossary_path, encoding="utf-8") as f:
                try:
                    gloss: dict = json.load(f)
                except json.JSONDecodeError:
                    gloss = {}
        else:
            gloss = {}

        existing = gloss.get(event.wrong_term)
        if existing == event.correct_term:
            return False  # Already up-to-date

        gloss[event.wrong_term] = event.correct_term

        # Atomic write: write to temp then rename
        tmp_path = glossary_path + ".tmp"
        AtomicWriter.write_json(tmp_path, gloss)
        os.replace(tmp_path, glossary_path)

        return True

    def load_corrections(self) -> list:
        """Load all recorded corrections as a list of dicts."""
        if not os.path.exists(self.corrections_path):
            return []
        events = []
        with open(self.corrections_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return events

    def replay_to_glossary(self, glossary_path: str, subject: Optional[str] = None) -> int:
        """Replay all recorded corrections to a glossary (e.g., after reset).

        Args:
            glossary_path: Target glossary.json path.
            subject:       If provided, only apply corrections for this subject.

        Returns:
            Number of corrections applied.
        """
        count = 0
        for raw in self.load_corrections():
            if subject and raw.get("subject") != subject:
                continue
            evt = CorrectionEvent(
                **{k: v for k, v in raw.items() if k in CorrectionEvent.__dataclass_fields__}
            )
            if self.apply_to_glossary(glossary_path, evt):
                count += 1
        return count

    def sync_vector_db(self, event: CorrectionEvent) -> None:  # noqa: F821
        """(P3-5) Upsert a correction event into the ChromaDB vector store.

        Embeds ``event.correct_term`` via the Ollama embeddings endpoint and
        upserts the document into the ``wiki_knowledge`` collection so future
        RAG queries can find the corrected terminology.

        Degrades gracefully: logs a warning and returns if ChromaDB or Ollama
        is not available, so pipeline execution is never blocked.
        """
        try:
            import chromadb as _chromadb  # type: ignore[import]
        except ImportError:
            _logger.debug("[MemoryUpdater] chromadb not installed — skipping sync_vector_db.")
            return

        # Locate ChromaDB via environment or default path
        db_path = os.environ.get(
            "OPENCLAW_VECTOR_DB_PATH",
            os.path.join(self.base_dir, "..", "telegram_kb_agent", "state", "chroma_db"),
        )
        db_path = os.path.realpath(db_path)
        if not os.path.exists(db_path):
            _logger.debug("[MemoryUpdater] ChromaDB not found at %s — skipping.", db_path)
            return

        try:
            client = _chromadb.PersistentClient(path=db_path)
            collection = client.get_or_create_collection(name="wiki_knowledge")
        except Exception as exc:
            _logger.warning("[MemoryUpdater] sync_vector_db: could not open ChromaDB: %s", exc)
            return

        # Get embedding from Ollama
        embed_model = "nomic-embed-text"
        ollama_url = os.environ.get("OLLAMA_API_URL", "http://127.0.0.1:11434/api")
        try:
            import requests

            doc_text = f"{event.wrong_term} → {event.correct_term}"
            if getattr(event, "context", None):
                doc_text += f"\n{event.context}"
            resp = requests.post(
                f"{ollama_url}/embeddings",
                json={"model": embed_model, "prompt": doc_text},
                timeout=20,
            )
            if not resp.ok:
                _logger.warning("[MemoryUpdater] Embedding request failed: %s", resp.text)
                return
            embedding = resp.json().get("embedding")
            if not embedding:
                return
        except Exception as exc:
            _logger.warning("[MemoryUpdater] sync_vector_db: embedding failed: %s", exc)
            return

        # Upsert into collection
        doc_id = f"correction_{event.subject}_{event.wrong_term}_{event.correct_term}"
        doc_id = "".join(c if c.isalnum() else "_" for c in doc_id)[:128]
        try:
            collection.upsert(
                ids=[doc_id],
                documents=[doc_text],
                embeddings=[embedding],
                metadatas=[
                    {
                        "subject": event.subject,
                        "wrong_term": event.wrong_term,
                        "correct_term": event.correct_term,
                        "source": "correction_pipeline",
                    }
                ],
            )
            _logger.info("[MemoryUpdater] sync_vector_db: upserted '%s'", event.correct_term)
        except Exception as exc:
            _logger.warning("[MemoryUpdater] sync_vector_db: upsert failed: %s", exc)
