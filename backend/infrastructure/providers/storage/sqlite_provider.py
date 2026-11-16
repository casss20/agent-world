import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from infrastructure.interfaces.base_storage_provider import BaseStorageProvider
from database import get_session_factory

logger = logging.getLogger(__name__)


class SQLiteProvider(BaseStorageProvider):
    """
    Wraps existing SQLAlchemy async patterns for SQLite.
    Identical to PostgreSQLProvider in behavior — the DB driver handles differences.
    """

    def __init__(self, session_factory: Optional[async_sessionmaker] = None):
        self.session_factory = session_factory or get_session_factory()

    async def execute(self, query: str, params: Dict = None) -> Any:
        async with self.session_factory() as session:
            result = await session.execute(text(query), params or {})
            return result.mappings().all()

    async def find_one(self, table: str, filters: Dict) -> Optional[Dict]:
        conditions = " AND ".join([f"{k} = :{k}" for k in filters.keys()])
        query = f"SELECT * FROM {table} WHERE {conditions} LIMIT 1"
        rows = await self.execute(query, filters)
        return dict(rows[0]) if rows else None

    async def find_many(
        self,
        table: str,
        filters: Dict = None,
        order_by: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        conditions = ""
        params = dict(filters) if filters else {}
        if filters:
            conditions = "WHERE " + " AND ".join([f"{k} = :{k}" for k in filters.keys()])
        query = f"SELECT * FROM {table} {conditions}"
        if order_by:
            direction = "DESC" if order_by.startswith("-") else "ASC"
            col = order_by.lstrip("-")
            query += f" ORDER BY {col} {direction}"
        query += f" LIMIT {limit} OFFSET {offset}"
        rows = await self.execute(query, params)
        return [dict(row) for row in rows]

    async def insert(self, table: str, data: Dict) -> str:
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f":{k}" for k in data.keys()])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        # SQLite with aiosqlite doesn't always support RETURNING; try it
        try:
            query_returning = query + " RETURNING id"
            rows = await self.execute(query_returning, data)
            if rows:
                return rows[0].get("id") or data.get("id")
        except Exception:
            pass
        # Fallback: just execute without RETURNING
        await self.execute(query, data)
        return data.get("id")

    async def update(self, table: str, id: str, data: Dict) -> bool:
        if not data:
            return False
        set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])
        params = dict(data)
        params["id"] = id
        query = f"UPDATE {table} SET {set_clause} WHERE id = :id"
        await self.execute(query, params)
        return True

    async def delete(self, table: str, id: str) -> bool:
        query = f"DELETE FROM {table} WHERE id = :id"
        await self.execute(query, {"id": id})
        return True

    async def transaction(self, operations: List[Callable]) -> bool:
        async with self.session_factory() as session:
            async with session.begin():
                try:
                    for op in operations:
                        if asyncio.iscoroutinefunction(op):
                            await op(session)
                        else:
                            op(session)
                    return True
                except Exception as e:
                    logger.error("SQLite transaction failed: %s", e)
                    return False

    async def health_check(self) -> bool:
        try:
            result = await self.execute("SELECT 1")
            return bool(result)
        except Exception as e:
            logger.error("SQLite health check failed: %s", e)
            return False
