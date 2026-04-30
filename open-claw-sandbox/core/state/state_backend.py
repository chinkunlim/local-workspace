"""
core/state_backend.py — Pluggable State Storage Protocol (P3-4)
===============================================================
Defines a StateBackend Protocol so StateManager can swap between:
  - JsonStateBackend   (current default — file-backed JSON with fcntl locking)
  - RedisStateBackend  (production — atomic Redis MULTI/EXEC, TTL support)

This is a non-breaking addition: StateManager still defaults to
JsonStateBackend; pass backend=RedisStateBackend(...) in config for prod.

Config (config.yaml):
    state_backend:
      type: "json"        # or "redis"
      redis:
        url: "redis://localhost:6379"
        db: 0
        key_prefix: "openclaw:"
        ttl_seconds: 86400   # 24h — 0 = no expiry

Usage:
    from core.state_backend import get_state_backend
    backend = get_state_backend(config_section)
    backend.set("workspace-state", {"tasks": {}})
    data = backend.get("workspace-state")
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import threading
from typing import Any, Dict, Optional, Protocol, runtime_checkable

_logger = logging.getLogger("OpenClaw.StateBackend")


# ---------------------------------------------------------------------------
# Protocol (Interface)
# ---------------------------------------------------------------------------


@runtime_checkable
class StateBackend(Protocol):
    """Minimal key-value store for pipeline state persistence."""

    def get(self, key: str) -> Optional[Dict[str, Any]]: ...
    def set(self, key: str, value: Dict[str, Any]) -> None: ...
    def delete(self, key: str) -> bool: ...
    def exists(self, key: str) -> bool: ...


# ---------------------------------------------------------------------------
# JSON Backend  (current default)
# ---------------------------------------------------------------------------


class JsonStateBackend:
    """File-backed JSON state store with cross-process fcntl.flock locking.

    This is the existing behaviour extracted from StateManager._load_state /
    _save_state into a reusable backend object.

    Args:
        base_dir: Directory where <key>.json files are stored.
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self._lock = threading.RLock()
        os.makedirs(base_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        safe_key = key.replace("/", "_").replace("..", "__")
        return os.path.join(self.base_dir, f"{safe_key}.json")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        with self._lock:
            try:
                with open(path, encoding="utf-8") as f:
                    fcntl.flock(f, fcntl.LOCK_SH)
                    try:
                        return json.load(f)
                    finally:
                        fcntl.flock(f, fcntl.LOCK_UN)
            except Exception as exc:
                _logger.warning("[JsonBackend] get(%s) failed: %s", key, exc)
                return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        from core.atomic_writer import AtomicWriter

        path = self._path(key)
        lock_path = path + ".lock"
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with self._lock, open(lock_path, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                AtomicWriter.write_json(path, value)
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))


# ---------------------------------------------------------------------------
# Redis Backend  (production)
# ---------------------------------------------------------------------------


class RedisStateBackend:
    """Redis-backed state store with MULTI/EXEC optimistic locking.

    Requires: pip install redis
    Each key is stored as a JSON string in Redis under `key_prefix + key`.
    Optional TTL ensures stale state is automatically expired.

    Args:
        url:        Redis connection URL (e.g. "redis://localhost:6379").
        db:         Redis database number (default 0).
        key_prefix: Namespace prefix for all keys.
        ttl_seconds: Seconds before a key expires. 0 = no expiry.
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        db: int = 0,
        key_prefix: str = "openclaw:",
        ttl_seconds: int = 0,
    ):
        try:
            import redis as _redis  # type: ignore[import]

            self._redis = _redis.from_url(url, db=db, decode_responses=True)
            self._redis.ping()  # Fail fast if Redis is not reachable
        except ImportError as exc:
            raise ImportError(
                "redis package is required for RedisStateBackend. Run: pip install redis"
            ) from exc
        self._prefix = key_prefix
        self._ttl = ttl_seconds
        _logger.info("[RedisBackend] Connected to %s (db=%d, ttl=%ds)", url, db, ttl_seconds)

    def _k(self, key: str) -> str:
        return self._prefix + key

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            raw = self._redis.get(self._k(key))
            return json.loads(raw) if raw else None
        except Exception as exc:
            _logger.warning("[RedisBackend] get(%s) failed: %s", key, exc)
            return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Atomic set with optional TTL using pipeline."""
        try:
            serialised = json.dumps(value, ensure_ascii=False)
            with self._redis.pipeline() as pipe:
                pipe.set(self._k(key), serialised)
                if self._ttl > 0:
                    pipe.expire(self._k(key), self._ttl)
                pipe.execute()
        except Exception as exc:
            _logger.error("[RedisBackend] set(%s) failed: %s", key, exc)
            raise

    def delete(self, key: str) -> bool:
        return bool(self._redis.delete(self._k(key)))

    def exists(self, key: str) -> bool:
        return bool(self._redis.exists(self._k(key)))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_state_backend(cfg: Dict[str, Any], base_dir: str = "") -> Any:
    """Instantiate a StateBackend from a config section dict.

    Args:
        cfg:      The `state_backend:` section from config.yaml.
        base_dir: Base directory for the JSON backend (ignored for Redis).

    Returns:
        A StateBackend-compatible instance.
    """
    backend_type = (cfg.get("type") or "json").lower()
    if backend_type == "redis":
        redis_cfg = cfg.get("redis", {})
        return RedisStateBackend(
            url=redis_cfg.get("url", "redis://localhost:6379"),
            db=redis_cfg.get("db", 0),
            key_prefix=redis_cfg.get("key_prefix", "openclaw:"),
            ttl_seconds=redis_cfg.get("ttl_seconds", 0),
        )
    # Default: JSON
    if not base_dir:
        raise ValueError("base_dir is required for JsonStateBackend")
    return JsonStateBackend(base_dir=base_dir)
