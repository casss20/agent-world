"""
Tests for Ultron Orchestrator — Phase 2 Bridge
AgentWorld v2.0 — Two-Tier Agent Unification
"""

import pytest
import os
from typing import Dict

from services.ultron_orchestrator import (
    UltronOrchestrator,
    RoutingPlan,
    OrchestratorResult,
    SpecialistType,
    _harness_enabled_agents,
)
from agents.roles.role_definitions import get_role


# ── Harness Flag Tests ─────────────────────────────────────────────────

def test_harness_enabled_all_by_default():
    """Without env var, all executives are harness-enabled."""
    # Ensure env var is not set
    old_env = os.environ.pop("HARNESS_ENABLED_AGENTS", None)
    try:
        agents = _harness_enabled_agents()
        assert "ceo" in agents
        assert "coo" in agents
        assert "developer" in agents
        assert "content_director" in agents
        assert "crm" in agents
    finally:
        if old_env is not None:
            os.environ["HARNESS_ENABLED_AGENTS"] = old_env


def test_harness_enabled_specific():
    """HARNESS_ENABLED_AGENTS=ceo,coo enables only those."""
    old_env = os.environ.get("HARNESS_ENABLED_AGENTS")
    os.environ["HARNESS_ENABLED_AGENTS"] = "ceo,coo"
    try:
        agents = _harness_enabled_agents()
        assert "ceo" in agents
        assert "coo" in agents
        assert "developer" not in agents
    finally:
        if old_env is not None:
            os.environ["HARNESS_ENABLED_AGENTS"] = old_env
        else:
            os.environ.pop("HARNESS_ENABLED_AGENTS", None)


# ── Routing Detection Tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detect_nova_keywords():
    """Research keywords route to Nova."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("ceo"),
        "Please research the market for children's books",
    )
    assert result.action == "route"
    assert result.routing_plan is not None
    assert SpecialistType.NOVA in result.routing_plan.suggested_specialists
    assert result.routing_plan.confidence > 0


@pytest.mark.asyncio
async def test_detect_pixel_keywords():
    """Design keywords route to Pixel."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("content_director"),
        "Create a logo and thumbnail for the product",
    )
    assert result.action == "route"
    assert SpecialistType.PIXEL in result.routing_plan.suggested_specialists


@pytest.mark.asyncio
async def test_detect_merchant_keywords():
    """Publishing keywords route to Merchant."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("coo"),
        "Publish the listing to Etsy and Amazon",
    )
    assert result.action == "route"
    assert SpecialistType.MERCHANT in result.routing_plan.suggested_specialists
    assert result.routing_plan.requires_approval is True  # Merchant needs approval


@pytest.mark.asyncio
async def test_detect_promoter_keywords():
    """Ad keywords route to Promoter."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("ceo"),
        "Launch a Facebook ad campaign with $50 budget",
    )
    assert result.action == "route"
    assert SpecialistType.PROMOTER in result.routing_plan.suggested_specialists
    assert result.routing_plan.requires_approval is True  # Promoter needs approval


@pytest.mark.asyncio
async def test_detect_growth_keywords():
    """SEO keywords route to Growth."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("content_director"),
        "Optimize our blog SEO and build backlinks",
    )
    assert SpecialistType.GROWTH in result.routing_plan.suggested_specialists


@pytest.mark.asyncio
async def test_detect_multi_specialist():
    """Complex queries route to multiple specialists."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("ceo"),
        "Research competitors, design a logo, and publish to Etsy",
    )
    assert result.action == "route"
    specialists = result.routing_plan.suggested_specialists
    assert SpecialistType.NOVA in specialists
    assert SpecialistType.PIXEL in specialists
    assert SpecialistType.MERCHANT in specialists
    assert result.routing_plan.confidence > 0.5


