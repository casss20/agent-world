from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseRepository(ABC):
    """Interface for all data repositories."""

    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    async def find_many(
        self, filters: Dict = None,
        order_by: str = None, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
        pass

    @abstractmethod
    async def save(self, data: Dict) -> Dict:
        pass

    @abstractmethod
    async def update(self, id: str, data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass

    @abstractmethod
    async def count(self, filters: Dict = None) -> int:
        pass
