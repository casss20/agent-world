"""
Ultron Harness — PEV Implementation on BaseHarness
Phase 3 — Two-Tier Agent Unification

UltronOrchestrator becomes a real harness:
- PLAN: Analyze message → detect specialists → build execution plan
- EXECUTE: Route to specialist templates (mock for Phase 3, real in Phase 4)
- VERIFY: Check plan completeness + governance approval status
- RECOVER: Adjust context with failure feedback for retry
- CHECKPOINT: Persist state to in-memory store (file-based in production)

This is the bridge between strategic executives and executional specialists.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from core.interfaces.base_harness import (
    BaseHarness,
    HarnessContext,
    HarnessResult,
    HarnessPhase,
)
from services.ultron_orchestrator import (
    UltronOrchestrator,
    RoutingPlan,
    SpecialistType,
)

logger = logging.getLogger(__name__)


# ── In-Memory Checkpoint Store (replace with DB in production) ───────────

class _CheckpointStore:
    """Simple in-memory checkpoint store for Phase 3."""

    def __init__(self):
        self._store: Dict[str, Dict] = {}

    def save(self, checkpoint_id: str, state: Dict) -> None:
        self._store[checkpoint_id] = {
            "state": state,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

    def load(self, checkpoint_id: str) -> Optional[Dict]:
        entry = self._store.get(checkpoint_id)
        return entry["state"] if entry else None


_checkpoint_store = _CheckpointStore()


# ── Ultron Harness ───────────────────────────────────────────────────────

class UltronHarness(BaseHarness):
    """
    PEV Harness implementation for Ultron — the executive-specialist bridge.

    PLAN:    Analyze task, detect specialists, build structured plan
    EXECUTE: Route to specialist(s) and collect outputs (mock in Phase 3)
    VERIFY:  Check plan completeness, governance approval, quality gates
    RECOVER: Inject failure feedback into context for retry
    """

    def __init__(self, orchestrator: Optional[UltronOrchestrator] = None):
        self.orchestrator = orchestrator or UltronOrchestrator()
        self.logger = logging.getLogger(self.__class__.__name__)

    # ── Phase 1: PLAN ───────────────────────────────────────────────────

    async def plan(self, context: HarnessContext) -> Dict:
        """
        Analyze the task and produce a structured execution plan.

        Uses UltronOrchestrator's keyword detection + adds harness-specific
        metadata: estimated cost, success criteria, step ordering.
        """
        from agents.roles.role_definitions import get_role

        role = get_role(context.agent_id)
        if not role:
            raise ValueError(f"Agent role not found: {context.agent_id}")

        # Use orchestrator to detect specialists
        result = await self.orchestrator.analyze_message(role, context.task, {
            "project_id": context.project_id,
            "memories": context.memories,
            "living_spec": context.living_spec,
        })

        if result.action == "direct":
            # No specialist routing needed — direct response plan
            return {
                "steps": [
                    {
                        "id": "direct",
                        "action": "respond_directly",
                        "tool": None,
                        "expected_output": "Direct answer to user",
                        "specialist": None,
                    }
                ],
                "success_criteria": [
                    {"criterion": "response_provided", "evidence_source": "output"}
                ],
                "estimated_cost": 0.0,
                "requires_approval": False,
                "plan_type": "direct",
                "reason": result.reason,
            }

        if result.action == "escalate":
            # Escalation plan — hand off to another executive
            return {
                "steps": [
                    {
                        "id": "escalate",
                        "action": "escalate_to_executive",
                        "tool": None,
                        "expected_output": f"Handoff to {result.escalate_to}",
                        "specialist": None,
                        "escalate_to": result.escalate_to,
                    }
                ],
                "success_criteria": [
                    {"criterion": "escalation_completed", "evidence_source": "handoff_record"}
                ],
                "estimated_cost": 0.0,
                "requires_approval": False,
                "plan_type": "escalate",
                "escalate_to": result.escalate_to,
                "reason": result.reason,
            }

        # Build specialist execution plan
        plan = result.routing_plan
        steps = []
        for idx, specialist in enumerate(plan.suggested_specialists, 1):
            sid = specialist.value
            # Phase 6: Merchant and Promoter require approval
            requires_approval = sid in ["merchant", "promoter"]
            steps.append({
                "id": f"step_{idx}",
                "action": f"execute_{sid}",
                "tool": None,  # Phase 4: populate from MCP registry
                "expected_output": f"{sid.title()} output",
                "specialist": sid,
                "requires_approval": requires_approval,
                "estimated_cost": 0.10 if requires_approval else 0.05,
            })

        return {
            "steps": steps,
            "success_criteria": [
                {"criterion": "all_steps_complete", "evidence_source": "step_results"},
                {"criterion": "outputs_valid", "evidence_source": "specialist_outputs"},
            ],
            "estimated_cost": plan.estimated_cost,
            "requires_approval": plan.requires_approval,
            "plan_type": "specialist",
            "detected_keywords": plan.detected_keywords,
            "confidence": plan.confidence,
            "specialists": [s.value for s in plan.suggested_specialists],
            "reason": result.reason,
        }

    # ── Phase 2: EXECUTE ────────────────────────────────────────────────

    async def execute(self, plan: Dict, context: HarnessContext) -> Dict:
        """
        Execute the plan step by step.

        Phase 3: Mock execution — returns placeholder outputs for each specialist.
        Phase 4: Will call actual specialist runtimes with MCP tools.
        """
        step_results = []
        artifacts = []
        tools_used = []
        errors = []
        total_cost = 0.0

        plan_type = plan.get("plan_type", "direct")

        if plan_type == "direct":
            # Direct response — no execution needed
            step_results.append({
                "step_id": "direct",
                "success": True,
                "output": "Direct response generated",
                "reason": plan.get("reason", ""),
            })

        elif plan_type == "escalate":
            # Escalation — record handoff
            escalate_to = plan.get("escalate_to", "unknown")
            step_results.append({
                "step_id": "escalate",
                "success": True,
                "output": f"Escalated to {escalate_to}",
                "reason": plan.get("reason", ""),
            })
            artifacts.append({"type": "escalation", "target": escalate_to})

        elif plan_type == "specialist":
            # Specialist execution — Phase 6: approval gate integration
            for step in plan.get("steps", []):
                specialist = step.get("specialist")
                if not specialist:
                    continue

                # Check if this specialist requires approval (Phase 6)
                if step.get("requires_approval", False):
                    # Submit to approval queue instead of executing
                    try:
                        from services.approval_queue import get_approval_queue
                        queue = get_approval_queue()
                        request = await queue.submit(
                            task_id=step["id"],
                            specialist_id=specialist,
                            task_description=step.get("task", f"Execute {specialist} task"),
                            reason=f"Budget-sensitive action by {specialist.title()}",
                            estimated_cost=step.get("estimated_cost", 0.10),
                            requested_by=context.agent_id or "ultron",
                            metadata={
                                "project_id": context.project_id,
                                "plan_type": plan_type,
                                "step": step,
                            },
                        )
                        step_results.append({
                            "step_id": step["id"],
                            "success": True,
                            "output": f"⏳ {specialist.title()} task submitted for approval (ID: {request.approval_id})",
                            "reason": "Awaiting human approval",
                            "approval_id": request.approval_id,
                        })
                        artifacts.append({
                            "type": "approval_request",
                            "specialist": specialist,
                            "approval_id": request.approval_id,
                        })
                    except Exception as e:
                        errors.append(f"Approval submission failed for {specialist}: {e}")
                        step_results.append({
                            "step_id": step["id"],
                            "success": False,
                            "output": f"Failed to submit approval: {str(e)}",
                            "reason": "Approval queue error",
                        })
                else:
                    # Phase 3: Mock specialist execution
                    # Phase 4: Call actual specialist agent runtime
                    mock_output = self._mock_specialist_execute(specialist, context)

                    step_results.append({
                        "step_id": step["id"],
                        "success": True,
                        "output": mock_output,
                        "reason": f"{specialist.title()} executed (mock)",
                    })
                    artifacts.append({
                        "type": "specialist_output",
                        "specialist": specialist,
                        "content": mock_output,
                    })
                    tools_used.append(f"mock_{specialist}")
                    total_cost += 0.01  # Mock cost

        return {
            "step_results": step_results,
            "artifacts": artifacts,
            "tools_used": tools_used,
            "cost": total_cost,
            "errors": errors,
        }

    # ── Phase 3: VERIFY ───────────────────────────────────────────────────

    async def verify(self, plan: Dict, execution: Dict, context: HarnessContext) -> Dict:
        """
        Verify execution against plan + success criteria.

        Phase 3 checks:
        - All planned steps have results
        - No errors in execution
        - Approval status matches plan flag
        - Cost is within budget
        """
        criteria_results = []
        all_met = True

        # Criterion 1: All steps completed
        planned_steps = len(plan.get("steps", []))
        completed_steps = len([s for s in execution.get("step_results", []) if s.get("success")])
        steps_met = planned_steps == completed_steps if planned_steps > 0 else True
        criteria_results.append({
            "criterion": "all_steps_complete",
            "met": steps_met,
            "evidence": f"{completed_steps}/{planned_steps} steps completed",
            "confidence": 1.0 if steps_met else 0.0,
        })
        if not steps_met:
            all_met = False

        # Criterion 2: No execution errors
        errors = execution.get("errors", [])
        no_errors_met = len(errors) == 0
        criteria_results.append({
            "criterion": "no_execution_errors",
            "met": no_errors_met,
            "evidence": f"{len(errors)} errors" if errors else "No errors",
            "confidence": 1.0 if no_errors_met else 0.0,
        })
        if not no_errors_met:
            all_met = False

        # Criterion 3: Budget check
        estimated_cost = plan.get("estimated_cost", 0.0)
        actual_cost = execution.get("cost", 0.0)
        budget_met = actual_cost <= context.budget_remaining if context.budget_remaining > 0 else True
        criteria_results.append({
            "criterion": "within_budget",
            "met": budget_met,
            "evidence": f"Cost: ${actual_cost:.2f} / Budget: ${context.budget_remaining:.2f}",
            "confidence": 1.0 if budget_met else 0.0,
        })
        if not budget_met:
            all_met = False

        # Criterion 4: Approval status
        requires_approval = plan.get("requires_approval", False)
        if requires_approval:
            # Phase 3: Assume approved if context.requires_approval is False
            # Phase 4: Query governance v2 approval queue
            approval_met = not context.requires_approval
            criteria_results.append({
                "criterion": "approval_obtained",
                "met": approval_met,
                "evidence": "Approval required but not yet obtained" if not approval_met else "Approval granted",
                "confidence": 1.0 if approval_met else 0.0,
            })
            if not approval_met:
                all_met = False

        return {
            "passed": all_met,
            "criteria_results": criteria_results,
            "evidence": {
                "planned_steps": planned_steps,
                "completed_steps": completed_steps,
                "errors": errors,
                "cost": actual_cost,
                "budget": context.budget_remaining,
            },
            "failures": [c for c in criteria_results if not c["met"]],
        }

    # ── Phase 4: RECOVER ────────────────────────────────────────────────

    async def recover(self, failure: Dict, context: HarnessContext) -> HarnessContext:
        """
        On verification failure, generate corrective context for retry.

        Injects failure analysis into the task description so the next
        plan attempt addresses the specific issue.
        """
        verification = failure.get("verification", {})
        failures = verification.get("failures", [])

        # Build failure feedback text
        feedback_parts = ["\n[HARNESS RECOVERY — Previous attempt failed:]"]
        for f in failures:
            feedback_parts.append(f"- {f['criterion']}: {f.get('evidence', 'Unknown failure')}")

        feedback_parts.append("Please adjust the plan to address these issues.")

        # Create updated context with failure feedback
        return HarnessContext(
            task=context.task + "\n" + "\n".join(feedback_parts),
            agent_id=context.agent_id,
            project_id=context.project_id,
            memories=context.memories + [{
                "type": "harness_failure",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "failures": failures,
                "attempt": failure.get("attempt", 0),
            }],
            living_spec=context.living_spec,
            available_tools=context.available_tools,
            budget_remaining=context.budget_remaining,
            requires_approval=context.requires_approval,
            parent_task_id=context.parent_task_id,
            metadata={
                **context.metadata,
                "recovery_attempt": failure.get("attempt", 0) + 1,
            },
        )

    # ── CHECKPOINT ────────────────────────────────────────────────────────

    async def checkpoint(self, state: Dict, context: HarnessContext) -> str:
        """Persist state to checkpoint store."""
        checkpoint_id = f"ultron_{context.agent_id}_{context.project_id}_{uuid.uuid4().hex[:8]}"
        _checkpoint_store.save(checkpoint_id, {
            "state": state,
            "context": context.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return checkpoint_id

    # ── Helpers ──────────────────────────────────────────────────────────

    def _mock_specialist_execute(self, specialist: str, context: HarnessContext) -> str:
        """Mock specialist execution for Phase 3."""
        mock_outputs = {
            "nova": f"[Nova Research] Market analysis complete for: {context.task[:50]}...",
            "pixel": f"[Pixel Design] Creative assets drafted for: {context.task[:50]}...",
            "forge": f"[Forge Listing] Product listing assembled for: {context.task[:50]}...",
            "cipher": f"[Cipher Comms] Message triage complete for: {context.task[:50]}...",
            "merchant": f"[Merchant] Publishing plan ready for: {context.task[:50]}...",
            "promoter": f"[Promoter] Ad campaign drafted for: {context.task[:50]}...",
            "growth": f"[Growth] SEO/content plan drafted for: {context.task[:50]}...",
        }
        return mock_outputs.get(specialist.lower(), f"[{specialist.title()}] Task processed.")
