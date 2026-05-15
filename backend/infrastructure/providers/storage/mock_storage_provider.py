import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable

from infrastructure.interfaces.base_storage_provider import BaseStorageProvider

logger = logging.getLogger(__name__)


class MockStorageProvider(BaseStorageProvider):
    """
    In-memory storage provider for unit tests.
    Stores records as dictionaries per table.
    """

    def __init__(self):
        self._data: Dict[str, List[Dict]] = {}
        self._id_counter = 0

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"mock-{self._id_counter}"

    def _matches(self, record: Dict, filters: Dict) -> bool:
        for key, value in filters.items():
            if record.get(key) != value:
                return False
        return True

    async def execute(self, query: str, params: Dict = None) -> Any:
        logger.debug("Mock execute: %s | params=%s", query, params)
        return []

    async def find_one(self, table: str, filters: Dict) -> Optional[Dict]:
        records = self._data.get(table, [])
        for record in records:
            if self._matches(record, filters):
                return dict(record)
        return None

    async def find_many(
        self,
        table: str,
        filters: Dict = None,
        order_by: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        records = self._data.get(table, [])
        if filters:
            records = [r for r in records if self._matches(r, filters)]
        # Simple order_by support (asc only, single column)
        if order_by:
            reverse = False
            sort_key = order_by
            if sort_key.startswith("-"):
                reverse = True
                sort_key = sort_key[1:]
            try:
                records = sorted(records, key=lambda r: r.get(sort_key), reverse=reverse)
            except Exception:
                pass
        return [dict(r) for r in records[offset:offset + limit]]

    async def insert(self, table: str, data: Dict) -> str:
        if table not in self._data:
            self._data[table] = []
        record = dict(data)
        if "id" not in record or record["id"] is None:
            record["id"] = self._next_id()
        self._data[table].append(record)
        return record["id"]

    async def update(self, table: str, id: str, data: Dict) -> bool:
        records = self._data.get(table, [])
        for record in records:
            if record.get("id") == id:
                record.update(data)
                return True
        return False

    async def delete(self, table: str, id: str) -> bool:
        records = self._data.get(table, [])
        for i, record in enumerate(records):
            if record.get("id") == id:
                records.pop(i)
                return True
        return False

    async def transaction(self, operations: List[Callable]) -> bool:
        # In-memory: just execute sequentially, no real rollback
        try:
            for op in operations:
                if asyncio.iscoroutinefunction(op):
                    await op()
                else:
                    op()
            return True
        except Exception as e:
            logger.error("Mock transaction failed: %s", e)
            return False

    async def health_check(self) -> bool:
        return True

    def reset(self) -> None:
        """Clear all data. Useful between tests."""
        self._data.clear()
        self._id_counter = 0
