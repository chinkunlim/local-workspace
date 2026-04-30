"""Shared logging setup for OpenClaw skills and workspace services."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
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


class JsonFormatter(logging.Formatter):
    """Structured JSON formatter for headless mode and log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def build_logger(
    name: str,
    *,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console: bool = False,
    console_level: Optional[int] = None,
    file_level: Optional[int] = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(min(level, console_level or level, file_level or level))
    logger.propagate = False

    if logger.handlers:
        return logger

    use_json = os.environ.get("OPENCLAW_LOG_JSON") == "1"
    if use_json:
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = EmojiFormatter(
            "%(asctime)s [%(levelname)s] %(emoji)s %(name)s:%(lineno)d - %(message)s"
        )

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(file_level or level)
        logger.addHandler(file_handler)

    if console:
        stream_handler: logging.Handler
        try:
            from rich.logging import RichHandler

            stream_handler = RichHandler(rich_tracebacks=True, markup=True, show_time=False)
        except ImportError:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
        stream_handler.setLevel(console_level or level)
        logger.addHandler(stream_handler)

    return logger


def log_exception(logger: logging.Logger, exc: BaseException, *, context: str = "") -> None:
    prefix = f"{context}: " if context else ""
    logger.error("%s%s", prefix, exc, exc_info=True)
