import logging
from typing import Any, Dict, List, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, insert, update, delete

from infrastructure.interfaces.base_storage_provider import BaseStorageProvider

logger = logging.getLogger(__name__)


class PostgreSQLProvider(BaseStorageProvider):
    """Wraps existing SQLAlchemy async engine behind BaseStorageProvider interface."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory
        self._engine = None

    def initialize(self, engine=None, session_factory=None) -> bool:
        """Connect to existing database."""
        if session_factory:
            self._session_factory = session_factory
        if engine:
            self._engine = engine
        return self._session_factory is not None

    async def execute(self, query: str, params: Dict = None) -> Any:
        async with self._session_factory() as session:
            result = await session.execute(text(query), params or {})
            return result.fetchall()

    async def find_one(self, table: str, filters: Dict) -> Optional[Dict]:
        async with self._session_factory() as session:
            # Build WHERE clause
            conditions = []
            for key, value in filters.items():
                conditions.append(f"{key} = :{key}")
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT 1"
            result = await session.execute(text(query), filters)
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None

    async def find_many(
        self,
        table: str,
        filters: Dict = None,
        order_by: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        async with self._session_factory() as session:
            where_clause = "1=1"
            params = {}
            if filters:
                conditions = [f"{k} = :{k}" for k in filters.keys()]
                where_clause = " AND ".join(conditions)
                params = filters
            order_clause = f"ORDER BY {order_by}" if order_by else ""
            query = f"SELECT * FROM {table} WHERE {where_clause} {order_clause} LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
            result = await session.execute(text(query), params)
            return [dict(row._mapping) for row in result.fetchall()]

    async def insert(self, table: str, data: Dict) -> str:
        async with self._session_factory() as session:
            columns = ", ".join(data.keys())
            placeholders = ", ".join([f":{k}" for k in data.keys()])
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
            result = await session.execute(text(query), data)
            await session.commit()
            row = result.fetchone()
            return str(row[0]) if row else None

    async def update(self, table: str, id: str, data: Dict) -> bool:
        async with self._session_factory() as session:
            sets = ", ".join([f"{k} = :{k}" for k in data.keys()])
            query = f"UPDATE {table} SET {sets} WHERE id = :id"
            params = {**data, "id": id}
            result = await session.execute(text(query), params)
            await session.commit()
            return result.rowcount > 0

    async def delete(self, table: str, id: str) -> bool:
        async with self._session_factory() as session:
            query = f"DELETE FROM {table} WHERE id = :id"
            result = await session.execute(text(query), {"id": id})
            await session.commit()
            return result.rowcount > 0

    async def transaction(self, operations: List[Callable]) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                for op in operations:
                    await op(session)
            return True

    async def health_check(self) -> bool:
        try:
            if not self._session_factory:
                return False
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.warning("PostgreSQL health check failed: %s", e)
            return False
