import logging
from typing import Optional
from infrastructure.interfaces.base_queue_provider import BaseQueueProvider

logger = logging.getLogger(__name__)
_queue_provider: Optional[BaseQueueProvider] = None

def get_queue_provider() -> BaseQueueProvider:
    global _queue_provider
    if _queue_provider is None:
        from infrastructure.providers.queue.memory_queue_provider import MemoryQueueProvider
        _queue_provider = MemoryQueueProvider()
        _queue_provider.initialize()
        logger.info("✅ Queue provider: Memory")
    return _queue_provider

def set_queue_provider(provider: BaseQueueProvider) -> None:
    global _queue_provider
    _queue_provider = provider

def reset_queue_provider() -> None:
    global _queue_provider
    _queue_provider = None
