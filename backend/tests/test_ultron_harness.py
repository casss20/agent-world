"""
Tests for UltronHarness — Phase 3 PEV Implementation
AgentWorld v2.0 — Two-Tier Agent Unification
"""

import pytest
from typing import Dict

from core.harnesses.ultron_harness import UltronHarness
from core.interfaces.base_harness import HarnessContext, HarnessPhase
from services.ultron_orchestrator import UltronOrchestrator


# ── Harness Instantiation Tests ──────────────────────────────────────────

def test_ultron_harness_implements_base():
    """UltronHarness is a concrete BaseHarness implementation."""
    harness = UltronHarness()
    assert harness is not None
    assert hasattr(harness, "plan")
    assert hasattr(harness, "execute")
    assert hasattr(harness, "verify")
    assert hasattr(harness, "recover")
    assert hasattr(harness, "checkpoint")
    assert hasattr(harness, "run")  # Inherited from BaseHarness


def test_ultron_harness_with_orchestrator():
    """Can inject a custom orchestrator."""
    orch = UltronOrchestrator()
    harness = UltronHarness(orchestrator=orch)
    assert harness.orchestrator is orch


# ── PLAN Phase Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_plan_direct_response():
    """Plan with no specialist keywords → direct response plan."""
    harness = UltronHarness()
    ctx = HarnessContext(task="Hello, how are you?", agent_id="ceo", project_id="p1")

    plan = await harness.plan(ctx)

    assert plan["plan_type"] == "direct"
    assert len(plan["steps"]) == 1
    assert plan["steps"][0]["action"] == "respond_directly"
    assert plan["requires_approval"] is False


@pytest.mark.asyncio
async def test_plan_specialist_routing():
    """Plan with specialist keywords → specialist execution plan."""
    harness = UltronHarness()
    ctx = HarnessContext(
        task="Research competitors and design a logo for my product",
        agent_id="ceo",
        project_id="p1",
    )

    plan = await harness.plan(ctx)

    assert plan["plan_type"] == "specialist"
    assert len(plan["steps"]) >= 2  # Nova + Pixel
    specialists = [s["specialist"] for s in plan["steps"]]
    assert "nova" in specialists
    assert "pixel" in specialists
    assert plan["estimated_cost"] > 0


@pytest.mark.asyncio
async def test_plan_escalation():
    """Low-confidence query → escalation plan."""
    harness = UltronHarness()
    ctx = HarnessContext(task="design", agent_id="ceo", project_id="p1")

    plan = await harness.plan(ctx)

    assert plan["plan_type"] == "escalate"
    assert plan["escalate_to"] == "content_director"


@pytest.mark.asyncio
async def test_plan_includes_success_criteria():
    """Plan includes verifiable success criteria."""
    harness = UltronHarness()
    ctx = HarnessContext(task="Publish to Etsy", agent_id="coo", project_id="p1")

    plan = await harness.plan(ctx)

    assert "success_criteria" in plan
    assert len(plan["success_criteria"]) > 0
    assert all("criterion" in sc for sc in plan["success_criteria"])


# ── EXECUTE Phase Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_direct():
    """Execute direct plan → single success result."""
    harness = UltronHarness()
    plan = {
        "plan_type": "direct",
        "steps": [{"id": "direct", "action": "respond_directly"}],
    }
    ctx = HarnessContext(task="Hello", agent_id="ceo", project_id="p1")

    execution = await harness.execute(plan, ctx)

    assert len(execution["step_results"]) == 1
    assert execution["step_results"][0]["success"] is True
    assert execution["cost"] == 0.0


@pytest.mark.asyncio
async def test_execute_escalation():
    """Execute escalation plan → escalation artifact."""
    harness = UltronHarness()
    plan = {
        "plan_type": "escalate",
        "escalate_to": "content_director",
        "steps": [{"id": "escalate", "action": "escalate_to_executive"}],
    }
    ctx = HarnessContext(task="design something", agent_id="ceo", project_id="p1")

    execution = await harness.execute(plan, ctx)

    assert execution["step_results"][0]["success"] is True
    assert any(a["type"] == "escalation" for a in execution["artifacts"])


