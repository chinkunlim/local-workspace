"""Classify exceptions into operational categories for logging and routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorCategory(str, Enum):
    CONFIG = "config"
    INPUT = "input"
    RESOURCE = "resource"
    EXTERNAL = "external"
    SECURITY = "security"
    INTERNAL = "internal"


@dataclass(frozen=True)
class ClassifiedError:
    category: ErrorCategory
    retryable: bool
    message: str
    detail: Optional[str] = None


def classify_exception(exc: BaseException) -> ClassifiedError:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    if "missing required config" in lowered or "config missing" in lowered:
        return ClassifiedError(ErrorCategory.CONFIG, False, message)
    if isinstance(exc, (FileNotFoundError, PermissionError)):
        return ClassifiedError(ErrorCategory.INPUT, False, message)
    if "security" in lowered or "forbidden" in lowered or "blocked" in lowered:
        return ClassifiedError(ErrorCategory.SECURITY, False, message)
    if "memory" in lowered or "ram" in lowered or "disk" in lowered or "temperature" in lowered:
        return ClassifiedError(ErrorCategory.RESOURCE, True, message)
    if (
        "timeout" in lowered
        or "connection" in lowered
        or "network" in lowered
        or "ollama" in lowered
    ):
        return ClassifiedError(ErrorCategory.EXTERNAL, True, message)
    return ClassifiedError(ErrorCategory.INTERNAL, False, message)
