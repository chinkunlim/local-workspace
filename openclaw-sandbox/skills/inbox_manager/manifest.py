"""skills/inbox_manager/manifest.py — SkillManifest (#17 / M1)"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from core.services.inbox_daemon import InboxDaemon

    InboxDaemon().run(**kw)


MANIFEST = SkillManifest(
    skill_name="inbox_manager",
    description="Watches the inbox directory for new files and routes them to the appropriate skill via the LocalTaskQueue.",
    phases=["daemon"],
    cli_entry="../../core/inbox_daemon.py",
    run_fn=_run,
    file_types=[".pdf", ".m4a", ".mp3", ".wav", ".md"],
    tags=["inbox", "routing", "daemon", "file-watch"],
)
