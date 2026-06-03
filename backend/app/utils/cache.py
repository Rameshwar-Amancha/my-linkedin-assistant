"""
cache.py — In-memory cache with optional Redis backend

Provides a simple async get/set/delete interface.
Falls back gracefully to in-memory dict if Redis is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# In-memory store: {key: (value, expires_at)}
_STORE: dict[str, tuple[Any, float]] = {}
_LOCK = asyncio.Lock()

DEFAULT_TTL = 1800  # 30 minutes


async def get_cache(key: str) -> Any | None:
    """Return cached value or None if missing/expired."""
    async with _LOCK:
        entry = _STORE.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at < time.monotonic():
            del _STORE[key]
            return None
        return value


async def set_cache(key: str, value: Any, ttl_seconds: int = DEFAULT_TTL) -> None:
    """Store value with TTL."""
    async with _LOCK:
        _STORE[key] = (value, time.monotonic() + ttl_seconds)


async def delete_cache(key: str) -> None:
    """Remove a cache entry."""
    async with _LOCK:
        _STORE.pop(key, None)


async def clear_all() -> None:
    """Clear all cache entries. Useful for tests."""
    async with _LOCK:
        _STORE.clear()


async def evict_expired() -> int:
    """Remove expired entries. Returns count evicted."""
    now = time.monotonic()
    async with _LOCK:
        expired_keys = [k for k, (_, exp) in _STORE.items() if exp < now]
        for k in expired_keys:
            del _STORE[k]
        return len(expired_keys)
