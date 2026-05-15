"""
Query Cache & Optimization
SQLAlchemy query result caching with TTL and invalidation.

Adapted from Ruflo pattern: HybridBackend memory layer + query optimization.
"""

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timezone, timedelta
from functools import wraps

logger = logging.getLogger(__name__)


class QueryCache:
    """
    In-memory query result cache with TTL.
    - Per-key TTL
    - Size-limited LRU eviction
    - Async-safe with locks
    """

    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 60):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl_seconds
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                self._misses += 1
                return None

            if datetime.now(timezone.utc) >= entry["expires_at"]:
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry["value"]

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store value with TTL."""
        async with self._lock:
            # LRU eviction if at capacity
            if len(self._cache) >= self._max_size:
                oldest = min(self._cache, key=lambda k: self._cache[k]["created_at"])
                del self._cache[oldest]

            effective_ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl

            self._cache[key] = {
                "value": value,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=effective_ttl),
            }

    async def invalidate(self, pattern: str) -> int:
        """Invalidate keys matching a substring."""
        async with self._lock:
            keys_to_remove = [k for k in self._cache if pattern in k]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)

    async def clear(self) -> None:
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }


def cached_query(ttl_seconds: int = 60, key_fn: Optional[Callable] = None):
    """
    Decorator to cache async function results.
    Usage:
        @cached_query(ttl_seconds=30)
        async def get_room_state(db, room_id):
            ...
    """
    cache = QueryCache(default_ttl_seconds=ttl_seconds)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_fn:
                cache_key = key_fn(*args, **kwargs)
            else:
                # Default: hash function name + args + kwargs
                key_data = json.dumps(
                    {"fn": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                    sort_keys=True,
                )
                cache_key = hashlib.sha256(key_data.encode()).hexdigest()[:32]

            # Try cache
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute and cache
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl_seconds)
            return result

        # Attach cache for external invalidation
        wrapper._cache = cache
        return wrapper

    return decorator


# ── Global Instance ─────────────────────────────────────────────────────────
query_cache = QueryCache()
