"""Queue provider registry."""
from typing import Optional

from infrastructure.interfaces.base_queue_provider import BaseQueueProvider

_active_provider: Optional[BaseQueueProvider] = None


def get_queue_provider() -> BaseQueueProvider:
    """Get active queue provider."""
    global _active_provider
    if _active_provider is not None:
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
