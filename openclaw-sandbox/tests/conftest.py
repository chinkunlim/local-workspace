"""Shared fixtures for pytest."""

import os
import shutil
import sys
import tempfile

import pytest


@pytest.fixture
def tmp_workspace(monkeypatch):
    """Create a temporary workspace directory for testing."""
    tmp_dir = tempfile.mkdtemp(prefix="openclaw_test_workspace_")

    # Override environment variable so get_workspace_root() uses tmp_dir
    monkeypatch.setenv("WORKSPACE_DIR", tmp_dir)

    # Also clear the lru_cache on get_workspace_root in case it was already called
    try:
        from core.utils.workspace import get_workspace_root

        get_workspace_root.cache_clear()
    except ImportError:
        pass

    # Create expected subdirectories
    os.makedirs(os.path.join(tmp_dir, "logs"))
    os.makedirs(os.path.join(tmp_dir, "data"))

    yield tmp_dir

    # Clean up after test
    shutil.rmtree(tmp_dir, ignore_errors=True)
