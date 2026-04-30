"""
core/scheduler.py — Open Claw Proactive Agent Scheduler (P2-1)
==============================================================
Provides APScheduler-backed cron scheduling with a JSON-persisted job store,
enabling academic-edu-assistant and other skills to run autonomously on
user-defined schedules (e.g. daily RSS ingestion, nightly batch processing).

Design:
  - Uses APScheduler (BackgroundScheduler) with a simple in-memory job store.
  - Job definitions are persisted to state/scheduled_jobs.json using AtomicWriter
    so schedules survive bot restarts.
  - Thread-safe: all public methods acquire an internal RLock before mutating state.
  - Skills register callable targets via OpenClawScheduler.add_job().
  - bot_daemon.py exposes /schedule add|list|remove commands that delegate here.

Usage:
    from core.orchestration.scheduler import scheduler

    # Add a daily RSS ingest job at 07:00
    scheduler.add_job(
        job_id="rss_daily",
        cron_expr="0 7 * * *",
        skill_name="academic-edu-assistant",
        command=["python", "scripts/phases/p00_rss_ingest.py"],
        description="Daily arxiv RSS ingest",
    )
    scheduler.start()

Requirements:
    pip install apscheduler
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import subprocess
import sys
import threading
from typing import Any, Callable, Dict, List, Optional

_logger = logging.getLogger("OpenClaw.Scheduler")

# ---------------------------------------------------------------------------
# Scheduled Job Data Contract
# ---------------------------------------------------------------------------

_JOBS_SCHEMA_VERSION = 1


def _job_record(
    job_id: str,
    cron_expr: str,
    skill_name: str,
    command: List[str],
    description: str = "",
    enabled: bool = True,
) -> Dict[str, Any]:
    return {
        "job_id": job_id,
        "cron_expr": cron_expr,
        "skill_name": skill_name,
        "command": command,
        "description": description,
        "enabled": enabled,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_run": None,
    }


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class OpenClawScheduler:
    """APScheduler-backed cron scheduler with JSON persistence.

    Falls back to no-op if APScheduler is not installed, so the bot can
    still start without crashing on minimal environments.
    """

    JOBS_FILE = "state/scheduled_jobs.json"

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.jobs_path = os.path.join(workspace_root, self.JOBS_FILE)
        self._lock = threading.RLock()
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._scheduler: Any = None  # BackgroundScheduler | None; typed as Any to avoid import
        self._load_jobs()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load_jobs(self) -> None:
        os.makedirs(os.path.dirname(self.jobs_path), exist_ok=True)
        if not os.path.exists(self.jobs_path):
            return
        try:
            with open(self.jobs_path, encoding="utf-8") as f:
                data = json.load(f)
            for record in data.get("jobs", []):
                self._jobs[record["job_id"]] = record
            _logger.info("[Scheduler] Loaded %d persisted job(s).", len(self._jobs))
        except Exception as exc:
            _logger.warning("[Scheduler] Could not load scheduled_jobs.json: %s", exc)

    def _save_jobs(self) -> None:
        """Atomically persist all job records."""
        from core.utils.atomic_writer import AtomicWriter

        payload = {
            "_schema_version": _JOBS_SCHEMA_VERSION,
            "_updated_at": datetime.now(timezone.utc).isoformat(),
            "jobs": list(self._jobs.values()),
        }
        AtomicWriter.write_json(self.jobs_path, payload)

    # ── Job Management ────────────────────────────────────────────────────

    def add_job(
        self,
        job_id: str,
        cron_expr: str,
        skill_name: str,
        command: List[str],
        description: str = "",
        enabled: bool = True,
    ) -> bool:
        """Register a new cron job.

        Args:
            job_id:      Unique identifier (e.g. "rss_daily").
            cron_expr:   Standard 5-field cron (e.g. "0 7 * * *").
            skill_name:  Owning skill (for display / filter).
            command:     subprocess command list to execute.
            description: Human-readable label.
            enabled:     Whether to schedule immediately.

        Returns:
            True if added, False if job_id already exists.
        """
        with self._lock:
            if job_id in self._jobs:
                _logger.warning("[Scheduler] job_id '%s' already exists.", job_id)
                return False
            record = _job_record(job_id, cron_expr, skill_name, command, description, enabled)
            self._jobs[job_id] = record
            self._save_jobs()
            if enabled and self._scheduler:
                self._register_apscheduler_job(record)
            _logger.info("[Scheduler] Added job '%s' (%s): %s", job_id, cron_expr, description)
            return True

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job by ID."""
        with self._lock:
            if job_id not in self._jobs:
                return False
            del self._jobs[job_id]
            self._save_jobs()
            if self._scheduler:
                try:
                    self._scheduler.remove_job(job_id)
                except Exception:
                    pass
            _logger.info("[Scheduler] Removed job '%s'.", job_id)
            return True

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Return a copy of all job records."""
        with self._lock:
            return list(self._jobs.values())

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    # ── APScheduler Integration ───────────────────────────────────────────

    def _make_job_fn(self, record: Dict[str, Any]) -> Callable:
        """Create a closure that runs the job's subprocess command."""
        job_id = record["job_id"]
        command = record["command"]
        skill_dir = os.path.join(self.workspace_root, "skills", record["skill_name"])

        def _run():
            _logger.info("[Scheduler] Running job '%s': %s", job_id, command)
            try:
                result = subprocess.run(
                    command,
                    cwd=skill_dir if os.path.isdir(skill_dir) else self.workspace_root,
                    capture_output=True,
                    text=True,
                    timeout=3600,
                )
                status = "success" if result.returncode == 0 else f"exit:{result.returncode}"
                _logger.info("[Scheduler] Job '%s' finished: %s", job_id, status)
            except Exception as exc:
                _logger.error("[Scheduler] Job '%s' failed: %s", job_id, exc)
            finally:
                # Update last_run timestamp
                with self._lock:
                    if job_id in self._jobs:
                        self._jobs[job_id]["last_run"] = datetime.now(timezone.utc).isoformat()
                        self._save_jobs()

        return _run

    def _register_apscheduler_job(self, record: Dict[str, Any]) -> None:
        """Register a single job with the running APScheduler instance."""
        if not self._scheduler:
            return
        parts = record["cron_expr"].split()
        if len(parts) != 5:
            _logger.warning(
                "[Scheduler] Invalid cron expression '%s' for job '%s'.",
                record["cron_expr"],
                record["job_id"],
            )
            return
        minute, hour, day, month, day_of_week = parts
        self._scheduler.add_job(
            self._make_job_fn(record),
            "cron",
            id=record["job_id"],
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            replace_existing=True,
        )

    def start(self) -> bool:
        """Start the APScheduler background scheduler.

        Returns True if started successfully, False if APScheduler is unavailable.
        """
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError:
            _logger.warning(
                "[Scheduler] APScheduler not installed (pip install apscheduler). "
                "Scheduled jobs will not fire automatically."
            )
            return False

        with self._lock:
            if self._scheduler and self._scheduler.running:
                return True
            self._scheduler = BackgroundScheduler(timezone="Asia/Taipei")
            for record in self._jobs.values():
                if record.get("enabled"):
                    self._register_apscheduler_job(record)
            self._scheduler.start()
            _logger.info("[Scheduler] APScheduler started with %d job(s).", len(self._jobs))
        return True

    def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        with self._lock:
            if self._scheduler and self._scheduler.running:
                self._scheduler.shutdown(wait=False)
                _logger.info("[Scheduler] Stopped.")

    def format_status(self) -> str:
        """Return a human-readable status string for Telegram /schedule list."""
        with self._lock:
            if not self._jobs:
                return "\U0001f4c5 \u76ee\u524d\u6c92\u6709\u6392\u7a0b\u4efb\u52d9\u3002"
            lines = ["\U0001f4c5 *\u6392\u7a0b\u4efb\u52d9\u6e05\u55ae*\n"]
            for rec in self._jobs.values():
                status_icon = "\u2705" if rec.get("enabled") else "\u23f8\ufe0f"
                last = rec.get("last_run") or "\u5f9e\u672a\u57f7\u884c"
                lines.append(
                    f"{status_icon} `{rec['job_id']}`\n"
                    f"   Skill: {rec['skill_name']}\n"
                    f"   Cron: `{rec['cron_expr']}`\n"
                    f"   \u8aaa\u660e: {rec.get('description', '')}\n"
                    f"   \u4e0a\u6b21\u57f7\u884c: {last}"
                )
            return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Module-level singleton (initialised lazily by bot_daemon or inbox_daemon)
# ---------------------------------------------------------------------------

_scheduler_instance: Optional[OpenClawScheduler] = None


def get_scheduler(workspace_root: str) -> OpenClawScheduler:
    """Return (or create) the module-level OpenClawScheduler singleton."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = OpenClawScheduler(workspace_root)
    return _scheduler_instance
