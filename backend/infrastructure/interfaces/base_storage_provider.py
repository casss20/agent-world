from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable


class BaseStorageProvider(ABC):
    """
    Interface for all database storage.
    Swap DB by changing config — no service code changes.
    """

    @abstractmethod
    async def execute(self, query: str, params: Dict = None) -> Any:
        """Execute raw query."""
        pass

    @abstractmethod
    async def find_one(self, table: str, filters: Dict) -> Optional[Dict]:
        """Find single record."""
        pass

    @abstractmethod
    async def find_many(
        self,
        table: str,
        filters: Dict = None,
        order_by: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Find multiple records."""
        pass

    @abstractmethod
    async def insert(self, table: str, data: Dict) -> str:
        """Insert record, return ID."""
        pass

    @abstractmethod
    async def update(self, table: str, id: str, data: Dict) -> bool:
        """Update record."""
        pass

    @abstractmethod
    async def delete(self, table: str, id: str) -> bool:
        """Delete record."""
        pass

    @abstractmethod
    async def transaction(self, operations: List[Callable]) -> bool:
        """Execute operations in a transaction."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check database connectivity."""
        pass
