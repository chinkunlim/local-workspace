# -*- coding: utf-8 -*-
"""Shared logging setup for OpenClaw skills and workspace services."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


class EmojiFormatter(logging.Formatter):
    LEVEL_EMOJI = {
        logging.DEBUG: "🔍",
        logging.INFO: "✅",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "💥",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.emoji = self.LEVEL_EMOJI.get(record.levelno, "•")
        return super().format(record)


def build_logger(
    name: str,
    *,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console: bool = False,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = EmojiFormatter("%(asctime)s [%(levelname)s] %(emoji)s %(message)s")

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


def log_exception(logger: logging.Logger, exc: BaseException, *, context: str = "") -> None:
    prefix = f"{context}: " if context else ""
    logger.error("%s%s", prefix, exc, exc_info=True)
