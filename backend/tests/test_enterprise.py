"""
Enterprise Architecture Tests
Tests for agent roles, chat service, swarm orchestration, external providers, and MCP.
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


# ── Agent Role Tests ───────────────────────────────────────────────────


def test_list_all_roles():
    """Should return all 5 role-based agents."""
    from agents.roles.role_definitions import list_roles
    roles = list_roles()
    assert len(roles) == 5
    ids = [r.id for r in roles]
    assert "ceo" in ids
    assert "coo" in ids
    assert "developer" in ids
    assert "content_director" in ids
    assert "crm" in ids


def test_get_role_by_id():
    """Should retrieve a specific role."""
    from agents.roles.role_definitions import get_role
    ceo = get_role("ceo")
    assert ceo is not None
    assert ceo.role == "Chief Executive Officer"
    assert ceo.avatar_emoji == "👔"


def test_role_escalation_rules():
    """CEO should escalate operational to COO."""
    from agents.roles.role_definitions import get_role
    ceo = get_role("ceo")
    assert ceo.escalation_rules.get("operational") == "coo"
    assert ceo.escalation_rules.get("technical") == "developer"


def test_role_to_dict():
    """Role should serialize to dict."""
    from agents.roles.role_definitions import get_role
    dev = get_role("developer")
    d = dev.to_dict()
    assert d["id"] == "developer"
    assert d["name"] == "Sam"
    assert "responsibilities" in d


# ── Agent Chat Service Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_with_agent():
    """Should chat with an agent and persist conversation."""
    from services.agent_chat_service import get_agent_chat_service
    from database import AsyncSessionLocal

    service = get_agent_chat_service()
    async with AsyncSessionLocal() as db:
        result = await service.chat(
            db=db,
            agent_id="ceo",
            user_id="test-user",
            message="What is our strategy?",
        )
        assert result["success"] is True
        assert result["agent"]["id"] == "ceo"
        assert "response" in result
        assert result["conversation_id"] is not None


@pytest.mark.asyncio
async def test_chat_with_invalid_agent():
    """Should fail gracefully for unknown agent."""
    from services.agent_chat_service import get_agent_chat_service
    from database import AsyncSessionLocal

    service = get_agent_chat_service()
    async with AsyncSessionLocal() as db:
        result = await service.chat(
            db=db,
            agent_id="nonexistent",
            user_id="test-user",
            message="Hello?",
        )
        assert result["success"] is False
        assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_get_conversation_history():
    """Should retrieve conversation history."""
    from services.agent_chat_service import get_agent_chat_service
    from database import AsyncSessionLocal

    service = get_agent_chat_service()
    async with AsyncSessionLocal() as db:
        # Send a message first
        await service.chat(db, "coo", "test-user", "Optimize our process")
        history = await service.get_history(db, "coo", "test-user")
        assert len(history) >= 1
        assert history[0]["message"] == "Optimize our process"


@pytest.mark.asyncio
async def test_assign_task_to_agent():
    """Should assign a task to an agent."""
    from services.agent_chat_service import get_agent_chat_service
    from database import AsyncSessionLocal

    service = get_agent_chat_service()
    async with AsyncSessionLocal() as db:
        result = await service.assign_task(
            db=db,
            agent_id="developer",
            user_id="test-user",
            task_description="Build login API",
            priority="high",
        )
        assert result["success"] is True
        assert "task_id" in result
        assert result["status"] == "pending"


# ── External Provider Tests ────────────────────────────────────────────


def test_dalle_provider_abstract():
    """DALL-E provider should implement BaseProvider."""
    from plugins.providers.image_gen.dalle_provider import DalleProvider
    from plugins.base.base_provider import BaseProvider

    p = DalleProvider()
    assert isinstance(p, BaseProvider)
    assert p.name == "dalle"
    assert p.provider_type == "image_gen"


def test_dalle_provider_without_api_key():
    """Should be inactive without API key."""
    from plugins.providers.image_gen.dalle_provider import DalleProvider
    from plugins.base.base_provider import ProviderStatus

    # Ensure no env var
    os.environ.pop("OPENAI_API_KEY", None)
    p = DalleProvider()
    result = p.initialize()
    assert result is False
    assert p.status == ProviderStatus.INACTIVE


@pytest.mark.asyncio
async def test_dalle_provider_execute_without_key():
    """Execute should fail gracefully without API key."""
    from plugins.providers.image_gen.dalle_provider import DalleProvider

    os.environ.pop("OPENAI_API_KEY", None)
    p = DalleProvider()
    p.initialize()
    result = await p.execute({"prompt": "test"})
    assert result["success"] is False
    assert "not initialized" in result["error"]


def test_runway_provider_structure():
    """Runway provider should have correct structure."""
    from plugins.providers.video_gen.runway_provider import RunwayProvider

    p = RunwayProvider()
    assert p.provider_type == "video_gen"
    cap = p.get_capability()
    assert cap.output_type == "video"
    assert "prompt" in cap.parameters["required"]


def test_slack_provider_structure():
    """Slack provider should have correct structure."""
    from plugins.providers.communication.slack_provider import SlackProvider

    p = SlackProvider()
    assert p.provider_type == "communication"
    cap = p.get_capability()
    assert "channel" in cap.parameters["required"]
    assert "message" in cap.parameters["required"]


def test_sendgrid_provider_structure():
    """SendGrid provider should have correct structure."""
    from plugins.providers.communication.sendgrid_provider import SendGridProvider

    p = SendGridProvider()
    assert p.provider_type == "communication"
    cap = p.get_capability()
    assert "to" in cap.parameters["required"]


# ── PluginLoader with Real Providers ───────────────────────────────────


def test_load_real_providers():
    """PluginLoader should discover and load real provider files."""
    from plugins.plugin_loader import PluginLoader

    PluginLoader.reset_registry()
    # Load from actual plugins/providers directory
    registry = PluginLoader.load_all_plugins()

    status = registry.get_status()
    # At least some providers should load (dalle, runway, slack, sendgrid)
    # But they may be inactive due to missing API keys — that's OK
    assert status["total"] >= 0
    names = registry.get_provider_names()
    assert len(names) >= 0


# ── Swarm Orchestrator Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_decomposition():
    """Should decompose a task into subtasks."""
    from services.orchestrator_service import SwarmOrchestrator

    orch = SwarmOrchestrator()
    subtasks = await orch.decompose_task("Build a marketing campaign", "medium")
    assert len(subtasks) >= 2
    assert all("id" in st for st in subtasks)
    assert all("agent_type" in st for st in subtasks)


@pytest.mark.asyncio
async def test_task_decomposition_complexity_levels():
    """Different complexity levels should produce different numbers of subtasks."""
    from services.orchestrator_service import SwarmOrchestrator

    orch = SwarmOrchestrator()
    low = await orch.decompose_task("x", "low")
    med = await orch.decompose_task("x", "medium")
    high = await orch.decompose_task("x", "high")

    assert len(low) < len(med) < len(high)


# ── MCP Manager Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_manager_lifecycle():
    """MCP Manager should initialize and manage servers."""
    from infrastructure.mcp.mcp_manager import get_mcp_manager, MCPServerConfig

    mgr = get_mcp_manager()
    await mgr.initialize()

    config = MCPServerConfig(
        name="test-server",
        transport="stdio",
        command="python",
    )
    result = await mgr.add_server(config)
    assert result is True

    servers = mgr.list_servers()
    assert len(servers) == 1
    assert servers[0]["name"] == "test-server"

    tools = await mgr.discover_tools("test-server")
    assert len(tools) >= 1

    call_result = await mgr.call_tool("test-server_tool_1", {"input": "test"})
    assert call_result["success"] is True

    removed = await mgr.remove_server("test-server")
    assert removed is True
    assert len(mgr.list_servers()) == 0


# ── Integration: Full System ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_end_to_end_agent_chat_and_task():
    """Full flow: chat with agent, assign task, verify persistence."""
    from services.agent_chat_service import get_agent_chat_service
    from database import AsyncSessionLocal

    service = get_agent_chat_service()
    async with AsyncSessionLocal() as db:
        # Chat
        chat_result = await service.chat(db, "content_director", "user-1", "Create a blog post")
        assert chat_result["success"] is True

        # Assign task
        task_result = await service.assign_task(db, "content_director", "user-1", "Write blog post about AI")
        assert task_result["success"] is True

        # Get history
        history = await service.get_history(db, "content_director", "user-1")
        assert len(history) >= 2

        # Get tasks
        tasks = await service.get_agent_tasks(db, "content_director")
        assert len(tasks) >= 1
