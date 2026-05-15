"""
Advanced Pattern Tests
Test orchestrator, background worker, self-healing, and cache.
"""

import os
import pytest
import asyncio
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_agentverse.db"


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    from database import init_db, close_engine
    asyncio.run(init_db())
    yield
    asyncio.run(close_engine())


@pytest.mark.asyncio
async def test_cache_basic():
    """QueryCache should store and retrieve values."""
    from utils.cache import QueryCache

    cache = QueryCache()
    await cache.set("key1", {"data": "value"}, ttl_seconds=5)
    result = await cache.get("key1")
    assert result == {"data": "value"}


@pytest.mark.asyncio
async def test_cache_expiration():
    """QueryCache should expire values after TTL."""
    from utils.cache import QueryCache

    cache = QueryCache()
    await cache.set("key2", "value", ttl_seconds=0)
    # TTL=0 means expires immediately (expires_at == now, so get() will detect expired)
    result = await cache.get("key2")
    assert result is None


@pytest.mark.asyncio
async def test_cache_invalidation():
    """QueryCache should invalidate by pattern."""
    from utils.cache import QueryCache

    cache = QueryCache()
    await cache.set("room:123", "A")
    await cache.set("room:456", "B")
    await cache.set("agent:123", "C")

    count = await cache.invalidate("room:")
    assert count == 2
    assert await cache.get("room:123") is None
    assert await cache.get("agent:123") == "C"


def test_orchestrator_stats():
    """Orchestrator should track pool statistics."""
    from orchestrator import orchestrator

    stats = orchestrator.get_pool_stats()
    assert stats == {}  # No agents registered yet


def test_self_healing_stats():
    """Self-healing service should track issue statistics."""
    from self_healing import self_healing

    stats = self_healing.stats()
    assert stats["total"] == 0
    assert stats["open"] == 0
    assert stats["resolved"] == 0


@pytest.mark.asyncio
async def test_background_worker_metrics():
    """Background worker should track processing metrics."""
    from background_worker import BackgroundWorker

    worker = BackgroundWorker(max_concurrent=5)
    metrics = worker.get_metrics()
    assert metrics["processed"] == 0
    assert metrics["failed"] == 0
    assert metrics["dead_lettered"] == 0


@pytest.mark.asyncio
async def test_task_valid_transitions():
    """TaskService should enforce valid state transitions."""
    from services.task_service import TaskService
    from database import AsyncSessionLocal
    from models import Task

    service = TaskService()
    async with AsyncSessionLocal() as db:
        task = Task(
            id="trans-task-2",
            room_id="trans-room",
            owner_agent_id="agent-1",
            title="Transition Test",
            task_type="test",
            status="pending",
            priority="medium",
            estimated_impact=10,
            created_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.flush()

        # Valid: pending -> active
        result = await service.update_task_status(db, "trans-task-2", "active")
        assert result.status == "active"

        # Invalid: active -> pending (should not be allowed)
        with pytest.raises(ValueError):
            await service.update_task_status(db, "trans-task-2", "pending", agent_id="agent-1")


@pytest.mark.asyncio
async def test_room_membership():
    """RoomService should track agent membership."""
    from services.room_service import RoomService
    from database import AsyncSessionLocal
    from models import Room, Agent, AgentRoom

    async with AsyncSessionLocal() as db:
        room = Room(
            id="mem-room-2",
            project_id="test-project",
            name="Membership Room",
            room_type="collaboration",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        agent = Agent(
            id="mem-agent-2",
            tenant_id="test-tenant",
            name="Member Agent",
            role="worker",
            status="idle",
            system_prompt="You are a test agent.",
            created_at=datetime.now(timezone.utc),
        )
        db.add_all([room, agent])
        await db.flush()

        # Add agent to room
        await RoomService.add_agent_to_room(db, "mem-room-2", "mem-agent-2")

        # Get members
        members = await RoomService.get_room_members(db, "mem-room-2")
        assert len(members) == 1
        assert members[0]["agent_id"] == "mem-agent-2"


@pytest.mark.asyncio
async def test_message_threads():
    """MessageService should handle threaded replies."""
    from services.message_service import MessageService
    from database import AsyncSessionLocal
    from models import Message

    async with AsyncSessionLocal() as db:
        parent = Message(
            id="parent-msg-2",
            room_id="thread-room",
            from_agent_id="agent-a",
            content="Parent message",
            message_type="chat",
            created_at=datetime.now(timezone.utc),
        )
        reply = Message(
            id="reply-msg-2",
            room_id="thread-room",
            from_agent_id="agent-b",
            content="Reply message",
            message_type="chat",
            reply_to_id="parent-msg-2",
            created_at=datetime.now(timezone.utc),
        )
        db.add_all([parent, reply])
        await db.flush()

        thread = await MessageService.get_thread(db, "parent-msg-2")
        assert len(thread) == 2
        assert thread[0].id == "parent-msg-2"
        assert thread[1].id == "reply-msg-2"


@pytest.mark.asyncio
async def test_task_dependency_resolution():
    """TaskService should resolve dependencies in topological order."""
    from services.task_service import TaskService
    from database import AsyncSessionLocal
    from models import Task

    service = TaskService()
    async with AsyncSessionLocal() as db:
        # Create tasks with dependencies: C -> B -> A
        task_a = Task(
            id="dep-a-2", room_id="dep-room", owner_agent_id="agent-1",
            title="Task A", task_type="test", status="pending",
            priority="medium", estimated_impact=10,
            created_at=datetime.now(timezone.utc),
        )
        task_b = Task(
            id="dep-b-2", room_id="dep-room", owner_agent_id="agent-1",
            title="Task B", task_type="test", status="pending",
            priority="medium", estimated_impact=10,
            depends_on=["dep-a-2"],
            created_at=datetime.now(timezone.utc),
        )
        task_c = Task(
            id="dep-c-2", room_id="dep-room", owner_agent_id="agent-1",
            title="Task C", task_type="test", status="pending",
            priority="medium", estimated_impact=10,
            depends_on=["dep-b-2"],
            created_at=datetime.now(timezone.utc),
        )
        db.add_all([task_a, task_b, task_c])
        await db.flush()

        deps = await service.resolve_dependencies(db, "dep-c-2")
        assert deps == ["dep-a-2", "dep-b-2"]  # Topological order
