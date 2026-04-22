import json
import os

from core.resume_manager import ResumeManager


def test_resume_manager_lifecycle(tmp_workspace):
    rm = ResumeManager(tmp_workspace)

    pdf_id = "test_doc_01"
    phase_key = "p1"
    chunk_index = 2

    # 1. Save Checkpoint
    rm.save_checkpoint(pdf_id, phase_key, chunk_index=chunk_index)

    # Verify file was created
    checkpoint_file = os.path.join(tmp_workspace, "state", "resume", pdf_id, "resume_state.json")
    assert os.path.exists(checkpoint_file)

    with open(checkpoint_file) as f:
        data = json.load(f)
        assert data["pdf_id"] == pdf_id
        assert data["phase"] == phase_key
        assert data["chunk_index"] == chunk_index
        assert data["status"] == "interrupted"

    # 2. Load Checkpoint
    loaded = rm.resume_from(pdf_id)
    assert loaded is not None
    assert loaded["pdf_id"] == pdf_id
    assert loaded["phase"] == phase_key

    # 3. Clear Checkpoint
    rm.clear_checkpoint(pdf_id)

    # Verify status changed to completed
    with open(checkpoint_file) as f:
        data = json.load(f)
        assert data["status"] == "completed"

    # Load checkpoint should now return None since it's no longer interrupted
    assert rm.resume_from(pdf_id) is None
