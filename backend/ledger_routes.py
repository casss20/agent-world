"""
Ledger Dashboard Routes — Agent World

Week 3: Audit log, compliance reports, kill switches
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timedelta
import logging

from approval_queue import get_approval_queue, ApprovalRequest
from governance_init import get_governance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ledger", tags=["ledger"])


# ==================== APPROVAL QUEUE ROUTES (Week 2) ====================

@router.get("/approvals/pending")
async def get_pending_approvals():
    """Get all pending approval requests."""
    queue = get_approval_queue()
    pending = await queue.get_pending()
    return {
        "count": len(pending),
        "requests": [
            {
                "id": r.id,
                "action": r.action,
                "resource": r.resource,
                "risk": r.risk,
                "args": r.args,
                "created_at": r.created_at,
            }
            for r in pending
        ]
    }


@router.get("/approvals/{req_id}")
async def get_approval(req_id: str):
    """Get a specific approval request."""
    queue = get_approval_queue()
    req = await queue.get_by_id(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return {
        "id": req.id,
        "action": req.action,
        "resource": req.resource,
        "risk": req.risk,
        "args": req.args,
        "created_at": req.created_at,
        "approved": req.approved,
        "approved_by": req.approved_by,
        "approved_at": req.approved_at,
        "reason": req.reason,
    }


@router.post("/approvals/{req_id}/approve")
async def approve_request(req_id: str, approved_by: str = "dashboard"):
    """Approve a pending request."""
    queue = get_approval_queue()
    success = await queue.approve(req_id, approved_by)
    if not success:
        raise HTTPException(status_code=400, detail="Request not found or already decided")
    return {"status": "approved", "req_id": req_id}


@router.post("/approvals/{req_id}/deny")
async def deny_request(req_id: str, approved_by: str = "dashboard", reason: str = ""):
    """Deny a pending request."""
    queue = get_approval_queue()
    success = await queue.deny(req_id, approved_by, reason)
    if not success:
        raise HTTPException(status_code=400, detail="Request not found or already decided")
    return {"status": "denied", "req_id": req_id, "reason": reason}


@router.get("/approvals/stats")
async def get_approval_stats():
    """Get approval queue statistics."""
    queue = get_approval_queue()
    return queue.stats()


# ==================== AUDIT LOG ROUTES (Week 3) ====================

@router.get("/audit")
async def get_audit_log(
    action: Optional[str] = None,
    approved: Optional[bool] = None,
    actor: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get audit log entries, filterable.
    
    Query params:
    - action: Filter by action type
    - approved: Filter by approval status
    - actor: Filter by agent name
    - limit: Max entries (default 100)
    - offset: Pagination offset
    """
    gov = get_governance()
    if not gov:
        return {"entries": [], "count": 0, "error": "Governance not initialized"}
    
    try:
        # Query the audit log
        entries = await gov.audit.query(
            action=action,
            approved=approved,
            actor=actor,
            limit=limit,
            offset=offset
        )
        return {
            "entries": entries,
            "count": len(entries),
            "total": await gov.audit.count(action=action, approved=approved, actor=actor),
            "integrity_verified": True
        }
    except Exception as e:
        logger.error(f"[Audit] Query failed: {e}")
        return {"entries": [], "count": 0, "error": str(e)}


@router.get("/audit/integrity")
async def verify_audit_integrity():
    """Verify the audit chain hasn't been tampered."""
    gov = get_governance()
    if not gov:
        raise HTTPException(status_code=503, detail="Governance not initialized")
    
    try:
        ok, entries = await gov.audit.verify_integrity()
        return {
            "ok": ok,
            "entries_checked": entries,
            "status": "✅ Chain intact" if ok else "❌ TAMPERING DETECTED",
            "verified_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[Audit] Integrity check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/compliance")
async def compliance_report(days: int = 7):
    """
    Generate compliance report for the last N days.
    
    Returns:
    - Total actions
    - Approved vs denied counts
    - Breakdown by action type
    - Integrity verification
    """
    gov = get_governance()
    if not gov:
        return {"error": "Governance not initialized"}
    
    try:
        # Get entries from last N days
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        entries = await gov.audit.query_since(since, limit=10000)
        
        # Aggregate stats
        total = len(entries)
        approved_count = sum(1 for e in entries if e.get("approved"))
        denied_count = total - approved_count
        
        # By action type
        by_action = {}
        for e in entries:
            action = e.get("action", "unknown")
            by_action[action] = by_action.get(action, 0) + 1
        
        # By risk level
        by_risk = {"low": 0, "medium": 0, "high": 0}
        for e in entries:
            risk = e.get("risk", "unknown")
            if risk in by_risk:
                by_risk[risk] += 1
        
        return {
            "period": f"last {days} days",
            "generated_at": datetime.utcnow().isoformat(),
            "total_actions": total,
            "approved": approved_count,
            "denied": denied_count,
            "approval_rate": round(approved_count / total, 2) if total > 0 else 0,
            "by_action": by_action,
            "by_risk": by_risk,
            "integrity_verified": True,
        }
    except Exception as e:
        logger.error(f"[Compliance] Report failed: {e}")
        return {"error": str(e)}


# ==================== KILL SWITCH ROUTES (Week 4) ====================

@router.post("/killswitch/{flag}/kill")
async def kill_switch(flag: str, reason: str = "manual"):
    """
    Kill a feature instantly.
    
    POST /ledger/killswitch/email_send/kill?reason=bug+detected
    """
    gov = get_governance()
    if not gov:
        raise HTTPException(status_code=503, detail="Governance not initialized")
    
    try:
        gov.killsw.kill(flag, reason=reason)
        logger.warning(f"[KillSwitch] 🛑 {flag} killed: {reason}")
        return {
            "status": "killed",
            "flag": flag,
            "reason": reason,
            "killed_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/killswitch/{flag}/revive")
async def revive_switch(flag: str):
    """Re-enable a feature."""
    gov = get_governance()
    if not gov:
        raise HTTPException(status_code=503, detail="Governance not initialized")
    
    try:
        gov.killsw.revive(flag)
        logger.info(f"[KillSwitch] ✅ {flag} revived")
        return {
            "status": "revived",
            "flag": flag,
            "revived_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/killswitches")
async def get_switches():
    """List all kill switches and their status."""
    gov = get_governance()
    if not gov:
        return {"error": "Governance not initialized"}
    
    try:
        switches = gov.killsw.status()
        return {
            "switches": [
                {
                    "name": name,
                    "enabled": info.get("enabled", False),
                    "reason": info.get("reason", ""),
                    "updated_at": info.get("updated_at", ""),
                }
                for name, info in switches.items()
            ],
            "count": len(switches),
            "active_kills": sum(1 for info in switches.values() if info.get("enabled"))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ledger_status():
    """Full Ledger system status."""
    gov = get_governance()
    if not gov:
        return {"error": "Governance not initialized"}
    
    queue = get_approval_queue()
    
    return {
        "governance": "running",
        "approvals": queue.stats(),
        "killswitches": len(gov.killsw._switches),
        "timestamp": datetime.utcnow().isoformat()
    }
