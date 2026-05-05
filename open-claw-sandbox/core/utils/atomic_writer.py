"""Crash-safe file writes using atomic rename."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

_core_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.environ.get(
    "WORKSPACE_DIR", os.path.abspath(os.path.join(_core_dir, "..", ".."))
)


class AtomicWriter:
    @staticmethod
    def write_text(path: str, content: str, encoding: str = "utf-8") -> None:
        abs_path = os.path.abspath(os.path.expanduser(path))
        if not abs_path.startswith(_workspace_root):
            raise PermissionError(
                f"🚨 Path Traversal 防禦觸發！禁止寫入 Workspace 外的絕對路徑: {abs_path}"
            )

        parent_dir = os.path.dirname(abs_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", dir=parent_dir or None)
        try:
            with os.fdopen(fd, "w", encoding=encoding) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, abs_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def write_json(path: str, payload: Any, encoding: str = "utf-8") -> None:
        AtomicWriter.write_text(
            path, json.dumps(payload, ensure_ascii=False, indent=2), encoding=encoding
        )
