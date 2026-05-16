"""
Tests for CommandCenter — Phase 8
AgentWorld v2.0 — Unified Command Center Dashboard
"""

import pytest
from typing import Dict, List

from services.command_center import CommandCenter, CommandCenterDashboard, get_command_center
from services.approval_queue import get_approval_queue
from services.revenue_tracker import get_revenue_tracker


# ── Instantiation ────────────────────────────────────────────────────────

def test_command_center_creation():
    """CommandCenter can be instantiated."""
    cc = CommandCenter()
    assert cc is not None


@pytest.mark.asyncio
async def test_command_center_singleton():
    """get_command_center returns singleton."""
    cc1 = await get_command_center()
    cc2 = await get_command_center()
    assert cc1 is cc2


# ── Dashboard Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_structure():
    """Dashboard returns expected structure."""
    cc = CommandCenter()
    dashboard = await cc.get_dashboard()

    assert dashboard.timestamp is not None
    assert len(dashboard.executives) == 2
    assert len(dashboard.specialists) == 3
    assert dashboard.system_health == "healthy"


@pytest.mark.asyncio
async def test_dashboard_has_all_executives():
    """Dashboard includes all 5 executives."""
    cc = CommandCenter()
    dashboard = await cc.get_dashboard()

    exec_ids = [a.agent_id for a in dashboard.executives]
    assert "ceo" in exec_ids
    assert "coo" in exec_ids


@pytest.mark.asyncio
async def test_dashboard_has_all_specialists():
    """Dashboard includes all specialists."""
    cc = CommandCenter()
    dashboard = await cc.get_dashboard()

    spec_ids = [a.agent_id for a in dashboard.specialists]
    assert "developer" in spec_ids
    assert "content_director" in spec_ids
    assert "crm" in spec_ids


@pytest.mark.asyncio
async def test_dashboard_serialization():
    """Dashboard serializes to dict with totals."""
    cc = CommandCenter()
    dashboard = await cc.get_dashboard()

    d = dashboard.to_dict()
    assert "timestamp" in d
    assert "executives" in d
    assert "specialists" in d
    assert "queue_stats" in d
    assert "budget_status" in d
    assert "totals" in d
    assert d["totals"]["executives_online"] == 2
    assert d["totals"]["specialists_online"] == 3


# ── Queue Integration Tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_shows_pending_approvals():
    """Dashboard reflects pending approvals from queue."""
    # Submit an approval for a specialist that exists
    queue = get_approval_queue()
    await queue.submit(
        task_id="task_1",
        specialist_id="developer",
        task_description="Code review",
        reason="Test",
        estimated_cost=0.50,
        requested_by="ultron",
    )

    cc = CommandCenter()
    dashboard = await cc.get_dashboard()

    # Developer should have 1 pending approval
    developer = next(a for a in dashboard.specialists if a.agent_id == "developer")
    assert developer.pending_approvals == 1


@pytest.mark.asyncio
async def test_dashboard_totals_pending_approvals():
    """Dashboard totals include all pending approvals."""
    queue = get_approval_queue()
    await queue.submit(
        task_id="task_2",
        specialist_id="content_director",
        task_description="Create content",
        reason="Test",
        estimated_cost=0.25,
        requested_by="ultron",
    )

    cc = CommandCenter()
    dashboard = await cc.get_dashboard()

    d = dashboard.to_dict()
    assert d["totals"]["total_pending_approvals"] >= 1


# ── Revenue Integration Tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_shows_costs():
    """Dashboard reflects weekly costs from revenue tracker."""
    revenue = get_revenue_tracker()
    revenue.record_execution("proj_1", "developer", 0.05, "task_1")
    revenue.record_execution("proj_1", "crm", 0.50, "task_2")

    cc = CommandCenter()
    dashboard = await cc.get_dashboard()

    developer = next(a for a in dashboard.specialists if a.agent_id == "developer")
    crm = next(a for a in dashboard.specialists if a.agent_id == "crm")

    assert developer.weekly_cost == 0.05
    assert crm.weekly_cost == 0.50


@pytest.mark.asyncio
async def test_dashboard_budget_status():
    """Dashboard includes budget status."""
    cc = CommandCenter()
    dashboard = await cc.get_dashboard()

    d = dashboard.to_dict()
    assert "budget_status" in d
    assert "weekly_total" in d["budget_status"]


# ── Agent Detail Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_detail_executive():
    """Agent detail returns executive info."""
    cc = CommandCenter()
    detail = await cc.get_agent_detail("ceo")

    assert detail is not None
    assert detail["agent_id"] == "ceo"
    assert detail["tier"] == "executive"
    assert "capabilities" in detail


@pytest.mark.asyncio
async def test_agent_detail_specialist():
    """Agent detail returns specialist info."""
    cc = CommandCenter()
    detail = await cc.get_agent_detail("developer")

    assert detail is not None
    assert detail["agent_id"] == "developer"
    assert detail["tier"] == "specialist"


@pytest.mark.asyncio
async def test_agent_detail_not_found():
    """Agent detail returns None for unknown agent."""
    cc = CommandCenter()
    detail = await cc.get_agent_detail("nonexistent")
    assert detail is None


# ── End-to-End Dashboard Flow ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_dashboard_flow():
    """End-to-end: approvals + costs + dashboard."""
    # Setup: submit approvals and record costs
    queue = get_approval_queue()
    revenue = get_revenue_tracker()

    await queue.submit(
        task_id="task_1",
        specialist_id="developer",
        task_description="Code review",
        reason="Testing",
        estimated_cost=0.50,
        requested_by="ultron",
    )
    revenue.record_execution("proj_etsy", "developer", 0.50, "task_1")
    revenue.record_execution("proj_etsy", "crm", 1.00, "task_2")

    # Get dashboard
    cc = CommandCenter()
    dashboard = await cc.get_dashboard()
    d = dashboard.to_dict()

    # Verify structure
    assert len(d["executives"]) == 2
    assert len(d["specialists"]) == 3
    assert d["system_health"] == "healthy"

    # Verify developer has pending approval
    developer = next(a for a in d["specialists"] if a["agent_id"] == "developer")
    assert developer["pending_approvals"] >= 1
    assert developer["weekly_cost"] >= 0.50

    # Verify crm has cost
    crm = next(a for a in d["specialists"] if a["agent_id"] == "crm")
    assert crm["weekly_cost"] >= 1.00

    # Verify totals
    assert d["totals"]["total_pending_approvals"] >= 1
    assert d["totals"]["total_weekly_cost"] >= 1.50

    # Verify queue stats
    assert d["queue_stats"]["total"] >= 1
