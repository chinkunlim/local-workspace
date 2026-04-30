"""Shared fixtures for pytest."""

import os
import shutil
import sys
import tempfile

import pytest

# Ensure the root of open-claw-sandbox is in sys.path so 'core' can be imported
sandbox_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if sandbox_root not in sys.path:
    sys.path.insert(0, sandbox_root)


@pytest.fixture
def tmp_workspace(monkeypatch):
    """Create a temporary workspace directory for testing."""
    tmp_dir = tempfile.mkdtemp(prefix="openclaw_test_workspace_")

    # Patch _workspace_root so AtomicWriter allows writes
    monkeypatch.setattr("core.utils.atomic_writer._workspace_root", tmp_dir)

    # Create expected subdirectories
    os.makedirs(os.path.join(tmp_dir, "logs"))
    os.makedirs(os.path.join(tmp_dir, "data"))

    yield tmp_dir

    # Clean up after test
    shutil.rmtree(tmp_dir, ignore_errors=True)
