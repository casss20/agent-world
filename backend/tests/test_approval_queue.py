"""
Tests for ApprovalQueue — Phase 6
AgentWorld v2.0 — Human-in-the-Loop Approval Gates
"""

import pytest
from typing import Dict, List

from services.approval_queue import (
    ApprovalQueue,
    ApprovalRequest,
    ApprovalStatus,
    get_approval_queue,
)


# ── Instantiation ────────────────────────────────────────────────────────

def test_queue_creation():
    """ApprovalQueue can be instantiated."""
    queue = ApprovalQueue()
    assert queue is not None
    assert queue.stats()["total"] == 0


def test_queue_singleton():
    """get_approval_queue returns singleton."""
    q1 = get_approval_queue()
    q2 = get_approval_queue()
    assert q1 is q2


# ── Submit Tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_approval():
    """Submit creates an approval request."""
    queue = ApprovalQueue()
    request = await queue.submit(
        task_id="task_123",
        specialist_id="merchant",
        task_description="Publish to Etsy",
        reason="Budget-sensitive action",
        estimated_cost=0.50,
        requested_by="ultron",
    )
    assert request.approval_id.startswith("appr_")
    assert request.status == ApprovalStatus.PENDING
    assert request.specialist_id == "merchant"
    assert request.estimated_cost == 0.50


@pytest.mark.asyncio
async def test_submit_with_metadata():
    """Metadata is preserved in approval request."""
    queue = ApprovalQueue()
    request = await queue.submit(
        task_id="task_456",
        specialist_id="promoter",
        task_description="Run Facebook ad",
        reason="Ad spend",
        estimated_cost=1.00,
        requested_by="ultron",
        metadata={"project_id": "proj_etsy", "campaign_type": "lookalike"},
    )
    assert request.metadata["project_id"] == "proj_etsy"


# ── Resolve Tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_approval():
    """Resolve approves a pending request."""
    queue = ApprovalQueue()
    request = await queue.submit(
        task_id="task_123",
        specialist_id="merchant",
        task_description="Publish",
        reason="Test",
        estimated_cost=0.10,
        requested_by="ultron",
    )

    resolved = await queue.resolve(
        approval_id=request.approval_id,
        decision="approved",
        reviewer_id="anthony",
        reason="Looks good",
    )

    assert resolved is not None
    assert resolved.status == ApprovalStatus.APPROVED
    assert resolved.resolved_by == "anthony"
    assert resolved.resolution_reason == "Looks good"


@pytest.mark.asyncio
async def test_resolve_reject():
    """Resolve can reject a request."""
    queue = ApprovalQueue()
    request = await queue.submit(
        task_id="task_123",
        specialist_id="promoter",
        task_description="Expensive campaign",
        reason="Too costly",
        estimated_cost=5.00,
        requested_by="ultron",
    )

    resolved = await queue.resolve(
        approval_id=request.approval_id,
        decision="rejected",
        reviewer_id="anthony",
        reason="Over budget",
    )

    assert resolved.status == ApprovalStatus.REJECTED


@pytest.mark.asyncio
async def test_resolve_nonexistent():
    """Resolving non-existent approval returns None."""
    queue = ApprovalQueue()
    result = await queue.resolve(
        approval_id="appr_fake",
        decision="approved",
        reviewer_id="anthony",
    )
    assert result is None


@pytest.mark.asyncio
async def test_resolve_already_resolved():
    """Cannot resolve an already-resolved approval."""
    queue = ApprovalQueue()
    request = await queue.submit(
        task_id="task_123",
        specialist_id="merchant",
        task_description="Publish",
        reason="Test",
        estimated_cost=0.10,
        requested_by="ultron",
    )

    await queue.resolve(request.approval_id, "approved", "anthony")
    second = await queue.resolve(request.approval_id, "rejected", "anthony")

    assert second is None


# ── List Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_pending():
    """List returns only pending approvals."""
    queue = ApprovalQueue()
    await queue.submit(task_id="t1", specialist_id="merchant", task_description="A", reason="R", estimated_cost=0.1, requested_by="ultron")
    await queue.submit(task_id="t2", specialist_id="promoter", task_description="B", reason="R", estimated_cost=0.1, requested_by="ultron")
    req3 = await queue.submit(task_id="t3", specialist_id="growth", task_description="C", reason="R", estimated_cost=0.1, requested_by="ultron")
    await queue.resolve(req3.approval_id, "approved", "anthony")

    pending = await queue.list_pending()
    assert len(pending) == 2
    assert all(r.status == ApprovalStatus.PENDING for r in pending)


