"""Simple in-memory TTL cache."""
from __future__ import annotations

import time
from typing import Any

_store: dict[str, tuple[float, Any]] = {}
DEFAULT_TTL = 30


def get(key: str) -> Any | None:
    entry = _store.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        _store.pop(key, None)
        return None
    return value


def put(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    _store[key] = (time.monotonic() + ttl, value)


def clear() -> None:
    _store.clear()
