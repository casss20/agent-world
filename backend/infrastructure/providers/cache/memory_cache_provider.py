"""Memory cache provider."""
from typing import Any, Optional, Dict

from infrastructure.interfaces.base_cache_provider import BaseCacheProvider


class MemoryCacheProvider(BaseCacheProvider):
    """In-memory cache provider for testing."""

    def __init__(self):
        self._data: Dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        self._data[key] = value
        return True

    async def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def health_check(self) -> bool:
        return True
