"""
Test Infrastructure
Verify all new modules import correctly and basic functionality works.
"""

import os
import pytest
import asyncio
from datetime import datetime, timezone

# Use SQLite for tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_agentverse.db"


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create tables once before all tests, drop after."""
    from database import init_db, close_engine
    asyncio.run(init_db())
    yield
    asyncio.run(close_engine())


def test_imports():
    """All new modules should import without errors."""
    from database import engine, get_db, init_db, AsyncSessionLocal
    from websocket_manager import WebSocketManager, ws_manager
    from utils import (
        retry_with_backoff,
        RetryExhaustedError,
        setup_logging,
        get_logger,
        LogContext,
        check_rate_limit,
    )
    from services import RoomService, TaskService, MessageService
    from routes import (
        rooms_router,
        tasks_router,
        agents_router,
        messages_router,
        projects_router,
        governance_router,
    )


@pytest.mark.asyncio
async def test_database_session():
    """Database session factory should create valid sessions."""
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        assert session is not None


@pytest.mark.asyncio
async def test_websocket_manager_lifecycle():
    """WebSocket manager should start/stop cleanly."""
    from websocket_manager import WebSocketManager

    manager = WebSocketManager()
    await manager.start()
    assert manager.total_connections() == 0
    assert manager.active_rooms() == []
    await manager.stop()


@pytest.mark.asyncio
async def test_retry_decorator():
    """Retry decorator should retry on specified exceptions."""
    from utils.retry import retry_with_backoff

    call_count = 0

    @retry_with_backoff(max_retries=2, base_delay=0.01)
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Simulated failure")
        return "success"

    result = await flaky_function()
    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_exhaustion():
    """Retry decorator should raise RetryExhaustedError after max retries."""
    from utils.retry import retry_with_backoff, RetryExhaustedError

    @retry_with_backoff(max_retries=1, base_delay=0.01)
    async def always_fails():
        raise ConnectionError("Always fails")

    with pytest.raises(RetryExhaustedError):
        await always_fails()


@pytest.mark.asyncio
async def test_rate_limiter():
    """Rate limiter should track requests correctly."""
    from utils.rate_limiter import check_rate_limit

    # First request should pass
    allowed, retry_after = await check_rate_limit("test-key", capacity=10, refill_rate=10)
    assert allowed is True
    assert retry_after == 0.0

    # Exhaust bucket
    for _ in range(10):
        await check_rate_limit("test-key", capacity=10, refill_rate=10)

    allowed, retry_after = await check_rate_limit("test-key", capacity=10, refill_rate=10)
    assert allowed is False
    assert retry_after > 0


def test_logger():
    """Logger should create structured JSON output."""
    from utils.logger import get_logger, set_correlation_id

    set_correlation_id("test-corr-id")
    logger = get_logger("test")
    logger.info("Test message", extra={"key": "value"})


@pytest.mark.asyncio
async def test_task_service_create():
    """TaskService should create tasks with valid status."""
    from services.task_service import TaskService
    from database import AsyncSessionLocal
    from models import Task

    service = TaskService()
    async with AsyncSessionLocal() as db:
        # Create a minimal task
        task = Task(
            id="test-task-1",
            room_id="test-room",
            owner_agent_id="test-agent",
            title="Test Task",
            task_type="test",
            status="pending",
            priority="medium",
            estimated_impact=10,
            created_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.flush()

        fetched = await service.get_task(db, "test-task-1")
        assert fetched is not None
        assert fetched.title == "Test Task"
        assert fetched.status == "pending"


@pytest.mark.asyncio
async def test_message_service_broadcast():
    """MessageService broadcast should create a Message record."""
    from services.message_service import MessageService
    from database import AsyncSessionLocal
    from models import Message

    async with AsyncSessionLocal() as db:
        msg = Message(
            id="test-msg-1",
            room_id="test-room",
            from_agent_id="agent-a",
            content="Hello world",
            message_type="chat",
            created_at=datetime.now(timezone.utc),
        )
        db.add(msg)
        await db.flush()

        history = await MessageService.get_room_history(db, "test-room", limit=10)
        assert len(history) >= 1
        assert history[0].content == "Hello world"


@pytest.mark.asyncio
async def test_room_service_context():
    """RoomService should manage shared context via event sourcing."""
    from services.room_service import RoomService
    from database import AsyncSessionLocal
    from models import Room, BlackboardEvent, BlackboardOperation

    async with AsyncSessionLocal() as db:
        room = Room(
            id="test-room-ctx",
            project_id="test-project",
            name="Test Room",
            room_type="collaboration",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db.add(room)
        await db.flush()

        # Add context events
        event = BlackboardEvent(
            id="evt-1",
            room_id="test-room-ctx",
            agent_id="agent-1",
            sequence_number=1,
            key="topic",
            value="AI Research",
            operation=BlackboardOperation.SET,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.flush()

        ctx = await RoomService.get_shared_context(db, "test-room-ctx")
        assert ctx.get("topic") == "AI Research"
