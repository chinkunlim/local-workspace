import os
from unittest.mock import MagicMock, patch

from core.services.inbox_daemon import SystemInboxDaemon


def test_process_file_dedup(tmp_workspace):
    daemon = SystemInboxDaemon()

    try:
        # Create a dummy file inside raw_path so path routing works
        inbox_dir = os.path.join(daemon.raw_path, "Default")
        os.makedirs(inbox_dir, exist_ok=True)
        test_file = os.path.join(inbox_dir, "test.pdf")
        with open(test_file, "w") as f:
            f.write("dummy content")

        with (
            patch.object(daemon.stability_poller, "schedule_trigger") as mock_schedule,
            patch("core.services.inbox_daemon.os.rename"),
            patch("core.services.inbox_daemon.update_session_manifest"),
        ):
            # Simulate first trigger
            daemon._process_file(test_file)
            count_after_first = mock_schedule.call_count

            # Simulate second trigger — dedup should prevent re-processing
            daemon._process_file(test_file)
            count_after_second = mock_schedule.call_count

        # Both counts should be equal (no additional call on second trigger)
        assert count_after_second == count_after_first
    finally:
        daemon.stop()


@patch("core.services.inbox_daemon.AtomicWriter.write_text")
@patch("core.orchestration.task_queue.LocalTaskQueue")
def test_check_rewrite_status_atomic(mock_queue_cls, mock_write_text, tmp_workspace):
    # Set up mock queue instance
    mock_queue_instance = MagicMock()
    mock_queue_cls.return_value = mock_queue_instance

    daemon = SystemInboxDaemon()
    try:
        # Create a dummy markdown file with rewrite status
        test_file = os.path.join(tmp_workspace, "test.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("---\nstatus: rewrite\n---\nContent")

        daemon._check_rewrite_status(test_file)

        # Assert AtomicWriter was used to update the status
        assert mock_write_text.call_count == 1
        args, _ = mock_write_text.call_args
        assert args[0] == test_file
        assert "status: processing" in args[1]

        # Assert LocalTaskQueue().enqueue was called
        assert mock_queue_instance.enqueue.call_count == 1
    finally:
        daemon.stop()
