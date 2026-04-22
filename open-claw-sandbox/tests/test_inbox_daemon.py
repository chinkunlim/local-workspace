import os
from unittest.mock import patch

from core.inbox_daemon import SystemInboxDaemon


@patch("core.inbox_daemon.SystemInboxDaemon._schedule_trigger")
def test_process_file_dedup(mock_schedule, tmp_workspace):
    daemon = SystemInboxDaemon()

    # Create a dummy file
    test_file = os.path.join(tmp_workspace, "test.pdf")
    with open(test_file, "w") as f:
        f.write("dummy content")

    # Simulate first trigger
    daemon._process_file(test_file)

    # Assert schedule was called
    assert mock_schedule.call_count == 1

    # Simulate second trigger (e.g. from watchdog while polling size)
    daemon._process_file(test_file)

    # Assert schedule was NOT called again because of _seen_files dedup
    assert mock_schedule.call_count == 1


@patch("core.inbox_daemon.AtomicWriter.write_text")
@patch("core.inbox_daemon.task_queue.enqueue")
def test_check_rewrite_status_atomic(mock_enqueue, mock_write_text, tmp_workspace):
    daemon = SystemInboxDaemon()

    # Create a dummy markdown file with rewrite status
    test_file = os.path.join(tmp_workspace, "test.md")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("---\nstatus: rewrite\n---\nContent")

    daemon._check_rewrite_status(test_file)

    # Assert AtomicWriter was used
    assert mock_write_text.call_count == 1
    args, _ = mock_write_text.call_args
    assert args[0] == test_file
    assert "status: processing" in args[1]

    # Assert enqueue was called
    assert mock_enqueue.call_count == 1