@pytest.mark.asyncio
async def test_no_keywords_direct():
    """Messages with no specialist keywords get direct response."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("ceo"),
        "Hello, how are you today?",
    )
    assert result.action == "direct"
    assert result.routing_plan is None


# ── Escalation Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_escalation_low_confidence():
    """Low confidence routing escalates to appropriate executive."""
    ultron = UltronOrchestrator()
    # CEO asking about design → low confidence should escalate to Content Director
    result = await ultron.analyze_message(
        get_role("ceo"),
        "design",  # Single keyword = low confidence
    )
    # Single keyword has confidence 0.5, which is below 0.7 threshold
    assert result.action == "escalate"
    assert result.escalate_to == "content_director"


@pytest.mark.asyncio
async def test_no_escalation_high_confidence():
    """High confidence stays with current executive."""
    ultron = UltronOrchestrator()
    # CEO asking about research + ads = high confidence
    result = await ultron.analyze_message(
        get_role("ceo"),
        "Research market and launch ad campaign immediately",
    )
    assert result.action == "route"
    assert result.routing_plan.confidence >= 0.7


# ── Approval & Cost Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_merchant_requires_approval():
    """Merchant actions require approval."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("coo"),
        "Publish product to Amazon and sync inventory",
    )
    assert result.action == "route"
    assert result.routing_plan.requires_approval is True


@pytest.mark.asyncio
async def test_nova_no_approval():
    """Research tasks don't require approval."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("ceo"),
        "Research competitor pricing",
    )
    assert result.action == "route"
    assert result.routing_plan.requires_approval is False


@pytest.mark.asyncio
async def test_cost_estimation():
    """Cost is estimated based on specialists."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("ceo"),
        "Design a logo",  # Pixel only = expensive
    )
    assert result.routing_plan.estimated_cost > 0.3  # Pixel is $0.50


# ── Formatting Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_format_routing_response():
    """Routing response is formatted for user display."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("ceo"),
        "Research market and design a logo",
    )
    formatted = await ultron.format_routing_response(result, get_role("ceo"))
    assert "Ultron Routing Plan" in formatted
    assert "Nova" in formatted
    assert "Pixel" in formatted


@pytest.mark.asyncio
async def test_format_escalation_response():
    """Escalation response mentions target executive."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("ceo"),
        "design",  # Low confidence triggers escalation
    )
    formatted = await ultron.format_routing_response(result, get_role("ceo"))
    assert "Escalating" in formatted
    assert "Taylor" in formatted  # Content Director's name


@pytest.mark.asyncio
async def test_format_direct_response():
    """Direct action returns empty string (fallback to placeholder)."""
    ultron = UltronOrchestrator()
    result = await ultron.analyze_message(
        get_role("ceo"),
        "Hello",
    )
    formatted = await ultron.format_routing_response(result, get_role("ceo"))
    assert formatted == ""


# ── Disabled Harness Tests ────────────────────────────────────────────

def test_disabled_agent_gets_direct():
    """Agents not in HARNESS_ENABLED_AGENTS get direct response."""
    old_env = os.environ.get("HARNESS_ENABLED_AGENTS")
    os.environ["HARNESS_ENABLED_AGENTS"] = "ceo"  # Only CEO enabled
    try:
        ultron = UltronOrchestrator()
        # Run sync check (the analyze_message is async, but the enabled check is sync)
        # We test via the internal method
        import asyncio
        result = asyncio.run(ultron.analyze_message(
            get_role("developer"),
            "Design a logo",
        ))
        assert result.action == "direct"
        assert "not enabled" in result.reason
    finally:
        if old_env is not None:
            os.environ["HARNESS_ENABLED_AGENTS"] = old_env
        else:
            os.environ.pop("HARNESS_ENABLED_AGENTS", None)


# ── Integration with Agent Chat Service ─────────────────────────────────

@pytest.mark.asyncio
async def test_chat_service_routes_through_ultron():
    """AgentChatService.chat() now calls Ultron for harness-enabled agents."""
    from services.agent_chat_service import AgentChatService
    
    service = AgentChatService()
    
    # Test with a harness-enabled agent (ceo by default)
    # We can't test the full async DB flow here, but we can test _generate_response
    response = await service._generate_response(
        get_role("ceo"),
        "Research market competitors and design a logo",
        None,
    )
    assert "Ultron" in response or "responsibilities" in response


@pytest.mark.asyncio
async def test_chat_service_fallback_on_error():
    """If Ultron fails, falls back to placeholder."""
    from services.agent_chat_service import AgentChatService
    
    service = AgentChatService()
    
    # Even with nonsense input, should not crash
    response = await service._generate_response(
        get_role("ceo"),
        "",
        None,
    )
    assert response is not None
    assert len(response) > 0
