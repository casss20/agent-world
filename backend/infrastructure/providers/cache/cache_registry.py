import logging
from typing import Optional
from infrastructure.interfaces.base_cache_provider import BaseCacheProvider

logger = logging.getLogger(__name__)
_cache_provider: Optional[BaseCacheProvider] = None

def get_cache_provider() -> BaseCacheProvider:
    global _cache_provider
    if _cache_provider is None:
        from infrastructure.providers.cache.memory_cache_provider import MemoryCacheProvider
        _cache_provider = MemoryCacheProvider()
        _cache_provider.initialize()
        logger.info("Cache provider: Memory")
    return _cache_provider

def set_cache_provider(provider: BaseCacheProvider) -> None:
    global _cache_provider
    _cache_provider = provider

def reset_cache_provider() -> None:
    global _cache_provider
    _cache_provider = None
