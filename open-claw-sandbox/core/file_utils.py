"""
core/file_utils.py — 共用檔案操作工具 (DRY Utilities)
======================================================
Provides safe, exception-handled file operations to replace redundant
try-except blocks across Open Claw skills.
"""

from collections.abc import Generator
from contextlib import contextmanager
import json
import logging
import os
import shutil
import tempfile
from typing import Any, Dict, Optional


def safe_read_json(path: str, logger: Optional[logging.Logger] = None) -> Optional[Dict[str, Any]]:
    """
    Read and parse a JSON file safely.
    Returns None if the file doesn't exist, is corrupted, or cannot be read.
    """
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        if logger:
            logger.error("JSON 檔案損毀 (%s): %s", path, exc)
        return None
    except OSError as exc:
        if logger:
            logger.error("無法讀取 JSON 檔案 (%s): %s", path, exc)
        return None


def ensure_dir(path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.
    Returns the absolute path.
    """
    abs_path = os.path.abspath(path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


@contextmanager
def managed_tmp_dir(parent: str, prefix: str = "openclaw_tmp_") -> Generator[str, None, None]:
    """
    Context manager: creates a temporary directory and guarantees cleanup on exit/crash.
    Use this to prevent orphan files (like .wav chunks) from accumulating.
    """
    ensure_dir(parent)
    tmp = tempfile.mkdtemp(prefix=prefix, dir=parent)
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
