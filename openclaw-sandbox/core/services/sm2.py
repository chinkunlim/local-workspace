"""
core/services/sm2.py — Spaced Repetition Engine
===============================================
A lightweight SuperMemo-2 (SM-2) algorithm implementation for scheduling Anki cards.
Stores the review schedule in a simple JSON file.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
from typing import Any, Dict, List, Optional

from core.utils.atomic_writer import AtomicWriter


class SM2Engine:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.schedule_path = os.path.join(
            workspace_root, "skills", "academic_edu_assistant", "data", "review_schedule.json"
        )
        self.db: Dict[str, Any] = {"cards": {}}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.schedule_path):
            try:
                with open(self.schedule_path, encoding="utf-8") as f:
                    self.db = json.load(f)
            except Exception:
                self.db = {"cards": {}}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.schedule_path), exist_ok=True)
        AtomicWriter.write_json(self.schedule_path, self.db)

    def add_card(self, front: str, back: str, deck: str) -> str:
        """Add a new card to the engine if it doesn't already exist.
        Returns the card ID.
        """
        import hashlib

        card_id = hashlib.md5(f"{deck}:{front}".encode()).hexdigest()

        if card_id not in self.db["cards"]:
            self.db["cards"][card_id] = {
                "id": card_id,
                "deck": deck,
                "front": front,
                "back": back,
                "efactor": 2.5,  # Easiness factor
                "interval": 0,  # Days until next review
                "repetition": 0,  # Consecutive correct answers
                "next_review": datetime.now().strftime("%Y-%m-%d"),
                "added_at": datetime.now().isoformat(),
            }
            self._save()
        return card_id

    def get_due_cards(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all cards due for review on or before the given date (YYYY-MM-DD)."""
        target = date_str or datetime.now().strftime("%Y-%m-%d")
        due = []
        for card in self.db["cards"].values():
            if card.get("next_review", target) <= target:
                due.append(card)
        return due

    def review_card(self, card_id: str, quality: int) -> None:
        """Process a review rating for a card using the SM-2 algorithm.
        Quality (0-5):
        5 - perfect response
        4 - correct response after a hesitation
        3 - correct response recalled with serious difficulty
        2 - incorrect response; where the correct one seemed easy to recall
        1 - incorrect response; the correct one remembered
        0 - complete blackout
        """
        card = self.db["cards"].get(card_id)
        if not card:
            return

        q = max(0, min(5, quality))

        # SM-2 Algorithm
        if q >= 3:
            if card["repetition"] == 0:
                card["interval"] = 1
            elif card["repetition"] == 1:
                card["interval"] = 6
            else:
                card["interval"] = round(card["interval"] * card["efactor"])
            card["repetition"] += 1
        else:
            card["repetition"] = 0
            card["interval"] = 1

        card["efactor"] = card["efactor"] + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        card["efactor"] = max(1.3, card["efactor"])

        next_date = datetime.now() + timedelta(days=card["interval"])
        card["next_review"] = next_date.strftime("%Y-%m-%d")

        self._save()
