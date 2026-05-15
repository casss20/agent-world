from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseCacheProvider(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any:
        pass
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        pass
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass
    @abstractmethod
    async def health_check(self) -> bool:
        pass
