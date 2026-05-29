import contextlib
import os
import subprocess
from unittest.mock import MagicMock, patch

from core.orchestration.run_all_pipelines import (
    _LOCK_FILE,
    _acquire_lock,
    _release_lock,
    run_pipelines,
)

# Count how many skills have a run_all.py (dynamic discovery)
_SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")
_EXPECTED_SKILL_COUNT = (
    sum(
        1
        for item in os.listdir(_SKILLS_DIR)
        if os.path.isfile(os.path.join(_SKILLS_DIR, item, "scripts", "run_all.py"))
    )
    if os.path.isdir(_SKILLS_DIR)
    else 0
)


@patch("core.orchestration.run_all_pipelines.subprocess.run")
def test_run_pipelines_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0)

    # Ensure lock is clear before testing
    _release_lock()

    run_pipelines()

    # Assert all discovered skills were attempted
    assert mock_run.call_count == _EXPECTED_SKILL_COUNT

    # Ensure lock was released
    assert not os.path.exists(_LOCK_FILE)


@patch("core.orchestration.run_all_pipelines.subprocess.run")
def test_run_pipelines_timeout_handling(mock_run):
    # Simulate a timeout for every call
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=7200)

    _release_lock()

    with contextlib.suppress(SystemExit):
        run_pipelines()

    # run_pipelines() logs errors but continues — all skills are attempted
    assert mock_run.call_count == _EXPECTED_SKILL_COUNT

    # Ensure lock was released in the finally block despite errors
    assert not os.path.exists(_LOCK_FILE)


def test_lock_mechanism():
    _release_lock()

    # First acquire should succeed
    assert _acquire_lock()
    assert os.path.exists(_LOCK_FILE)

    # Second acquire should fail because the lockfile exists and holds our own PID
    # (Since we are alive, os.kill(pid, 0) succeeds, so it thinks it's locked)
    assert not _acquire_lock()

    _release_lock()
    assert not os.path.exists(_LOCK_FILE)
