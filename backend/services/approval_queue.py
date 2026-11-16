"""
Approval Queue — Phase 6
In-memory approval queue for human-in-the-loop gates.

Connects UltronHarness approval requests to the governance layer.
When a specialist task requires approval, it's added to this queue.
Humans review and approve/deny via API or WebSocket.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """A single approval request in the queue."""
    approval_id: str
    task_id: str
    specialist_id: str
    task_description: str
    reason: str
    estimated_cost: float
    requested_by: str  # agent_id that requested
    requested_at: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None  # human reviewer
    resolution_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "task_id": self.task_id,
            "specialist_id": self.specialist_id,
            "task_description": self.task_description,
            "reason": self.reason,
            "estimated_cost": self.estimated_cost,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "status": self.status.value,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "resolution_reason": self.resolution_reason,
            "metadata": self.metadata,
        }


class ApprovalQueue:
    """
    In-memory approval queue with TTL.
    Production: replace with Redis + persistent DB.
    """

    def __init__(self, ttl_minutes: int = 60):
        self._queue: Dict[str, ApprovalRequest] = {}
        self._ttl_minutes = ttl_minutes
        self.logger = logging.getLogger(self.__class__.__name__)

    async def submit(
        self,
        task_id: str,
        specialist_id: str,
        task_description: str,
        reason: str,
        estimated_cost: float,
        requested_by: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """Submit a new approval request."""
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        request = ApprovalRequest(
            approval_id=approval_id,
            task_id=task_id,
            specialist_id=specialist_id,
            task_description=task_description,
            reason=reason,
            estimated_cost=estimated_cost,
            requested_by=requested_by,
            requested_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self._queue[approval_id] = request
        self.logger.info(f"Approval {approval_id} submitted for {specialist_id}")
        return request

    async def resolve(
        self,
        approval_id: str,
        decision: str,  # "approved" or "rejected"
        reviewer_id: str,
        reason: Optional[str] = None,
    ) -> Optional[ApprovalRequest]:
        """Resolve an approval request."""
        request = self._queue.get(approval_id)
        if not request:
            return None

        if request.status != ApprovalStatus.PENDING:
            return None  # Already resolved

        request.status = ApprovalStatus.APPROVED if decision == "approved" else ApprovalStatus.REJECTED
        request.resolved_at = datetime.now(timezone.utc).isoformat()
        request.resolved_by = reviewer_id
        request.resolution_reason = reason or ""

        self.logger.info(f"Approval {approval_id} {request.status.value} by {reviewer_id}")
        return request

    async def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Get a single approval request."""
        return self._queue.get(approval_id)

    async def list_pending(
        self,
        specialist_id: Optional[str] = None,
        requested_by: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """List pending approvals with optional filtering."""
        pending = [
            r for r in self._queue.values()
            if r.status == ApprovalStatus.PENDING
        ]
        if specialist_id:
            pending = [r for r in pending if r.specialist_id == specialist_id]
        if requested_by:
            pending = [r for r in pending if r.requested_by == requested_by]
        return pending

    async def list_all(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[ApprovalRequest]:
        """List all approvals with optional status filter."""
        results = list(self._queue.values())
        if status:
            results = [r for r in results if r.status.value == status]
        return sorted(results, key=lambda r: r.requested_at, reverse=True)[:limit]

    async def expire_old(self) -> int:
        """Expire approvals older than TTL. Returns count expired."""
        now = datetime.now(timezone.utc)
        expired_count = 0
        for request in list(self._queue.values()):
            if request.status != ApprovalStatus.PENDING:
                continue
            requested_at = datetime.fromisoformat(request.requested_at)
            age_minutes = (now - requested_at).total_seconds() / 60
            if age_minutes > self._ttl_minutes:
                request.status = ApprovalStatus.EXPIRED
                expired_count += 1
                self.logger.info(f"Approval {request.approval_id} expired")
        return expired_count

    def stats(self) -> Dict[str, int]:
        """Queue statistics."""
        counts = {s.value: 0 for s in ApprovalStatus}
        for r in self._queue.values():
            counts[r.status.value] += 1
        return {
            "total": len(self._queue),
            **counts,
            "ttl_minutes": self._ttl_minutes,
        }


# ── Singleton ───────────────────────────────────────────────────────────

_approval_queue: Optional[ApprovalQueue] = None


def get_approval_queue() -> ApprovalQueue:
    global _approval_queue
    if _approval_queue is None:
        _approval_queue = ApprovalQueue()
    return _approval_queue
