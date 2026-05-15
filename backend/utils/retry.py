"""
Retry Infrastructure
Exponential backoff with jitter for resilient async operations.

Adapted from Ruflo pattern: fault-tolerant coordination with retry.
"""

import asyncio
import logging
import random
from functools import wraps
from typing import Callable, TypeVar, Optional, Tuple, Any

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> Callable[[F], F]:
    """
    Decorator: retry an async function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Multiplier for each retry (default 2.0 = 1, 2, 4, 8...)
        jitter: Add random 0-1s to delay to prevent thundering herd
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Callback(exception, attempt_number, next_delay)

    Usage:
        @retry_with_backoff(max_retries=3, retryable_exceptions=(ConnectionError,))
        async def fetch_data():
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt >= max_retries:
                        break

                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay,
                    )
                    if jitter:
                        delay += random.random()

                    logger.warning(
                        "Retry %d/%d for %s after %s: %.2fs delay",
                        attempt + 1,
                        max_retries,
                        func.__name__,
                        type(e).__name__,
                        delay,
                    )

                    if on_retry:
                        try:
                            on_retry(e, attempt + 1, delay)
                        except Exception:
                            pass

                    await asyncio.sleep(delay)

            raise RetryExhaustedError(
                f"{func.__name__} failed after {max_retries + 1} attempts"
            ) from last_exception

        return wrapper  # type: ignore[return-value]
    return decorator


# ── Standalone retry function ───────────────────────────────────────────────
async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[type, ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    """
    Standalone retry helper for one-off calls.

    Usage:
        result = await retry_async(
            some_async_func, arg1, arg2,
            max_retries=3,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )
    """
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt >= max_retries:
                break

            delay = min(base_delay * (2.0 ** attempt), max_delay) + random.random()
            logger.warning(
                "Retry %d/%d: %.2fs delay (%s)",
                attempt + 1, max_retries, delay, type(e).__name__,
            )
            await asyncio.sleep(delay)

    raise RetryExhaustedError(
        f"Function failed after {max_retries + 1} attempts"
    ) from last_exception
