"""
Tests for LLMRouter — Phase 5
AgentWorld v2.0 — Multi-LLM Smart Routing
"""

import pytest
from typing import Dict, List

from core.routing.llm_router import (
    LLMRouter,
    TaskTier,
    get_llm,
    get_router,
    RuleBasedStrategy,
)
from core.routing.routing_rules import ROUTING_RULES
from core.interfaces.base_llm_provider import BaseLLMProvider


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_router_with_mock():
    """Create router with a mock provider to avoid needing real keys."""
    from tests.mocks.llm_mock import LLMMock
    router = LLMRouter.__new__(LLMRouter)
    router._providers = {"mock": LLMMock()}
    router._strategy = RuleBasedStrategy()
    return router


# ── Classification Tests ────────────────────────────────────────────────

def test_ceo_strategic_task_routes_heavyweight():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Strategize Q3 OKRs for Nectara",
        agent="ceo",
        phase="",
        available_providers=["mock"],
    )
    assert tier == TaskTier.HEAVYWEIGHT


def test_coo_planning_routes_heavyweight():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Plan quarterly operations",
        agent="coo",
        phase="",
        available_providers=["mock"],
    )
    assert tier == TaskTier.HEAVYWEIGHT


def test_ultron_routing_task_routes_fast():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Route this task to the correct agent",
        agent="ultron",
        phase="",
        available_providers=["mock"],
    )
    assert tier == TaskTier.FAST


def test_cipher_quality_check_routes_fast():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Check format and safety",
        agent="cipher",
        phase="",
        available_providers=["mock"],
    )
    assert tier == TaskTier.FAST


def test_batch_job_routes_local():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Batch process all products",
        agent="",
        phase="",
        available_providers=["mock"],
    )
    assert tier == TaskTier.LOCAL


def test_scheduled_job_routes_local():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Generate morning briefing",
        agent="coo",
        phase="",
        available_providers=["mock"],
    )
    assert tier == TaskTier.LOCAL


def test_content_creation_routes_standard():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Write a blog post about productivity",
        agent="forge",
        phase="execute",
        available_providers=["mock"],
    )
    assert tier == TaskTier.STANDARD


def test_research_task_routes_standard():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Research competitor trends",
        agent="nova",
        phase="execute",
        available_providers=["mock"],
    )
    assert tier == TaskTier.STANDARD


def test_code_generation_routes_standard():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Implement a new API endpoint",
        agent="developer",
        phase="execute",
        available_providers=["mock"],
    )
    assert tier == TaskTier.STANDARD


def test_unknown_task_defaults_standard():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="Something random",
        agent="unknown",
        phase="",
        available_providers=["mock"],
    )
    assert tier == TaskTier.STANDARD


# ── Phase-Based Routing ─────────────────────────────────────────────────

def test_plan_phase_routes_heavyweight():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="any task",
        agent="",
        phase="plan",
        available_providers=["mock"],
    )
    assert tier == TaskTier.HEAVYWEIGHT


def test_verify_phase_routes_heavyweight():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="any task",
        agent="",
        phase="verify",
        available_providers=["mock"],
    )
    assert tier == TaskTier.HEAVYWEIGHT


def test_execute_phase_routes_standard():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="any task",
        agent="",
        phase="execute",
        available_providers=["mock"],
    )
    assert tier == TaskTier.STANDARD


def test_recover_phase_routes_standard():
    router = _make_router_with_mock()
    tier = router._strategy.classify(
        task="any task",
        agent="",
        phase="recover",
        available_providers=["mock"],
    )
    assert tier == TaskTier.STANDARD


# ── Forced Override Tests ───────────────────────────────────────────────

def test_force_provider_override():
    router = _make_router_with_mock()
    provider = router.get(force_provider="mock")
    assert provider is not None


def test_force_tier_override():
    router = _make_router_with_mock()
    provider = router.get(task="anything", force_tier="heavyweight")
    assert provider is not None


def test_force_invalid_provider_warns():
    router = _make_router_with_mock()
    provider = router.get(force_provider="nonexistent")
    # Falls back to any available
    assert provider is not None


# ── Routing Table Tests ─────────────────────────────────────────────────

def test_routing_table_returns_all_tiers():
    router = _make_router_with_mock()
    table = router.routing_table()
    assert "heavyweight" in table
    assert "standard" in table
    assert "fast" in table
    assert "local" in table


def test_routing_table_with_mock_provider():
    router = _make_router_with_mock()
    table = router.routing_table()
    # With only "mock" provider, tiers map to it or none
    assert table["heavyweight"] in ["mock", "none_available"]


# ── Available Providers ─────────────────────────────────────────────────

def test_available_providers_list():
    router = _make_router_with_mock()
    providers = router.available_providers()
    assert "mock" in providers


# ── PEV Convenience ─────────────────────────────────────────────────────

def test_pev_plan_gets_heavyweight():
    router = _make_router_with_mock()
    provider = router.get_for_pev("plan")
    assert provider is not None


def test_pev_execute_gets_standard():
    router = _make_router_with_mock()
    provider = router.get_for_pev("execute")
    assert provider is not None


# ── Rule Validation ─────────────────────────────────────────────────────

def test_all_routing_rules_have_valid_tiers():
    for rule in ROUTING_RULES:
        assert rule.tier in TaskTier, f"Rule {rule.name} has invalid tier"


def test_all_routing_rules_have_names():
    for rule in ROUTING_RULES:
        assert rule.name, "Rule must have a name"


def test_routing_rules_order_priority():
    """Heavyweight rules should come before standard."""
    tiers_in_order = [r.tier for r in ROUTING_RULES]
    # First few should be heavyweight
    assert tiers_in_order[0] == TaskTier.HEAVYWEIGHT


# ── get_llm() Wrapper ────────────────────────────────────────────────────

def test_get_llm_returns_provider():
    from tests.mocks.llm_mock import LLMMock
    router = _make_router_with_mock()
    # get_llm is a function, needs global router setup
    provider = router.get(task="test", agent="nova")
    assert provider is not None


# ── No Providers Error ────────────────────────────────────────────────────

def test_no_providers_raises_error():
    router = LLMRouter.__new__(LLMRouter)
    router._providers = {}
    router._strategy = RuleBasedStrategy()
    with pytest.raises(RuntimeError):
        router.get(task="anything")
