"""
Tests for BaseHarness interface.
Phase 2 — AgentWorld v2.0 Harness Integration
"""

import pytest
from typing import Dict

from core.interfaces.base_harness import (
    BaseHarness,
    HarnessContext,
    HarnessResult,
    HarnessPhase,
)


class MockHarness(BaseHarness):
    """Minimal harness for testing the interface and run() loop."""

    def __init__(self, fail_verification=False):
        self._fail_verification = fail_verification
        self._plan_called = 0
        self._execute_called = 0
        self._verify_called = 0
        self._recover_called = 0
        self._checkpoints = []

    async def plan(self, context: HarnessContext) -> Dict:
        self._plan_called += 1
        return {
            "steps": [{"id": 1, "action": "test", "tool": "mock"}],
            "success_criteria": [{"criterion": "output exists", "evidence_source": "artifact"}],
            "estimated_cost": 0.01,
            "requires_approval": False,
        }

    async def execute(self, plan: Dict, context: HarnessContext) -> Dict:
        self._execute_called += 1
        return {
            "step_results": [{"step_id": 1, "success": True, "output": "done"}],
            "artifacts": ["test_output"],
            "tools_used": ["mock"],
            "cost": 0.01,
            "errors": [],
        }

    async def verify(self, plan: Dict, execution: Dict, context: HarnessContext) -> Dict:
        self._verify_called += 1
        if self._fail_verification and self._verify_called == 1:
            return {
                "passed": False,
                "criteria_results": [],
                "evidence": {},
                "failures": [{"criterion": "test", "reason": "forced failure"}],
            }
        return {
            "passed": True,
            "criteria_results": [{"criterion": "output exists", "met": True, "evidence": "test_output", "confidence": 1.0}],
            "evidence": {"artifact": "test_output"},
            "failures": [],
        }

    async def recover(self, failure: Dict, context: HarnessContext) -> HarnessContext:
        self._recover_called += 1
        # Inject failure context
        return HarnessContext(
            task=context.task + "\n[RECOVERED] Previous attempt failed.",
            agent_id=context.agent_id,
            project_id=context.project_id,
        )

    async def checkpoint(self, state: Dict, context: HarnessContext) -> str:
        cp_id = f"cp_{len(self._checkpoints)}"
        self._checkpoints.append({"id": cp_id, "state": state})
        return cp_id


# ── Interface Tests ──────────────────────────────────────────────────────

def test_base_harness_is_abstract():
    """BaseHarness cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseHarness()


def test_harness_context_defaults():
    """HarnessContext has sensible defaults."""
    ctx = HarnessContext(task="test", agent_id="a1", project_id="p1")
    assert ctx.task == "test"
    assert ctx.agent_id == "a1"
    assert ctx.project_id == "p1"
    assert ctx.memories == []
    assert ctx.living_spec == {}
    assert ctx.available_tools == []
    assert ctx.budget_remaining == 0.0
    assert ctx.requires_approval is False
    assert ctx.parent_task_id is None


def test_harness_context_to_dict():
    """HarnessContext serializes to dict."""
    ctx = HarnessContext(task="t", agent_id="a1", project_id="p1")
    d = ctx.to_dict()
    assert d["task"] == "t"
    assert d["agent_id"] == "a1"
    assert d["memories_count"] == 0


def test_harness_result_defaults():
    """HarnessResult has sensible defaults."""
    result = HarnessResult(success=True, output="ok", evidence={})
    assert result.success is True
    assert result.tools_used == []
    assert result.cost == 0.0
    assert result.phase_results == {}
    assert result.failure_reason is None
    assert result.completed_at is not None


def test_harness_phase_enum():
    """HarnessPhase has all expected phases."""
    assert HarnessPhase.PLAN.value == "plan"
    assert HarnessPhase.EXECUTE.value == "execute"
    assert HarnessPhase.VERIFY.value == "verify"
    assert HarnessPhase.RECOVER.value == "recover"
    assert HarnessPhase.COMPLETE.value == "complete"


# ── PEV Loop Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_harness_run_success():
    """Happy path: Plan → Execute → Verify passes on first try."""
    harness = MockHarness(fail_verification=False)
    ctx = HarnessContext(task="test task", agent_id="a1", project_id="p1")

    result = await harness.run(ctx, max_retries=3)

    assert result.success is True
    assert result.output == ["test_output"]
    assert result.cost == 0.01
    assert result.tools_used == ["mock"]
    assert result.failure_reason is None
    assert result.evidence["verification"]["passed"] is True

    # Each phase called exactly once
    assert harness._plan_called == 1
    assert harness._execute_called == 1
    assert harness._verify_called == 1
    assert harness._recover_called == 0

    # Checkpoints recorded
    assert len(harness._checkpoints) == 3  # plan, execute, verify


@pytest.mark.asyncio
async def test_harness_run_recover_then_success():
    """Verification fails once, recovers, then succeeds."""
    harness = MockHarness(fail_verification=True)
    ctx = HarnessContext(task="test task", agent_id="a1", project_id="p1")

    result = await harness.run(ctx, max_retries=3)

    assert result.success is True  # Succeeds on second attempt
    assert harness._plan_called == 2
    assert harness._execute_called == 2
    assert harness._verify_called == 2
    assert harness._recover_called == 1
    assert len(harness._checkpoints) == 7  # plan, exec, verify, recover ×2 + final verify


@pytest.mark.asyncio
async def test_harness_run_max_retries_exceeded():
    """Verification always fails — max_retries hit."""
    harness = MockHarness(fail_verification=True)
    harness._verify_called = 0

    # Override verify to always fail
    async def always_fail(plan, execution, context):
        harness._verify_called += 1
        return {
            "passed": False,
            "criteria_results": [],
            "evidence": {},
            "failures": [{"criterion": "test", "reason": "always fails"}],
        }

    harness.verify = always_fail

    ctx = HarnessContext(task="test task", agent_id="a1", project_id="p1")
    result = await harness.run(ctx, max_retries=2)

    assert result.success is False
    assert result.failure_reason == "MAX_RETRIES_EXCEEDED"
    assert harness._plan_called == 2  # 2 attempts
    assert harness._verify_called == 2
    assert harness._recover_called == 2  # 2 recoveries (after each failure)


@pytest.mark.asyncio
async def test_harness_run_zero_retries():
    """max_retries=1 means one shot, no retry."""
    harness = MockHarness(fail_verification=False)
    ctx = HarnessContext(task="test", agent_id="a1", project_id="p1")

    result = await harness.run(ctx, max_retries=1)

    assert result.success is True
    assert harness._plan_called == 1


@pytest.mark.asyncio
async def test_harness_run_preserves_evidence():
    """Result includes full evidence chain."""
    harness = MockHarness()
    ctx = HarnessContext(task="test", agent_id="a1", project_id="p1")

    result = await harness.run(ctx, max_retries=3)

    assert "plan" in result.evidence
    assert "execution" in result.evidence
    assert "verification" in result.evidence
    assert result.evidence["attempts"] == 1


# ── Budget Tracking ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_harness_run_tracks_cost_across_retries():
    """Total cost accumulates across retry attempts."""
    harness = MockHarness(fail_verification=True)
    ctx = HarnessContext(task="test", agent_id="a1", project_id="p1")

    result = await harness.run(ctx, max_retries=3)

    # 2 attempts × $0.01 = $0.02 total
    assert result.cost == 0.02
    assert result.success is True
