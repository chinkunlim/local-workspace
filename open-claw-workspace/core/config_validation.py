# -*- coding: utf-8 -*-
"""Configuration validation helpers for required runtime settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence


class ConfigValidationError(ValueError):
    """Raised when a configuration value is missing or out of bounds."""


@dataclass(frozen=True)
class ConfigIssue:
    path: str
    message: str


class ConfigValidator:
    @staticmethod
    def require(value: Any, path: str) -> Any:
        if value is None:
            raise ConfigValidationError(f"Missing required config value: {path}")
        return value

    @staticmethod
    def require_int(value: Any, path: str, *, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
        value = ConfigValidator.require(value, path)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigValidationError(f"{path} must be an integer")
        if min_value is not None and value < min_value:
            raise ConfigValidationError(f"{path} must be >= {min_value}")
        if max_value is not None and value > max_value:
            raise ConfigValidationError(f"{path} must be <= {max_value}")
        return value

    @staticmethod
    def require_float(value: Any, path: str, *, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
        value = ConfigValidator.require(value, path)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigValidationError(f"{path} must be a number")
        numeric = float(value)
        if min_value is not None and numeric < min_value:
            raise ConfigValidationError(f"{path} must be >= {min_value}")
        if max_value is not None and numeric > max_value:
            raise ConfigValidationError(f"{path} must be <= {max_value}")
        return numeric

    @staticmethod
    def require_choice(value: Any, path: str, choices: Sequence[str]) -> str:
        value = ConfigValidator.require(value, path)
        if value not in choices:
            raise ConfigValidationError(f"{path} must be one of: {', '.join(choices)}")
        return str(value)
