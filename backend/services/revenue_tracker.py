"""
Revenue Feedback Loop — Phase 7
Weekly cost aggregation + budget threshold alerts.

Tracks:
- Cost per specialist per week
- Total project burn rate
- Budget threshold warnings (75%, 90%, 100%)
- Auto-throttle when budget exhausted
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


@dataclass
class WeeklyCostReport:
    """Cost report for a single week."""
    week_start: str
    week_end: str
    total_cost: float
    by_specialist: Dict[str, float]
    by_project: Dict[str, float]
    approval_count: int
    execution_count: int
    budget_threshold_hit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "week_start": self.week_start,
            "week_end": self.week_end,
            "total_cost": round(self.total_cost, 4),
            "by_specialist": {k: round(v, 4) for k, v in self.by_specialist.items()},
            "by_project": {k: round(v, 4) for k, v in self.by_project.items()},
            "approval_count": self.approval_count,
            "execution_count": self.execution_count,
            "budget_threshold_hit": self.budget_threshold_hit,
        }


class RevenueTracker:
    """
    Tracks costs and provides budget alerts.
    
    In production:
    - Replace in-memory store with DB table
    - Run via cron job weekly
    - Integrate with billing system
    """

    BUDGET_THRESHOLDS = [0.75, 0.90, 1.0]

    def __init__(self):
        self._executions: List[Dict[str, Any]] = []
        self._approvals: List[Dict[str, Any]] = []
        self._budgets: Dict[str, float] = {}  # project_id -> budget
        self.logger = logging.getLogger(self.__class__.__name__)

    def record_execution(
        self,
        project_id: str,
        specialist_id: str,
        cost: float,
        task_id: str,
        approved: bool = True,
    ) -> None:
        """Record a single execution cost."""
        self._executions.append({
            "project_id": project_id,
            "specialist_id": specialist_id,
            "cost": cost,
            "task_id": task_id,
            "approved": approved,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_approval(
        self,
        approval_id: str,
        project_id: str,
        specialist_id: str,
        estimated_cost: float,
        status: str,
    ) -> None:
        """Record an approval event."""
        self._approvals.append({
            "approval_id": approval_id,
            "project_id": project_id,
            "specialist_id": specialist_id,
            "estimated_cost": estimated_cost,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def set_budget(self, project_id: str, budget: float) -> None:
        """Set budget for a project."""
        self._budgets[project_id] = budget

    def generate_weekly_report(
        self,
        project_id: Optional[str] = None,
        week_offset: int = 0,
    ) -> WeeklyCostReport:
        """Generate cost report for a given week."""
        now = datetime.now(timezone.utc)
        # Calculate week boundaries (Monday-starting)
        days_since_monday = now.weekday()
        week_start = now - timedelta(days=days_since_monday + (week_offset * 7))
        week_end = week_start + timedelta(days=7)

        # Filter executions in week
        week_execs = [
            e for e in self._executions
            if self._in_week(e["timestamp"], week_start, week_end)
            and (project_id is None or e["project_id"] == project_id)
        ]

        # Calculate totals
        total_cost = sum(e["cost"] for e in week_execs)
        by_specialist: Dict[str, float] = {}
        by_project: Dict[str, float] = {}

        for e in week_execs:
            sid = e["specialist_id"]
            pid = e["project_id"]
            by_specialist[sid] = by_specialist.get(sid, 0.0) + e["cost"]
            by_project[pid] = by_project.get(pid, 0.0) + e["cost"]

        # Count approvals
        week_approvals = [
            a for a in self._approvals
            if self._in_week(a["timestamp"], week_start, week_end)
            and (project_id is None or a["project_id"] == project_id)
        ]

        # Check budget thresholds
        threshold_hit = None
        if project_id and project_id in self._budgets:
            budget = self._budgets[project_id]
            if budget > 0:
                ratio = total_cost / budget
                for t in sorted(self.BUDGET_THRESHOLDS, reverse=True):
                    if ratio >= t:
                        threshold_hit = f"{int(t*100)}%"
                        break

        return WeeklyCostReport(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            total_cost=total_cost,
            by_specialist=by_specialist,
            by_project=by_project,
            approval_count=len(week_approvals),
            execution_count=len(week_execs),
            budget_threshold_hit=threshold_hit,
        )

    def check_budget(self, project_id: str, estimated_cost: float) -> Dict[str, Any]:
        """Check if a proposed cost would exceed budget."""
        if project_id not in self._budgets:
            return {"allowed": True, "reason": "No budget set"}

        budget = self._budgets[project_id]
        current = sum(
            e["cost"] for e in self._executions
            if e["project_id"] == project_id
        )
        projected = current + estimated_cost

        if projected > budget:
            return {
                "allowed": False,
                "reason": f"Would exceed budget: ${projected:.2f} / ${budget:.2f}",
                "current_spend": current,
                "budget": budget,
                "remaining": budget - current,
            }

        # Warning at 90%
        if projected / budget >= 0.9:
            return {
                "allowed": True,
                "warning": f"Budget 90% consumed: ${projected:.2f} / ${budget:.2f}",
                "current_spend": current,
                "budget": budget,
                "remaining": budget - current,
            }

        return {
            "allowed": True,
            "current_spend": current,
            "budget": budget,
            "remaining": budget - current,
        }

    def get_recommendations(self, project_id: str) -> List[str]:
        """Get cost optimization recommendations."""
        recs = []
        report = self.generate_weekly_report(project_id=project_id)

        if not report.by_specialist:
            return recs

        # Find most expensive specialist
        most_expensive = max(report.by_specialist.items(), key=lambda x: x[1])
        if most_expensive[1] > 1.0:
            recs.append(
                f"💡 {most_expensive[0].title()} is your highest cost ({most_expensive[1]:.2f}). "
                f"Consider reviewing usage patterns."
            )

        # Check approval ratio
        if report.approval_count > 0:
            ratio = report.execution_count / report.approval_count
            if ratio < 0.5:
                recs.append(
                    f"⚠️ Low approval-to-execution ratio ({ratio:.1f}). "
                    f"Many tasks pending approval."
                )

        # Budget threshold
        if report.budget_threshold_hit:
            recs.append(
                f"🚨 Budget threshold hit: {report.budget_threshold_hit}. "
                f"Consider pausing non-essential tasks."
            )

        return recs

    def _in_week(self, timestamp: str, week_start: datetime, week_end: datetime) -> bool:
        """Check if timestamp falls within week."""
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return week_start <= ts < week_end
        except (ValueError, AttributeError):
            return False


# ── Singleton ───────────────────────────────────────────────────────────

_revenue_tracker: Optional[RevenueTracker] = None


def get_revenue_tracker() -> RevenueTracker:
    global _revenue_tracker
    if _revenue_tracker is None:
        _revenue_tracker = RevenueTracker()
    return _revenue_tracker
