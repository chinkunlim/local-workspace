"""
core/file_utils.py — 共用檔案操作工具 (DRY Utilities)
======================================================
Provides safe, exception-handled file operations to replace redundant
try-except blocks across Open Claw skills.

Functions:
  safe_read_json   — Read and parse a JSON file safely.
  ensure_dir       — Create directory if it doesn't exist.
  managed_tmp_dir  — Context manager for temp dir with guaranteed cleanup.
  encode_image_b64 — Encode an image file to a Base64 string (for VLM APIs).
  write_csv_safe   — Write a list of rows to a CSV file using the stdlib csv module.
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


def encode_image_b64(image_path: str) -> str:
    """
    Encode an image file to a Base64 string suitable for VLM API payloads.

    Replaces the redundant `_encode_image()` helper scattered across skills
    (e.g., p01d_vlm_vision.py). Centralised here per §3.4 Audit recommendation.

    Args:
        image_path: Absolute path to the image file.

    Returns:
        Base64-encoded string of the image bytes.

    Raises:
        FileNotFoundError: If the image path does not exist.
        OSError: If the file cannot be read.
    """
    import base64

    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def write_csv_safe(
    path: str,
    rows: list,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """
    Write a list of rows to a CSV file using Python's stdlib csv module.

    Replaces manual string-formatting CSV generation across skills (e.g.,
    academic-edu-assistant p02_anki.py) to correctly handle commas and quotes.

    Args:
        path:   Absolute path to the output .csv file.
        rows:   List of iterables, where each element is one CSV row.
        logger: Optional logger for error reporting.

    Returns:
        True on success, False on failure.
    """
    import csv as _csv

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = _csv.writer(f, quoting=_csv.QUOTE_MINIMAL)
            writer.writerows(rows)
        return True
    except OSError as exc:
        if logger:
            logger.error("write_csv_safe failed (%s): %s", path, exc)
        return False
