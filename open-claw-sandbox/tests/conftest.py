"""Shared fixtures for pytest."""

import os
import shutil
import tempfile

import pytest


@pytest.fixture
def tmp_workspace(monkeypatch):
    """Create a temporary workspace directory for testing."""
    tmp_dir = tempfile.mkdtemp(prefix="openclaw_test_workspace_")

    # Patch _workspace_root so AtomicWriter allows writes
    monkeypatch.setattr("core.atomic_writer._workspace_root", tmp_dir)

    # Create expected subdirectories
    os.makedirs(os.path.join(tmp_dir, "logs"))
    os.makedirs(os.path.join(tmp_dir, "data"))

    yield tmp_dir

    # Clean up after test
    shutil.rmtree(tmp_dir, ignore_errors=True)
