"""
core/services/scheduler.py — Open Claw Task Scheduler
====================================================
Runs APScheduler to trigger daily Spaced Repetition (Anki) pushes to Telegram,
along with any other cron-style background jobs.

Usage:
    python -m core.services.scheduler
"""

import logging
import os
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

from core.orchestration.task_queue import task_queue
from core.services.sm2 import SM2Engine
from core.services.telegram_bot import send_message
from core.utils.log_manager import build_logger

logger = build_logger("Scheduler")


def push_due_cards():
    """Find cards due today and push them via Telegram."""
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    engine = SM2Engine(workspace_root)
    due = engine.get_due_cards()

    if not due:
        logger.info("No cards due for review today.")
        return

    logger.info(f"Pushing {len(due)} due cards to Telegram.")

    # Push a summary message
    send_message(f"📚 **Spaced Repetition Time!**\nYou have {len(due)} cards due for review today.")

    # We just push the first 5 cards to avoid spamming the user all at once.
    # In a full implementation, the bot could use InlineKeyboards to flip cards and rate them.
    for card in due[:5]:
        msg = f"🎴 **Deck**: {card['deck']}\n\n**Q**: {card['front']}\n\n*(Reply with /reveal {card['id']} to see the answer)*"
        send_message(msg)

    if len(due) > 5:
        send_message(f"...and {len(due) - 5} more.")


def trigger_anki_push():
    """Enqueue the Anki push task into the global single-threaded queue to prevent OOM."""
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cmd = [
        sys.executable,
        "-c",
        "from core.services.scheduler import push_due_cards; push_due_cards()",
    ]
    task_queue.enqueue(
        name="Daily Anki SM-2 Push",
        cmd=cmd,
        cwd=workspace_root,
        subject="System",
    )


def main():
    logger.info("Starting Open Claw Scheduler...")
    scheduler = BlockingScheduler()

    # Schedule the Anki push every day at 09:00 AM via TaskQueue
    scheduler.add_job(trigger_anki_push, "cron", hour=9, minute=0)

    try:
        # We also run it immediately once on startup just to verify it works
        trigger_anki_push()
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