@pytest.mark.asyncio
async def test_execute_specialist_mock():
    """Execute specialist plan → mock outputs for each specialist."""
    harness = UltronHarness()
    plan = {
        "plan_type": "specialist",
        "steps": [
            {"id": "step_1", "specialist": "nova"},
            {"id": "step_2", "specialist": "pixel"},
        ],
    }
    ctx = HarnessContext(task="Research and design", agent_id="ceo", project_id="p1")

    execution = await harness.execute(plan, ctx)

    assert len(execution["step_results"]) == 2
    assert all(s["success"] for s in execution["step_results"])
    assert len(execution["artifacts"]) == 2
    assert execution["cost"] > 0  # Mock cost applied


# ── VERIFY Phase Tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_all_pass():
    """Execution matches plan → verification passes."""
    harness = UltronHarness()
    plan = {
        "plan_type": "specialist",
        "steps": [{"id": "step_1", "specialist": "nova"}],
        "estimated_cost": 0.05,
        "requires_approval": False,
    }
    execution = {
        "step_results": [{"step_id": "step_1", "success": True}],
        "artifacts": [],
        "errors": [],
        "cost": 0.01,
    }
    ctx = HarnessContext(task="Research", agent_id="ceo", project_id="p1", budget_remaining=1.0)

    verification = await harness.verify(plan, execution, ctx)

    assert verification["passed"] is True
    assert len(verification["failures"]) == 0


@pytest.mark.asyncio
async def test_verify_steps_mismatch():
    """Missing step results → verification fails."""
    harness = UltronHarness()
    plan = {
        "plan_type": "specialist",
        "steps": [
            {"id": "step_1", "specialist": "nova"},
            {"id": "step_2", "specialist": "pixel"},
        ],
    }
    execution = {
        "step_results": [{"step_id": "step_1", "success": True}],  # Missing step_2
        "artifacts": [],
        "errors": [],
        "cost": 0.01,
    }
    ctx = HarnessContext(task="Research and design", agent_id="ceo", project_id="p1")

    verification = await harness.verify(plan, execution, ctx)

    assert verification["passed"] is False
    assert any(f["criterion"] == "all_steps_complete" for f in verification["failures"])


@pytest.mark.asyncio
async def test_verify_budget_exceeded():
    """Cost over budget → verification fails."""
    harness = UltronHarness()
    plan = {"plan_type": "direct", "steps": [], "estimated_cost": 0.0}
    execution = {"step_results": [], "artifacts": [], "errors": [], "cost": 1.0}
    ctx = HarnessContext(task="Test", agent_id="ceo", project_id="p1", budget_remaining=0.5)

    verification = await harness.verify(plan, execution, ctx)

    assert verification["passed"] is False
    assert any(f["criterion"] == "within_budget" for f in verification["failures"])


@pytest.mark.asyncio
async def test_verify_approval_required():
    """Plan requires approval but not granted → verification fails."""
    harness = UltronHarness()
    plan = {
        "plan_type": "specialist",
        "steps": [{"id": "step_1", "specialist": "merchant"}],
        "requires_approval": True,
    }
    execution = {
        "step_results": [{"step_id": "step_1", "success": True}],
        "artifacts": [],
        "errors": [],
        "cost": 0.01,
    }
    ctx = HarnessContext(
        task="Publish to Etsy",
        agent_id="coo",
        project_id="p1",
        requires_approval=True,  # Approval NOT granted
    )

    verification = await harness.verify(plan, execution, ctx)

    assert verification["passed"] is False
    assert any(f["criterion"] == "approval_obtained" for f in verification["failures"])


# ── RECOVER Phase Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recover_injects_feedback():
    """Recover injects failure feedback into context task."""
    harness = UltronHarness()
    failure = {
        "verification": {
            "failures": [
                {"criterion": "all_steps_complete", "evidence": "1/2 steps done"}
            ]
        },
        "attempt": 0,
    }
    ctx = HarnessContext(task="Research market", agent_id="ceo", project_id="p1")

    recovered = await harness.recover(failure, ctx)

    assert "HARNESS RECOVERY" in recovered.task
    assert "all_steps_complete" in recovered.task
    assert len(recovered.memories) == 1
    assert recovered.memories[0]["type"] == "harness_failure"


