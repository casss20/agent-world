"""Cache provider registry."""
from typing import Optional

from infrastructure.interfaces.base_cache_provider import BaseCacheProvider

_active_provider: Optional[BaseCacheProvider] = None


def get_cache_provider() -> BaseCacheProvider:
    """Get active cache provider."""
    global _active_provider
    if _active_provider is not None:
        return _active_provider
    from infrastructure.providers.cache.memory_cache_provider import MemoryCacheProvider
    _active_provider = MemoryCacheProvider()
    return _active_provider


def set_cache_provider(provider: BaseCacheProvider) -> None:
    """Set active cache provider."""
    global _active_provider
    _active_provider = provider


def reset_cache_provider() -> None:
    """Reset active cache provider."""
    global _active_provider
    _active_provider = None
