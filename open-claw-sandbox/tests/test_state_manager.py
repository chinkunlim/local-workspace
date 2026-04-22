import os
from unittest.mock import patch

from core.state_manager import StateManager


def test_load_state_corrupt_json(tmp_workspace):
    # Setup corrupted JSON
    state_file = os.path.join(tmp_workspace, "dashboard_state.json")
    with open(state_file, "w", encoding="utf-8") as f:
        f.write("{ invalid json")

    sm = StateManager(tmp_workspace, "test-skill")

    # Should handle gracefully and return empty dict
    assert sm.state == {}


def test_update_task_cascade_invalidation(tmp_workspace):
    sm = StateManager(tmp_workspace, "doc-parser")

    # Manually seed state
    sm.state = {"Math": {"file1.pdf": {"p1a": "✅", "p1b": "✅", "p1c": "✅"}}}

    # Call cascade_invalidate directly as update_task doesn't cascade
    sm.cascade_invalidate("Math", "file1.pdf", "p1a")

    # The subsequent phases should be invalidated
    assert sm.state["Math"]["file1.pdf"]["p1b"] == "⏳"
    assert sm.state["Math"]["file1.pdf"]["p1c"] == "⏳"

    # The target phase (p1a) is untouched by cascade_invalidate (it only invalidates subsequent phases)
    assert sm.state["Math"]["file1.pdf"]["p1a"] == "✅"


@patch("core.state_manager.AtomicWriter.write_text")
def test_render_checklist_atomic(mock_write_text, tmp_workspace):
    sm = StateManager(tmp_workspace, "doc-parser")
    sm.state = {"Math": {"test.pdf": {}}}
    sm.update_task("Math", "test.pdf", "p1a", "✅")

    # _save_state automatically calls _render_checklist
    assert mock_write_text.called
    args, _ = mock_write_text.call_args
    # Checklist is in state/checklist.md
    assert args[0] == os.path.join(tmp_workspace, "state", "checklist.md")
    assert "Math" in args[1]
    assert "test.pdf" in args[1]
