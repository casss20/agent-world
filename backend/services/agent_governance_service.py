"""
Governance Service for Role-Based Agents
Applies Ledger governance, approval gates, and audit logging
to the new enterprise agents (CEO, COO, Developer, Content Director, CRM).
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum

from agents.roles.role_definitions import get_role, list_roles

logger = logging.getLogger(__name__)


class GovernanceAction(str, Enum):
    """Actions that require governance approval."""
    ASSIGN_TASK = "assign_task"
    SPAWN_SWARM = "spawn_swarm"
    ACCESS_REVENUE = "access_revenue"
    ACCESS_TRENDS = "access_trends"
    SEND_MESSAGE = "send_message"
    CREATE_CONTENT = "create_content"
    EXECUTE_WORKFLOW = "execute_workflow"
    PAUSE_AGENT = "pause_agent"
    REVOKE_AGENT = "revoke_agent"


class AgentGovernance:
    """
    Governance layer for role-based agents.
    - Approval gates for high-risk actions
    - Audit logging for all agent activities
    - Capability-based access control
    - Kill switch support
    """

    # Actions that require approval by role
    APPROVAL_REQUIRED = {
        "ceo": [],  # CEO can do everything
        "coo": [GovernanceAction.SPAWN_SWARM, GovernanceAction.REVOKE_AGENT],
        "developer": [GovernanceAction.SPAWN_SWARM, GovernanceAction.EXECUTE_WORKFLOW],
        "content_director": [GovernanceAction.ACCESS_TRENDS],  # Trend access auto-approved
        "crm": [GovernanceAction.ACCESS_REVENUE, GovernanceAction.REVOKE_AGENT],
    }

    # Risk scores per action (0-100)
    ACTION_RISK = {
        GovernanceAction.ASSIGN_TASK: 10,
        GovernanceAction.SEND_MESSAGE: 5,
        GovernanceAction.CREATE_CONTENT: 15,
        GovernanceAction.ACCESS_TRENDS: 20,
        GovernanceAction.ACCESS_REVENUE: 30,
        GovernanceAction.EXECUTE_WORKFLOW: 40,
        GovernanceAction.SPAWN_SWARM: 60,
        GovernanceAction.PAUSE_AGENT: 70,
        GovernanceAction.REVOKE_AGENT: 90,
    }

    def __init__(self):
        self._audit_log: List[Dict[str, Any]] = []
        self._approval_queue: List[Dict[str, Any]] = []
        self._kill_switches: Dict[str, bool] = {}

    # ── Approval Gates ────────────────────────────────────────────────────

    async def check_action(
        self,
        agent_id: str,
        action: GovernanceAction,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Check if an agent is allowed to perform an action.
        Returns approval status and any required escalations.
        """
        role = get_role(agent_id)
        if not role:
            return {
                "allowed": False,
                "reason": f"Unknown agent: {agent_id}",
                "requires_approval": False,
            }

        # Check kill switch
        if self._kill_switches.get(agent_id, False):
            return {
                "allowed": False,
                "reason": f"Agent {agent_id} is disabled by kill switch",
                "requires_approval": False,
            }

        risk_score = self.ACTION_RISK.get(action, 50)
        required = self.APPROVAL_REQUIRED.get(agent_id, [])

        # Check if action requires approval for this role
        needs_approval = action in required

        # Auto-approve low-risk actions
        if risk_score < 20 and not needs_approval:
            await self._audit(agent_id, action, "auto_approved", context)
            return {
                "allowed": True,
                "auto_approved": True,
                "risk_score": risk_score,
            }

        # Require approval for high-risk or restricted actions
        if needs_approval or risk_score >= 50:
            approval_id = await self._request_approval(agent_id, action, context, risk_score)
            return {
                "allowed": False,
                "requires_approval": True,
                "approval_id": approval_id,
                "risk_score": risk_score,
                "escalation_target": role.escalation_rules.get(self._get_escalation_type(action)),
                "reason": f"Action '{action}' requires approval (risk: {risk_score})",
            }

        # Medium risk — allow but log
        await self._audit(agent_id, action, "allowed_with_logging", context)
        return {
            "allowed": True,
            "auto_approved": False,
            "risk_score": risk_score,
        }

    def _get_escalation_type(self, action: GovernanceAction) -> str:
        """Determine escalation category for an action."""
        escalation_map = {
            GovernanceAction.SPAWN_SWARM: "operational",
            GovernanceAction.REVOKE_AGENT: "strategic",
            GovernanceAction.ACCESS_REVENUE: "operational",
            GovernanceAction.ACCESS_TRENDS: "strategic",
            GovernanceAction.EXECUTE_WORKFLOW: "technical",
        }
        return escalation_map.get(action, "operational")

    async def _request_approval(
        self,
        agent_id: str,
        action: GovernanceAction,
        context: Optional[Dict[str, Any]],
        risk_score: int,
    ) -> str:
        """Queue an action for approval."""
        approval_id = f"approval-{agent_id}-{action}-{len(self._approval_queue)}"
        request = {
            "id": approval_id,
            "agent_id": agent_id,
            "action": action.value,
            "risk_score": risk_score,
            "context": context or {},
            "status": "pending",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
        self._approval_queue.append(request)
        logger.info("Approval requested: %s for %s/%s", approval_id, agent_id, action)
        return approval_id

    async def approve_action(self, approval_id: str, approver: str) -> Dict[str, Any]:
        """Approve a pending action."""
        for req in self._approval_queue:
            if req["id"] == approval_id:
                req["status"] = "approved"
                req["approver"] = approver
                await self._audit(req["agent_id"], req["action"], f"approved_by_{approver}", req.get("context"))
                return {
                    "success": True,
                    "approval_id": approval_id,
                    "approved_by": approver,
                }
        return {
            "success": False,
            "error": f"Approval request {approval_id} not found",
        }

    # ── Audit Logging ──────────────────────────────────────────────────────

    async def _audit(
        self,
        agent_id: str,
        action: GovernanceAction,
        outcome: str,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Log an agent action to the audit trail."""
        entry = {
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "action": action.value,
            "outcome": outcome,
            "context": context or {},
        }
        self._audit_log.append(entry)

        # Also log to external audit if available
        try:
            from governance_init import get_governance
            gov = get_governance()
            if gov:
                await gov.audit(entry)
        except Exception:
            pass

    def get_audit_trail(self, agent_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail, optionally filtered by agent."""
        logs = self._audit_log
        if agent_id:
            logs = [log for log in logs if log["agent_id"] == agent_id]
        return logs[-limit:]

    # ── Kill Switches ──────────────────────────────────────────────────────

    def enable_kill_switch(self, agent_id: str, reason: str) -> Dict[str, Any]:
        """Disable an agent immediately."""
        self._kill_switches[agent_id] = True
        logger.critical("KILL SWITCH ACTIVATED for %s: %s", agent_id, reason)
        return {
            "success": True,
            "agent_id": agent_id,
            "status": "disabled",
            "reason": reason,
        }

    def disable_kill_switch(self, agent_id: str) -> Dict[str, Any]:
        """Re-enable an agent."""
        self._kill_switches[agent_id] = False
        logger.info("Kill switch deactivated for %s", agent_id)
        return {
            "success": True,
            "agent_id": agent_id,
            "status": "enabled",
        }

    def get_kill_switch_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get kill switch status for one or all agents."""
        if agent_id:
            return {
                "agent_id": agent_id,
                "disabled": self._kill_switches.get(agent_id, False),
            }
        return {
            "agents": {
                agent_id: disabled
                for agent_id, disabled in self._kill_switches.items()
            },
        }

    # ── Capability Checks ───────────────────────────────────────────────────

    def check_capability(self, agent_id: str, capability: str) -> bool:
        """Check if an agent has a specific capability."""
        role = get_role(agent_id)
        if not role:
            return False
        return capability in role.allowed_tools

    def get_agent_permissions(self, agent_id: str) -> Dict[str, Any]:
        """Get full permission set for an agent."""
        role = get_role(agent_id)
        if not role:
            return {"error": f"Agent {agent_id} not found"}

        return {
            "agent_id": agent_id,
            "role": role.role,
            "priority": role.priority,
            "allowed_tools": role.allowed_tools,
            "escalation_rules": role.escalation_rules,
            "can_auto_approve": self.APPROVAL_REQUIRED.get(agent_id, []),
            "kill_switch_active": self._kill_switches.get(agent_id, False),
        }


# ── Singleton ─────────────────────────────────────────────────────────────

_agent_governance: Optional[AgentGovernance] = None


def get_agent_governance() -> AgentGovernance:
    global _agent_governance
    if _agent_governance is None:
        _agent_governance = AgentGovernance()
    return _agent_governance