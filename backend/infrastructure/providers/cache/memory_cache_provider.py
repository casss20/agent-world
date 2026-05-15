import time
from typing import Any, Dict, Optional
from infrastructure.interfaces.base_cache_provider import BaseCacheProvider

class MemoryCacheProvider(BaseCacheProvider):
    def __init__(self):
        self._store: Dict[str, tuple[Any, float]] = {}

    def initialize(self) -> bool:
        return True

    async def get(self, key: str) -> Any:
        if key in self._store:
            value, expiry = self._store[key]
            if expiry == 0 or time.time() < expiry:
                return value
            del self._store[key]
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        expiry = time.time() + ttl if ttl > 0 else 0
        self._store[key] = (value, expiry)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        val = await self.get(key)
        return val is not None

    async def health_check(self) -> bool:
        return True