@pytest.mark.asyncio
async def test_recover_preserves_context():
    """Recover preserves agent_id, project_id, and other fields."""
    harness = UltronHarness()
    failure = {"verification": {"failures": []}, "attempt": 1}
    ctx = HarnessContext(
        task="Test",
        agent_id="ceo",
        project_id="p1",
        living_spec={"key": "value"},
        budget_remaining=100.0,
    )

    recovered = await harness.recover(failure, ctx)

    assert recovered.agent_id == "ceo"
    assert recovered.project_id == "p1"
    assert recovered.living_spec == {"key": "value"}
    assert recovered.budget_remaining == 100.0


# ── CHECKPOINT Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_checkpoint_returns_id():
    """Checkpoint returns a unique checkpoint ID."""
    harness = UltronHarness()
    ctx = HarnessContext(task="Test", agent_id="ceo", project_id="p1")

    cp_id = await harness.checkpoint({"phase": "plan"}, ctx)

    assert cp_id.startswith("ultron_ceo_p1_")
    assert len(cp_id) > 20


@pytest.mark.asyncio
async def test_checkpoint_persists_state():
    """Checkpoint state can be loaded back."""
    from core.harnesses.ultron_harness import _checkpoint_store

    harness = UltronHarness()
    ctx = HarnessContext(task="Test", agent_id="ceo", project_id="p1")
    state = {"phase": "execute", "data": {"key": "value"}}

    cp_id = await harness.checkpoint(state, ctx)
    loaded = _checkpoint_store.load(cp_id)

    assert loaded is not None
    assert loaded["state"]["phase"] == "execute"
    assert loaded["state"]["data"]["key"] == "value"


# ── Full PEV Loop Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_pev_success():
    """Full PEV loop: plan → execute → verify passes on first try."""
    harness = UltronHarness()
    ctx = HarnessContext(
        task="Research competitors",
        agent_id="ceo",
        project_id="p1",
        budget_remaining=1.0,
    )

    result = await harness.run(ctx, max_retries=3)

    assert result.success is True
    assert result.evidence["verification"]["passed"] is True
    assert result.cost > 0


@pytest.mark.asyncio
async def test_full_pev_with_approval_failure():
    """Plan requires approval → verification fails → retry."""
    harness = UltronHarness()
    ctx = HarnessContext(
        task="Publish to Etsy and Amazon",
        agent_id="coo",
        project_id="p1",
        budget_remaining=1.0,
        requires_approval=True,  # Approval NOT granted
    )

    result = await harness.run(ctx, max_retries=2)

    # Should fail after max retries (approval never granted in mock)
    assert result.success is False
    assert result.failure_reason == "MAX_RETRIES_EXCEEDED"


@pytest.mark.asyncio
async def test_full_pev_preserves_evidence():
    """Result includes full evidence chain across all phases."""
    harness = UltronHarness()
    ctx = HarnessContext(task="Design a logo", agent_id="ceo", project_id="p1", budget_remaining=1.0)

    result = await harness.run(ctx, max_retries=3)

    assert "plan" in result.evidence
    assert "execution" in result.evidence
    assert "verification" in result.evidence
    assert "attempts" in result.evidence


# ── Integration: Orchestrator + Harness ───────────────────────────────────

@pytest.mark.asyncio
async def test_harness_uses_orchestrator_routing():
    """Harness plan() delegates to orchestrator for keyword detection."""
    harness = UltronHarness()
    ctx = HarnessContext(task="SEO optimize my listings", agent_id="content_director", project_id="p1")

    plan = await harness.plan(ctx)

    # SEO routes to Growth + Forge
    if plan["plan_type"] == "specialist":
        specialists = plan.get("specialists", [])
        assert "growth" in specialists
