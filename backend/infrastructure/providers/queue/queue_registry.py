"""Queue provider registry."""
import os
from typing import Optional

from infrastructure.interfaces.base_queue_provider import BaseQueueProvider

_active_provider: Optional[BaseQueueProvider] = None


def get_queue_provider() -> BaseQueueProvider:
    """Get active queue provider."""
    global _active_provider
    if _active_provider is not None:
        return _active_provider

    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            import redis.asyncio as redis_async
            client = redis_async.from_url(redis_url)
            from infrastructure.providers.queue.redis_queue_provider import RedisQueueProvider
            _active_provider = RedisQueueProvider(client)
            return _active_provider
        except Exception:
            pass

    database_url = os.getenv("DATABASE_URL", "")
    if database_url and ("postgresql" in database_url or "postgres" in database_url):
        from infrastructure.providers.queue.postgres_queue_provider import PostgresQueueProvider
        _active_provider = PostgresQueueProvider()
        return _active_provider

    from infrastructure.providers.queue.memory_queue_provider import MemoryQueueProvider
    _active_provider = MemoryQueueProvider()
    return _active_provider


def set_queue_provider(provider: BaseQueueProvider) -> None:
    """Set active queue provider."""
    global _active_provider
    _active_provider = provider


def reset_queue_provider() -> None:
    """Reset active queue provider."""
    global _active_provider
    _active_provider = None
