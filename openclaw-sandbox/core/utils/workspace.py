"""Single source of truth for workspace root resolution."""

from __future__ import annotations

from functools import lru_cache
import os


@lru_cache(maxsize=1)
def get_workspace_root() -> str:
    """Determine the workspace root directory.

    Priority:
    1. WORKSPACE_DIR environment variable
    2. Sentinel file discovery (pyproject.toml) upwards from current file
    3. Fallback to raising RuntimeError
    """
    if env := os.environ.get("WORKSPACE_DIR"):
        return os.path.abspath(env)

    # Walk up from current file to find openclaw-sandbox marker
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.exists(os.path.join(current, "pyproject.toml")):
            return current
        current = os.path.dirname(current)

    raise RuntimeError("Cannot determine workspace root (no pyproject.toml found)")
