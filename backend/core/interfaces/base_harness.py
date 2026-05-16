from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class HarnessPhase(Enum):
    """Phase of the PEV (Plan-Execute-Verify) control loop."""
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    RECOVER = "recover"
    COMPLETE = "complete"


@dataclass
class HarnessContext:
    """
    Everything an agent needs for one execution cycle.
    Passed into every harness method.
    """
    task: str
    agent_id: str
    project_id: str
    memories: List[Dict] = field(default_factory=list)
    living_spec: Dict = field(default_factory=dict)
    available_tools: List[str] = field(default_factory=list)
    budget_remaining: float = 0.0
    requires_approval: bool = False
    parent_task_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "task": self.task,
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "memories_count": len(self.memories),
            "living_spec_keys": list(self.living_spec.keys()),
            "available_tools": self.available_tools,
            "budget_remaining": self.budget_remaining,
            "requires_approval": self.requires_approval,
            "parent_task_id": self.parent_task_id,
        }


@dataclass
class HarnessResult:
    """
    Output of one harness cycle, with evidence.
    Every result includes proof of what was done.
    """
    success: bool
    output: Any
    evidence: Dict
    tools_used: List[str] = field(default_factory=list)
    cost: float = 0.0
    phase_results: Dict = field(default_factory=dict)
    failure_reason: Optional[str] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.completed_at is None:
            self.completed_at = datetime.now(timezone.utc)


class BaseHarness(ABC):
    """
    The control layer between the API and the agent.
    Every agent execution goes through a harness.

    Pattern: Plan-Execute-Verify (PEV)
    Inspired by:
    - Augment Code's PEV pattern (Intent, 2026)
    - LangChain Deep Agents PreCompletionChecklistMiddleware
    - Anthropic's effective-harness architecture
    - MindStudio's minimal Python harness

    Usage:
        harness = PEVHarness()  # or any implementation
        result = await harness.run(context, max_retries=3)
    """

    @abstractmethod
    async def plan(self, context: HarnessContext) -> Dict:
        """
        Phase 1: Generate structured execution plan.

        Returns a dict with:
        - steps: List of step dicts with id, action, tool, expected_output
        - success_criteria: List of criterion dicts with criterion and evidence_source
        - estimated_cost: float
        - requires_approval: bool
        """
        pass

    @abstractmethod
    async def execute(self, plan: Dict, context: HarnessContext) -> Dict:
        """
        Phase 2: Run the plan step by step.

        Returns a dict with:
        - step_results: List of {step_id, success, output, reason}
        - artifacts: List of produced artifacts
        - tools_used: List of tool names called
        - cost: float (total cost of execution)
        - errors: List of failed steps
        """
        pass

    @abstractmethod
    async def verify(self, plan: Dict, execution: Dict, context: HarnessContext) -> Dict:
        """
        Phase 3: Verify execution against plan + success criteria.

        Returns a dict with:
        - passed: bool (ALL criteria must be met)
        - criteria_results: List of {criterion, met, evidence, confidence}
        - evidence: Dict of specific proof (file paths, output lines, etc.)
        - failures: List of unmet criteria with reasons
        """
        pass

    @abstractmethod
    async def recover(self, failure: Dict, context: HarnessContext) -> HarnessContext:
        """
        Phase 4: On verification failure, generate corrective context.

        Injects failure analysis into context for the next plan attempt.
        Returns: Updated HarnessContext to re-run from Plan.
        """
        pass

    @abstractmethod
    async def checkpoint(self, state: Dict, context: HarnessContext) -> str:
        """
        Persist state for resume-after-crash.

        Returns: checkpoint_id string
        """
        pass

    # ── Standard Control Loop (DO NOT OVERRIDE) ───────────────────────────

    async def run(self, context: HarnessContext, max_retries: int = 3) -> HarnessResult:
        """
        Full PEV cycle with retry on verification failure.

        This is the standard control loop. Implementations override
        plan(), execute(), verify(), recover(), checkpoint() —
        NOT this method.

        Flow:
            1. Plan → checkpoint
            2. Execute → checkpoint
            3. Verify → checkpoint
               If passed → return success
               If failed → Recover → retry (up to max_retries)
            4. Max retries → return failure

        Args:
            context: Everything the agent needs for this cycle
            max_retries: Maximum verification retries before giving up

        Returns:
            HarnessResult with success/fail, output, evidence, cost
        """
        attempts = 0
        current_context = context
        total_cost = 0.0
        all_phase_results = {}

        while attempts < max_retries:
            # ── Phase 1: Plan ────────────────────────────────────────────────
            plan = await self.plan(current_context)
            await self.checkpoint(
                {"phase": HarnessPhase.PLAN.value, "plan": plan, "attempt": attempts},
                current_context,
            )
            all_phase_results["plan"] = plan

            # ── Phase 2: Execute ───────────────────────────────────────────────
            execution = await self.execute(plan, current_context)
            await self.checkpoint(
                {"phase": HarnessPhase.EXECUTE.value, "execution": execution, "attempt": attempts},
                current_context,
            )
            all_phase_results["execution"] = execution
            total_cost += execution.get("cost", 0.0)

            # ── Phase 3: Verify ────────────────────────────────────────────────
            verification = await self.verify(plan, execution, current_context)
            await self.checkpoint(
                {"phase": HarnessPhase.VERIFY.value, "verification": verification, "attempt": attempts},
                current_context,
            )
            all_phase_results["verification"] = verification

            if verification.get("passed", False):
                # Success! Return result with full evidence chain
                return HarnessResult(
                    success=True,
                    output=execution.get("artifacts", []),
                    evidence={
                        "plan": plan,
                        "execution": execution,
                        "verification": verification,
                        "attempts": attempts + 1,
                    },
                    tools_used=execution.get("tools_used", []),
                    cost=total_cost,
                    phase_results=all_phase_results,
                )

            # ── Phase 4: Recover ───────────────────────────────────────────────
            current_context = await self.recover(
                {
                    "plan": plan,
                    "execution": execution,
                    "verification": verification,
                    "attempt": attempts,
                },
                current_context,
            )
            await self.checkpoint(
                {"phase": HarnessPhase.RECOVER.value, "context": current_context.to_dict(), "attempt": attempts},
                current_context,
            )
            attempts += 1

        # Max retries exceeded — return failure with full evidence
        return HarnessResult(
            success=False,
            output=None,
            evidence={
                "attempts": attempts,
                "last_phase_results": all_phase_results,
            },
            tools_used=[],
            cost=total_cost,
            phase_results=all_phase_results,
            failure_reason="MAX_RETRIES_EXCEEDED",
        )
