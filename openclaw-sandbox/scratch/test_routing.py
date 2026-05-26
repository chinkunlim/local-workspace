import os
import shutil
import time

from core.orchestration.task_queue import task_queue
from core.services.inbox_daemon import SystemInboxDaemon
from core.utils.workspace import get_workspace_root


def test_pipeline_routing():
    workspace = get_workspace_root()
    inbox_dir = os.path.join(workspace, "data", "raw", "TestSubject")
    os.makedirs(inbox_dir, exist_ok=True)

    pdf_path = os.path.join(inbox_dir, "dummy_test.pdf")
    mp3_path = os.path.join(inbox_dir, "dummy_test.mp3")

    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 dummy content")

    with open(mp3_path, "wb") as f:
        f.write(b"ID3 dummy content")

    print(f"Created dummy files in {inbox_dir}")

    # Run inbox daemon scan
    daemon = SystemInboxDaemon()
    daemon.scan_all()

    print("Files routed. Waiting for poller...")
    time.sleep(5)
    print("Waiting for task queue...")
    task_queue.join()


if __name__ == "__main__":
    test_pipeline_routing()
