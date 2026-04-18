# -*- coding: utf-8 -*-
"""
core/bootstrap.py — Open Claw Boundary-Safe Path Initialiser
=============================================================
Every Phase script imports exactly ONE line from this module instead of
copy-pasting the 10-line boundary-safe `sys.path.insert` boilerplate.

Usage (replace the entire Boundary-Safe Init block at the top of any script)::

    from core.bootstrap import ensure_core_path
    ensure_core_path(__file__)

That's it. The function is idempotent — safe to call multiple times.
"""

from __future__ import annotations

import os
import sys


def _find_openclawed_root(script_file: str) -> str:
    """
    Walk up the directory tree from *script_file* until we find the
    directory that contains the ``core/`` package.

    Searching upward (rather than counting ``..`` hops) makes this
    resilient to any future directory restructuring.
    """
    candidate = os.path.abspath(script_file)
    for _ in range(10):             # hard cap — prevents infinite loops
        candidate = os.path.dirname(candidate)
        if os.path.isdir(os.path.join(candidate, "core")):
            return candidate
    # Fallback: WORKSPACE_DIR env or cwd
    return os.environ.get(
        "WORKSPACE_DIR",
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )


def ensure_core_path(script_file: str) -> str:
    """
    Guarantee that ``open-claw-sandbox/`` is on ``sys.path`` so that
    ``from core import ...`` resolves correctly from any Phase script,
    regardless of how the script is launched (direct ``python3``, from
    ``run_all.py``, or via the Web UI subprocess manager).

    Returns:
        The resolved ``open-claw-sandbox`` root directory (absolute path).

    Idempotent — inserts only if not already present.
    """
    root = _find_openclawed_root(script_file)
    if root not in sys.path:
        sys.path.insert(0, root)
    return root
