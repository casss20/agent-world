"""
Rate Limiting
Token bucket algorithm for per-tenant and per-endpoint rate limiting.

Adapted from Ruflo pattern: resource quotas and fair scheduling.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from functools import wraps
from fastapi import HTTPException, Request


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int = 100          # Max tokens
    refill_rate: float = 10.0    # Tokens per second
    _tokens: float = field(default=0.0, repr=False)
    _last_refill: float = field(default_factory=time.time, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def __post_init__(self):
        if self._tokens == 0.0:
            self._tokens = float(self.capacity)

    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_refill
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last_refill = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def wait_time(self, tokens: int = 1) -> float:
        """Calculate seconds to wait until tokens are available."""
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_refill
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last_refill = now

            deficit = tokens - self._tokens
            if deficit <= 0:
                return 0.0
            return deficit / self.refill_rate


# ── Global Rate Limit Store ─────────────────────────────────────────────────
_buckets: Dict[str, TokenBucket] = {}
_store_lock = asyncio.Lock()


async def get_bucket(key: str, capacity: int = 100, refill_rate: float = 10.0) -> TokenBucket:
    """Get or create a token bucket for a key (tenant, IP, user)."""
    if key not in _buckets:
        async with _store_lock:
            if key not in _buckets:
                _buckets[key] = TokenBucket(capacity=capacity, refill_rate=refill_rate)
    return _buckets[key]


async def check_rate_limit(
    key: str,
    capacity: int = 100,
    refill_rate: float = 10.0,
    tokens: int = 1,
) -> Tuple[bool, float]:
    """
    Check if request is within rate limit.
    Returns: (allowed: bool, retry_after: float)
    """
    bucket = await get_bucket(key, capacity, refill_rate)
    allowed = await bucket.acquire(tokens)
    retry_after = await bucket.wait_time(tokens) if not allowed else 0.0
    return allowed, retry_after


# ── FastAPI Middleware / Dependency ──────────────────────────────────────────
async def rate_limit_dependency(
    request: Request,
    capacity: int = 100,
    refill_rate: float = 10.0,
) -> None:
    """
    FastAPI dependency for endpoint rate limiting.
    Usage: dependencies=[Depends(rate_limit_dependency)]
    """
    # Use API key header, or X-Forwarded-For, or direct IP
    key = (
        request.headers.get("X-API-Key")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host if request.client else "unknown"
    )

    allowed, retry_after = await check_rate_limit(key, capacity, refill_rate)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(retry_after))},
        )


# ── Decorator ───────────────────────────────────────────────────────────────
def rate_limited(capacity: int = 100, refill_rate: float = 10.0, key_func=None):
    """
    Decorator for rate limiting async functions.
    key_func: callable that extracts a rate limit key from args/kwargs
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = "global"

            allowed, retry_after = await check_rate_limit(key, capacity, refill_rate)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Retry after {retry_after:.1f}s",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
