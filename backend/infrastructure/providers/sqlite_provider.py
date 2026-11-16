import sqlite3
from typing import Any, Dict, List, Optional, Callable

from infrastructure.interfaces.base_storage_provider import BaseStorageProvider


class SQLiteProvider(BaseStorageProvider):
    """Lightweight SQLite provider for testing and local dev."""

    def __init__(self, db_path: str = "./agentworld_test.db"):
        self._db_path = db_path
        self._conn = None

    def initialize(self) -> bool:
        try:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            return True
        except Exception:
            return False

    async def execute(self, query: str, params: Dict = None) -> Any:
        cursor = self._conn.execute(query, params or {})
        return [dict(row) for row in cursor.fetchall()]

    async def find_one(self, table: str, filters: Dict) -> Optional[Dict]:
        rows = await self.find_many(table, filters, limit=1)
        return rows[0] if rows else None

    async def find_many(
        self, table: str, filters: Dict = None,
        order_by: str = None, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
        where_clause = "1=1"
        params = {}
        if filters:
            conditions = [f"{k} = ?" for k in filters.keys()]
            where_clause = " AND ".join(conditions)
            params = list(filters.values())
        order_clause = f"ORDER BY {order_by}" if order_by else ""
        query = f"SELECT * FROM {table} WHERE {where_clause} {order_clause} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    async def insert(self, table: str, data: Dict) -> str:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self._conn.execute(query, list(data.values()))
        self._conn.commit()
        return str(cursor.lastrowid)

    async def update(self, table: str, id: str, data: Dict) -> bool:
        sets = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {sets} WHERE id = ?"
        cursor = self._conn.execute(query, list(data.values()) + [id])
        self._conn.commit()
        return cursor.rowcount > 0

    async def delete(self, table: str, id: str) -> bool:
        query = f"DELETE FROM {table} WHERE id = ?"
        cursor = self._conn.execute(query, [id])
        self._conn.commit()
        return cursor.rowcount > 0

    async def transaction(self, operations: List[Callable]) -> bool:
        try:
            for op in operations:
                await op(self)
            self._conn.commit()
            return True
        except Exception:
            self._conn.rollback()
            return False

    async def health_check(self) -> bool:
        try:
            self._conn.execute("SELECT 1")
            return True
        except Exception:
            return False
