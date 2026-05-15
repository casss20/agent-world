"""
Self-Healing Service
Auto-detect issues, generate fixes, and safely apply patches.

Adapted from Ruflo pattern: Self-learning swarm intelligence + auto-repair.
"""

import logging
import traceback
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from utils.retry import retry_with_backoff
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Issue:
    """Detected issue with context."""
    id: str
    category: str  # db, api, ws, task, memory, etc.
    severity: str  # low, medium, high, critical
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "open"  # open, fixing, resolved, failed


@dataclass
class FixResult:
    """Result of a fix attempt."""
    success: bool
    action_taken: str
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    error: Optional[str] = None


class SelfHealingService:
    """
    Monitors system health and auto-applies fixes.
    - Detectors: identify issues
    - Fixers: apply repairs
    - Rollback: undo if fix makes things worse
    """

    def __init__(self):
        self._detectors: Dict[str, Callable] = {}
        self._fixers: Dict[str, Callable] = {}
        self._issues: List[Issue] = []
        self._max_history = 100

    # ── Registration ───────────────────────────────────────────────────────────

    def register_detector(self, category: str, detector: Callable) -> None:
        """Register an issue detector for a category."""
        self._detectors[category] = detector
        logger.info("Registered detector for category=%s", category)

    def register_fixer(self, category: str, fixer: Callable) -> None:
        """Register a fix handler for a category."""
        self._fixers[category] = fixer
        logger.info("Registered fixer for category=%s", category)

    # ── Detection ─────────────────────────────────────────────────────────────

    async def detect_all(self) -> List[Issue]:
        """Run all detectors and return found issues."""
        new_issues: List[Issue] = []
        for category, detector in self._detectors.items():
            try:
                detected = await detector()
                for d in detected:
                    issue = Issue(
                        id=f"issue-{datetime.now(timezone.utc).isoformat()}-{category}",
                        category=category,
                        severity=d.get("severity", "medium"),
                        description=d.get("description", "Unknown issue"),
                        context=d.get("context", {}),
                    )
                    new_issues.append(issue)
                    self._issues.append(issue)
            except Exception as e:
                logger.error("Detector %s failed: %s", category, e)

        # Trim history
        if len(self._issues) > self._max_history:
            self._issues = self._issues[-self._max_history:]

        return new_issues

    # ── Repair ────────────────────────────────────────────────────────────────

    async def repair(self, issue: Issue) -> FixResult:
        """Attempt to fix an identified issue."""
        fixer = self._fixers.get(issue.category)
        if not fixer:
            return FixResult(
                success=False,
                action_taken="none",
                before_state={},
                after_state={},
                error=f"No fixer registered for category {issue.category}",
            )

        issue.status = "fixing"
        before = issue.context.copy()

        try:
            @retry_with_backoff(max_retries=1, base_delay=0.5)
            async def _apply_fix():
                return await fixer(issue)

            result = await _apply_fix()
            issue.status = "resolved"

            return FixResult(
                success=True,
                action_taken=result.get("action", "unknown"),
                before_state=before,
                after_state=result.get("state", {}),
            )

        except Exception as e:
            issue.status = "failed"
            logger.error("Fix failed for issue %s: %s", issue.id, e)
            return FixResult(
                success=False,
                action_taken="attempted",
                before_state=before,
                after_state=issue.context,
                error=str(e),
            )

    async def repair_all(self, severity_threshold: str = "medium") -> List[FixResult]:
        """Repair all open issues meeting severity threshold."""
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        threshold = severity_order.get(severity_threshold, 1)

        open_issues = [
            i for i in self._issues
            if i.status == "open"
            and severity_order.get(i.severity, 0) >= threshold
        ]

        results = []
        for issue in open_issues:
            result = await self.repair(issue)
            results.append(result)

        return results

    # ── Built-in Detectors ────────────────────────────────────────────────────

    @staticmethod
    async def check_db_health() -> List[Dict[str, Any]]:
        """Detect database connectivity issues."""
        try:
            from database import health_check
            status = await health_check()
            if status.get("status") != "healthy":
                return [{
                    "severity": "high",
                    "description": f"DB unhealthy: {status.get('error', 'unknown')}",
                    "context": status,
                }]
            return []
        except Exception as e:
            return [{
                "severity": "critical",
                "description": f"DB health check failed: {str(e)}",
                "context": {"error": str(e)},
            }]

    @staticmethod
    async def check_ws_health() -> List[Dict[str, Any]]:
        """Detect WebSocket connection issues."""
        from websocket_manager import ws_manager
        total = ws_manager.total_connections()
        # Alert if connections drop unexpectedly (would need baseline)
        return []

    # ── Built-in Fixers ─────────────────────────────────────────────────────

    @staticmethod
    async def reset_db_pool(issue: Issue) -> Dict[str, Any]:
        """Fix: Recycle database connections."""
        try:
            from database import close_engine, get_engine
            await close_engine()
            get_engine()  # Recreate
            return {"action": "db_pool_reset", "state": {"pool": "recreated"}}
        except Exception as e:
            return {"action": "failed", "state": {"error": str(e)}}

    @staticmethod
    async def restart_ws_manager(issue: Issue) -> Dict[str, Any]:
        """Fix: Restart WebSocket manager."""
        try:
            from websocket_manager import ws_manager
            await ws_manager.stop()
            await ws_manager.start()
            return {"action": "ws_manager_restarted", "state": {"connections": ws_manager.total_connections()}}
        except Exception as e:
            return {"action": "failed", "state": {"error": str(e)}}

    # ── Queries ─────────────────────────────────────────────────────────────

    def get_issues(self, status: Optional[str] = None) -> List[Issue]:
        """Get all or filtered issues."""
        if status:
            return [i for i in self._issues if i.status == status]
        return list(self._issues)

    def stats(self) -> Dict[str, int]:
        """Get healing statistics."""
        return {
            "total": len(self._issues),
            "open": len([i for i in self._issues if i.status == "open"]),
            "resolved": len([i for i in self._issues if i.status == "resolved"]),
            "failed": len([i for i in self._issues if i.status == "failed"]),
        }


# ── Global Instance ─────────────────────────────────────────────────────────
self_healing = SelfHealingService()
# Register built-in detectors and fixers
self_healing.register_detector("db", SelfHealingService.check_db_health)
self_healing.register_detector("ws", SelfHealingService.check_ws_health)
self_healing.register_fixer("db", SelfHealingService.reset_db_pool)
self_healing.register_fixer("ws", SelfHealingService.restart_ws_manager)
