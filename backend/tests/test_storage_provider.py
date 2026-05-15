"""
Tests for BaseStorageProvider interface.
Week 2 OOP Migration — AgentWorld v2.0
"""

import os
import pytest
from typing import Dict, List, Optional

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_agentverse.db"

from infrastructure.interfaces.base_storage_provider import BaseStorageProvider


class MockStorageProvider(BaseStorageProvider):
    """In-memory storage for testing."""

    def __init__(self):
        self._data: Dict[str, List[Dict]] = {}
        self.call_log = []

    def initialize(self) -> bool:
        return True

    async def execute(self, query: str, params: Dict = None) -> List[Dict]:
        self.call_log.append(("execute", query, params))
        return []

    async def find_one(self, table: str, filters: Dict) -> Optional[Dict]:
        self.call_log.append(("find_one", table, filters))
        rows = self._data.get(table, [])
        for row in rows:
            if all(row.get(k) == v for k, v in filters.items()):
                return row
        return None

    async def find_many(
        self, table: str, filters: Dict = None,
        order_by: str = None, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
        self.call_log.append(("find_many", table, filters))
        rows = self._data.get(table, [])
        if filters:
            rows = [r for r in rows if all(r.get(k) == v for k, v in filters.items())]
        return rows[offset:offset + limit]

    async def insert(self, table: str, data: Dict) -> str:
        self.call_log.append(("insert", table, data))
        if table not in self._data:
            self._data[table] = []
        record_id = str(len(self._data[table]) + 1)
        data["id"] = record_id
        self._data[table].append(data.copy())
        return record_id

    async def update(self, table: str, id: str, data: Dict) -> bool:
        self.call_log.append(("update", table, id, data))
        rows = self._data.get(table, [])
        for row in rows:
            if row.get("id") == id:
                row.update(data)
                return True
        return False

    async def delete(self, table: str, id: str) -> bool:
        self.call_log.append(("delete", table, id))
        rows = self._data.get(table, [])
        for i, row in enumerate(rows):
            if row.get("id") == id:
                rows.pop(i)
                return True
        return False

    async def transaction(self, operations: List) -> bool:
        for op in operations:
            await op(self)
        return True

    async def health_check(self) -> bool:
        return True


# ── Interface Tests ──────────────────────────────────────────────────────

def test_base_storage_is_abstract():
    """BaseStorageProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseStorageProvider()


# ── Mock Provider Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_storage_crud():
    """Test full CRUD with mock storage."""
    store = MockStorageProvider()
    store.initialize()

    # Create
    id1 = await store.insert("agents", {"name": "CEO", "role": "leader"})
    assert id1 == "1"

    # Read
    row = await store.find_one("agents", {"id": id1})
    assert row["name"] == "CEO"

    # Update
    updated = await store.update("agents", id1, {"name": "CEO Updated"})
    assert updated is True

    # Verify update
    row = await store.find_one("agents", {"id": id1})
    assert row["name"] == "CEO Updated"

    # Delete
    deleted = await store.delete("agents", id1)
    assert deleted is True

    # Verify delete
    row = await store.find_one("agents", {"id": id1})
    assert row is None


@pytest.mark.asyncio
async def test_mock_storage_find_many():
    """Test filtering and pagination."""
    store = MockStorageProvider()
    await store.insert("tasks", {"title": "Task A", "status": "pending"})
    await store.insert("tasks", {"title": "Task B", "status": "done"})
    await store.insert("tasks", {"title": "Task C", "status": "pending"})

    # Filter by status
    pending = await store.find_many("tasks", {"status": "pending"})
    assert len(pending) == 2

    # Limit
    all_tasks = await store.find_many("tasks", limit=2)
    assert len(all_tasks) == 2


@pytest.mark.asyncio
async def test_mock_storage_health_check():
    store = MockStorageProvider()
    assert await store.health_check() is True


# ── Registry Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_registry_returns_provider():
    """Registry returns a valid provider."""
    from infrastructure.providers.storage.storage_registry import get_storage_provider
    provider = get_storage_provider()
    assert isinstance(provider, BaseStorageProvider)
    assert await provider.health_check() is True


def test_storage_registry_mock_override():
    """Can override with mock for testing."""
    from infrastructure.providers.storage.storage_registry import set_storage_provider, reset_storage_provider
    mock = MockStorageProvider()
    set_storage_provider(mock)

    from infrastructure.providers.storage.storage_registry import get_storage_provider
    provider = get_storage_provider()
    assert provider is mock

    reset_storage_provider()


# ── PostgreSQL Provider Tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_postgresql_provider_initialize():
    """PostgreSQL provider initializes with existing session factory."""
    from infrastructure.providers.storage.postgresql_provider import PostgreSQLProvider
    from database import get_session_factory

    provider = PostgreSQLProvider(session_factory=get_session_factory())
    assert provider.session_factory is not None


@pytest.mark.asyncio
async def test_postgresql_provider_health_check():
    """PostgreSQL provider health check works."""
    from infrastructure.providers.storage.postgresql_provider import PostgreSQLProvider
    from database import get_session_factory

    provider = PostgreSQLProvider(session_factory=get_session_factory())
    health = await provider.health_check()
    assert health is True


# ── Cleanup ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_provider_after_test():
    yield
    from infrastructure.providers.storage.storage_registry import reset_storage_provider
    reset_storage_provider()
