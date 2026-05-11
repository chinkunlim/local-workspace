"""skills/telegram_kb_agent/manifest.py — SkillManifest (#17 / M1)"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.bot_daemon import main

    main()


MANIFEST = SkillManifest(
    skill_name="telegram_kb_agent",
    description="Telegram bot providing remote control of Open Claw pipelines, knowledge base queries, HITL callbacks, and runtime model switching.",
    phases=["bot_daemon"],
    cli_entry="scripts/bot_daemon.py",
    run_fn=_run,
    file_types=[],
    tags=["telegram", "bot", "remote", "hitl", "query"],
)
