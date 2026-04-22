import contextlib
import os
import subprocess
from unittest.mock import MagicMock, patch

from core.run_all_pipelines import _LOCK_FILE, _acquire_lock, _release_lock, run_pipelines


@patch("core.run_all_pipelines.subprocess.run")
def test_run_pipelines_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0)

    # Ensure lock is clear before testing
    _release_lock()

    run_pipelines()

    # Assert two pipelines were run
    assert mock_run.call_count == 2

    # Ensure lock was released
    assert not os.path.exists(_LOCK_FILE)


@patch("core.run_all_pipelines.subprocess.run")
def test_run_pipelines_timeout_handling(mock_run):
    # Simulate a timeout
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=7200)

    _release_lock()

    with contextlib.suppress(SystemExit):
        run_pipelines()

    # Should only be called once because it exits on the first timeout
    assert mock_run.call_count == 1

    # Ensure lock was released in the finally block despite sys.exit
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
