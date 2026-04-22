import os
from unittest.mock import MagicMock, patch

from core.task_queue import LocalTaskQueue


@patch("core.task_queue.subprocess.run")
def test_task_queue_success(mock_run, tmp_workspace):
    mock_run.return_value = MagicMock(returncode=0)

    tq = LocalTaskQueue()
    # Replace worker thread to avoid actually starting a background thread for tests
    # We will manually call the loop body or test logic.
    # Actually, we can just push a task and let the thread run, then join.

    tq.enqueue("Test Task", ["echo", "test"], tmp_workspace)

    # Wait for processing
    tq.join()

    # Verify subprocess was called
    assert mock_run.call_count >= 1


@patch("core.task_queue.subprocess.run")
@patch("core.task_queue.shutil.move")
def test_task_queue_dlq_quarantine(mock_move, mock_run, tmp_workspace):
    # Simulate a process that always fails
    mock_run.return_value = MagicMock(returncode=1)

    tq = LocalTaskQueue()
    # We want to test max retries.
    # To prevent test from hanging, we'll enqueue a task and wait for it to be processed max_retries times.

    dummy_file = os.path.join(tmp_workspace, "dummy.pdf")
    with open(dummy_file, "w") as f:
        f.write("test")

    tq.enqueue("Fail Task", ["false"], tmp_workspace, filepath=dummy_file, skill="test-skill")

    tq.join()

    # Since it fails 3 times, run should be called 3 times.
    # Note: Because we start the thread in __init__, it might race.
    # But since we use .join(), it blocks until the queue is empty (meaning all retries are done and it's quarantined).
    assert mock_run.call_count >= 3

    # Verify it was quarantined
    assert mock_move.call_count == 1
    args, _ = mock_move.call_args
    assert args[0] == dummy_file
    assert "quarantine" in args[1]
