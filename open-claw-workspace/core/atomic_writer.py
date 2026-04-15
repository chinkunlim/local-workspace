# -*- coding: utf-8 -*-
"""Crash-safe file writes using atomic rename."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any


class AtomicWriter:
    @staticmethod
    def write_text(path: str, content: str, encoding: str = "utf-8") -> None:
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", dir=parent_dir or None)
        try:
            with os.fdopen(fd, "w", encoding=encoding) as handle:
                handle.write(content)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def write_json(path: str, payload: Any, encoding: str = "utf-8") -> None:
        AtomicWriter.write_text(path, json.dumps(payload, ensure_ascii=False, indent=2), encoding=encoding)