@pytest.mark.asyncio
async def test_list_pending_filtered():
    """List pending filtered by specialist_id."""
    queue = ApprovalQueue()
    await queue.submit(task_id="t1", specialist_id="merchant", task_description="A", reason="R", estimated_cost=0.1, requested_by="ultron")
    await queue.submit(task_id="t2", specialist_id="promoter", task_description="B", reason="R", estimated_cost=0.1, requested_by="ultron")

    pending = await queue.list_pending(specialist_id="merchant")
    assert len(pending) == 1
    assert pending[0].specialist_id == "merchant"


@pytest.mark.asyncio
async def test_list_all_with_status():
    """List all with status filter."""
    queue = ApprovalQueue()
    r1 = await queue.submit(task_id="t1", specialist_id="merchant", task_description="A", reason="R", estimated_cost=0.1, requested_by="ultron")
    await queue.submit(task_id="t2", specialist_id="merchant", task_description="B", reason="R", estimated_cost=0.1, requested_by="ultron")
    await queue.resolve(r1.approval_id, "approved", "anthony")

    approved = await queue.list_all(status="approved")
    assert len(approved) == 1
    assert approved[0].status == ApprovalStatus.APPROVED


# ── Get Single Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_approval():
    """Get returns a single approval by ID."""
    queue = ApprovalQueue()
    request = await queue.submit(
        task_id="task_123",
        specialist_id="merchant",
        task_description="Publish",
        reason="Test",
        estimated_cost=0.10,
        requested_by="ultron",
    )

    fetched = await queue.get(request.approval_id)
    assert fetched is not None
    assert fetched.approval_id == request.approval_id


@pytest.mark.asyncio
async def test_get_nonexistent():
    """Get returns None for non-existent approval."""
    queue = ApprovalQueue()
    result = await queue.get("appr_fake")
    assert result is None


# ── Stats Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_queue_stats():
    """Stats returns counts by status."""
    queue = ApprovalQueue()
    r1 = await queue.submit(task_id="t1", specialist_id="merchant", task_description="A", reason="R", estimated_cost=0.1, requested_by="ultron")
    await queue.submit(task_id="t2", specialist_id="promoter", task_description="B", reason="R", estimated_cost=0.1, requested_by="ultron")
    await queue.resolve(r1.approval_id, "approved", "anthony")

    stats = queue.stats()
    assert stats["total"] == 2
    assert stats["pending"] == 1
    assert stats["approved"] == 1
    assert stats["rejected"] == 0


# ── Expiration Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expire_old():
    """Old pending approvals are expired."""
    queue = ApprovalQueue(ttl_minutes=0)  # Immediate expiration
    await queue.submit(
        task_id="t1",
        specialist_id="merchant",
        task_description="Old task",
        reason="R",
        estimated_cost=0.1,
        requested_by="ultron",
    )

    expired = await queue.expire_old()
    assert expired == 1

    pending = await queue.list_pending()
    assert len(pending) == 0


# ── Serialization Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approval_to_dict():
    """ApprovalRequest serializes to dict."""
    queue = ApprovalQueue()
    request = await queue.submit(
        task_id="task_123",
        specialist_id="merchant",
        task_description="Publish",
        reason="Test",
        estimated_cost=0.10,
        requested_by="ultron",
    )

    d = request.to_dict()
    assert d["approval_id"].startswith("appr_")
    assert d["specialist_id"] == "merchant"
    assert d["status"] == "pending"
    assert d["estimated_cost"] == 0.10


# ── Integration: Harness + Approval Queue ──────────────────────────────────

@pytest.mark.asyncio
async def test_harness_approval_integration():
    """UltronHarness with requires_approval submits to queue."""
    from core.harnesses.ultron_harness import UltronHarness
    from core.interfaces.base_harness import HarnessContext

    harness = UltronHarness()
    ctx = HarnessContext(
        task="Publish to Etsy and run ads",
        agent_id="ceo",
        project_id="proj_test",
        budget_remaining=1.00,
    )

    result = await harness.run(ctx, max_retries=2)

    # Should succeed even with approvals
    assert result.success is True
    # requires_approval is in plan sub-dict
    assert result.evidence["plan"]["requires_approval"] is True

    # Check that approvals were submitted
    queue = get_approval_queue()
    pending = await queue.list_pending()
    assert len(pending) >= 1

    # Verify at least one approval is for merchant or promoter
    specialist_ids = [p.specialist_id for p in pending]
    assert "merchant" in specialist_ids or "promoter" in specialist_ids
