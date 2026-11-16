"""BaseCacheProvider interface."""
from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseCacheProvider(ABC):
    """Abstract cache provider."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
