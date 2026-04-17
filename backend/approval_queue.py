"""
Approval Queue — Agent World
Human-in-the-loop for risky agent actions.
"""

import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    """A request waiting for human approval."""
    id: str
    action: str
    resource: str
    risk: str
    args: Dict
    created_at: str
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    reason: Optional[str] = None  # for denials


class ApprovalQueue:
    """
    In-memory approval queue for HARD governance actions.
    
    In production: replace with Redis-backed queue for persistence.
    """
    
    def __init__(self):
        self._queue: Dict[str, ApprovalRequest] = {}
        self._waiters: Dict[str, asyncio.Event] = {}
        self._hooks: List[Callable[[ApprovalRequest], Awaitable[None]]] = []
    
    async def push(self, req: ApprovalRequest) -> None:
        """Add a request to the queue."""
        self._queue[req.id] = req
        self._waiters[req.id] = asyncio.Event()
        logger.info(f"[ApprovalQueue] New request: {req.action} on {req.resource} (risk: {req.risk})")
        
        # Notify hooks (e.g., send to dashboard, Slack, email)
        for hook in self._hooks:
            try:
                await hook(req)
            except Exception as e:
                logger.error(f"[ApprovalQueue] Hook error: {e}")
    
    async def approve(self, req_id: str, approved_by: str) -> bool:
        """Approve a request."""
        req = self._queue.get(req_id)
        if not req or req.approved is not None:
            return False
        
        req.approved = True
        req.approved_by = approved_by
        req.approved_at = datetime.utcnow().isoformat()
        
        # Wake up waiter
        if req_id in self._waiters:
            self._waiters[req_id].set()
        
        logger.info(f"[ApprovalQueue] ✅ Approved: {req.action} by {approved_by}")
        return True
    
    async def deny(self, req_id: str, approved_by: str, reason: str = "") -> bool:
        """Deny a request."""
        req = self._queue.get(req_id)
        if not req or req.approved is not None:
            return False
        
        req.approved = False
        req.approved_by = approved_by
        req.approved_at = datetime.utcnow().isoformat()
        req.reason = reason
        
        # Wake up waiter
        if req_id in self._waiters:
            self._waiters[req_id].set()
        
        logger.info(f"[ApprovalQueue] ❌ Denied: {req.action} by {approved_by} — {reason}")
        return True
    
    async def get_pending(self) -> List[ApprovalRequest]:
        """Get all pending requests."""
        return [r for r in self._queue.values() if r.approved is None]
    
    async def get_by_id(self, req_id: str) -> Optional[ApprovalRequest]:
        """Get a specific request."""
        return self._queue.get(req_id)
    
    async def wait_for_approval(self, req_id: str, timeout_sec: float = 300) -> bool:
        """
        Poll until approved/denied or timeout.
        Returns True if approved, False if denied or timeout.
        """
        waiter = self._waiters.get(req_id)
        if not waiter:
            return False
        
        try:
            await asyncio.wait_for(waiter.wait(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            logger.warning(f"[ApprovalQueue] Timeout waiting for {req_id}")
            return False
        
        req = self._queue.get(req_id)
        if not req:
            return False
        
        return req.approved is True
    
    def register_hook(self, hook: Callable[[ApprovalRequest], Awaitable[None]]):
        """Register a callback for new requests."""
        self._hooks.append(hook)
    
    def stats(self) -> Dict:
        """Queue statistics."""
        all_reqs = list(self._queue.values())
        return {
            "total": len(all_reqs),
            "pending": sum(1 for r in all_reqs if r.approved is None),
            "approved": sum(1 for r in all_reqs if r.approved is True),
            "denied": sum(1 for r in all_reqs if r.approved is False),
        }


# Singleton instance
_queue_instance: Optional[ApprovalQueue] = None


def get_approval_queue() -> ApprovalQueue:
    """Get or create the global approval queue."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = ApprovalQueue()
    return _queue_instance


# Wire into governance
async def approval_hook(ctx: Dict) -> bool:
    """
    Called by @governed decorator when action needs HARD approval.
    
    ctx keys: action, resource, risk, args
    Returns: True = approved, False = denied/timeout
    """
    queue = get_approval_queue()
    
    req = ApprovalRequest(
        id=f"req_{uuid.uuid4().hex[:12]}",
        action=ctx.get("action", "unknown"),
        resource=ctx.get("resource", "unknown"),
        risk=ctx.get("risk", "unknown"),
        args=ctx.get("args", {}),
        created_at=datetime.utcnow().isoformat(),
    )
    
    await queue.push(req)
    logger.info(f"[ApprovalHook] Waiting for approval: {req.id}")
    
    approved = await queue.wait_for_approval(req.id, timeout_sec=300)
    
    if approved:
        logger.info(f"[ApprovalHook] ✅ Action approved: {req.id}")
    else:
        logger.warning(f"[ApprovalHook] ❌ Action denied or timeout: {req.id}")
    
    return approved
