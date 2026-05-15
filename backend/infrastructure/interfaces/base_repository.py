"""Week 5: BaseRepository interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseRepository(ABC):
    """Abstract repository for data access."""

    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def find_many(self, filters: Dict = None, order_by: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def delete(self, id: str) -> bool:
        ...

    @abstractmethod
    async def count(self, filters: Dict = None) -> int:
        ...
