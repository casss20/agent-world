"""
Unified Command Center — Phase 8
Dashboard aggregator for all 13 agents (5 executives + 8 specialists).

Aggregates:
- Agent status (online, busy, idle)
- Active tasks per agent
- Trust scores
- Approval queue status
- Weekly cost metrics
- Recent diagnostic results
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone

from agents.roles.role_definitions import list_roles, get_role
from services.approval_queue import get_approval_queue
from services.revenue_tracker import get_revenue_tracker

logger = logging.getLogger(__name__)


@dataclass
class AgentDashboardCard:
    """Status card for a single agent."""
    agent_id: str
    name: str
    tier: str  # "executive" or "specialist"
    status: str  # "online", "busy", "idle", "offline"
    active_tasks: int
    trust_score: float
    weekly_cost: float
    pending_approvals: int
    last_active: str
    capabilities: List[str]


@dataclass
class CommandCenterDashboard:
    """Full dashboard state."""
    timestamp: str
    executives: List[AgentDashboardCard]
    specialists: List[AgentDashboardCard]
    queue_stats: Dict[str, Any]
    budget_status: Dict[str, Any]
    recent_diagnoses: List[Dict[str, Any]]
    system_health: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "executives": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "status": a.status,
                    "active_tasks": a.active_tasks,
                    "trust_score": a.trust_score,
                    "weekly_cost": a.weekly_cost,
                    "pending_approvals": a.pending_approvals,
                    "last_active": a.last_active,
                    "capabilities": a.capabilities,
                }
                for a in self.executives
            ],
            "specialists": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "status": a.status,
                    "active_tasks": a.active_tasks,
                    "trust_score": a.trust_score,
                    "weekly_cost": a.weekly_cost,
                    "pending_approvals": a.pending_approvals,
                    "last_active": a.last_active,
                    "capabilities": a.capabilities,
                }
                for a in self.specialists
            ],
            "queue_stats": self.queue_stats,
            "budget_status": self.budget_status,
            "recent_diagnoses": self.recent_diagnoses,
            "system_health": self.system_health,
            "totals": {
                "executives_online": sum(1 for a in self.executives if a.status == "online"),
                "specialists_online": sum(1 for a in self.specialists if a.status == "online"),
                "total_pending_approvals": sum(a.pending_approvals for a in self.executives + self.specialists),
                "total_weekly_cost": sum(a.weekly_cost for a in self.executives + self.specialists),
            },
        }


class CommandCenter:
    """
    Unified dashboard for monitoring all agents.
    
    Usage:
        cc = CommandCenter()
        dashboard = await cc.get_dashboard()
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_dashboard(self) -> CommandCenterDashboard:
        """Build complete dashboard state."""
        now = datetime.now(timezone.utc).isoformat()

        # Get all roles
        all_roles = list_roles()
        executives = []
        specialists = []

        # Get approval queue stats
        queue = get_approval_queue()
        queue_stats = queue.stats()
        pending_approvals = await queue.list_pending()

        # Get revenue tracker
        revenue = get_revenue_tracker()
        weekly_report = revenue.generate_weekly_report()

        # Build agent cards
        for role in all_roles:
            is_executive = role.id in ["ceo", "coo", "cmo", "cfo", "cco"]
            # Only 2 executives in current role definitions: ceo, coo
            # developer, content_director, crm are specialists/special roles
            is_executive = role.id in ["ceo", "coo"]

            # Mock status (Phase 8: integrate with actual agent heartbeat)
            agent_pending = len([a for a in pending_approvals if a.specialist_id == role.id])
            agent_cost = weekly_report.by_specialist.get(role.id, 0.0)

            card = AgentDashboardCard(
                agent_id=role.id,
                name=role.name,
                tier="executive" if is_executive else "specialist",
                status="online",  # Phase 8: real status from heartbeat
                active_tasks=0,  # Phase 8: from task service
                trust_score=0.85,  # Phase 8: from governance
                weekly_cost=agent_cost,
                pending_approvals=agent_pending,
                last_active=now,
                capabilities=role.responsibilities[:3],
            )

            if is_executive:
                executives.append(card)
            else:
                specialists.append(card)

        # Budget status
        budget_status = {
            "weekly_total": weekly_report.total_cost,
            "by_project": weekly_report.by_project,
            "threshold_hit": weekly_report.budget_threshold_hit,
        }

        return CommandCenterDashboard(
            timestamp=now,
            executives=executives,
            specialists=specialists,
            queue_stats=queue_stats,
            budget_status=budget_status,
            recent_diagnoses=[],  # Phase 8: from diagnostic store
            system_health="healthy",
        )

    async def get_agent_detail(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed view of a single agent."""
        role = get_role(agent_id)
        if not role:
            return None

        # Get pending approvals for this agent
        queue = get_approval_queue()
        pending = await queue.list_pending(specialist_id=agent_id)

        return {
            "agent_id": agent_id,
            "name": role.name,
            "role": role.role,
            "tier": "executive" if role.id in ["ceo", "coo"] else "specialist",
            "status": "online",
            "pending_approvals": [a.to_dict() for a in pending],
            "capabilities": role.responsibilities,
        }


# ── Singleton ───────────────────────────────────────────────────────────

_command_center: Optional[CommandCenter] = None


async def get_command_center() -> CommandCenter:
    global _command_center
    if _command_center is None:
        _command_center = CommandCenter()
    return _command_center
