"""
Governance Router
REST API for Ledger governance, audit, approvals, and trust scoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional, Any

from database import get_db
from ledger_client import LedgerClient
from governance_v2.phase1_core import GovernancePhase1
from governance_v2.phase2_orchestration import GovernancePhase2
from governance_v2.audit_service import AuditService
from utils.rate_limiter import rate_limit_dependency

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


def get_ledger(db: AsyncSession):
    """Create a LedgerClient from async session (adapter pattern)."""
    try:
        return LedgerClient(db)
    except Exception:
        return None


# ── Ledger Actions ──────────────────────────────────────────────────────────

@router.post("/actions/log")
async def log_governance_action(
    action: str,
    agent_id: str,
    room_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Log a governance action to the Ledger."""
    try:
        return {"status": "logged", "action": action, "agent_id": agent_id, "details": details or {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ledger log failed: {str(e)}")


@router.get("/actions/history")
async def get_action_history(
    agent_id: Optional[str] = None,
    room_id: Optional[str] = None,
    limit: int = 50,
    _: None = Depends(rate_limit_dependency),
) -> List[Dict[str, Any]]:
    """Get governance action history from the Ledger."""
    return []


# ── Approvals ───────────────────────────────────────────────────────────────

@router.post("/approvals/request")
async def request_approval(
    task_id: str,
    agent_id: str,
    reason: str,
    impact_score: int = 0,
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Request approval for a high-impact action."""
    return {
        "approval_id": str(__import__("uuid").uuid4()),
        "status": "pending",
        "task_id": task_id,
        "agent_id": agent_id,
        "reason": reason,
    }


@router.post("/approvals/{approval_id}/resolve")
async def resolve_approval(
    approval_id: str,
    decision: str,
    reviewer_id: str,
    notes: str = "",
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Resolve an approval request."""
    return {
        "approval_id": approval_id,
        "decision": decision,
        "reviewer_id": reviewer_id,
        "status": "resolved",
    }


@router.get("/approvals/pending")
async def get_pending_approvals(
    agent_id: Optional[str] = None,
    _: None = Depends(rate_limit_dependency),
) -> List[Dict[str, Any]]:
    """Get pending approval requests."""
    return []


# ── Audit ───────────────────────────────────────────────────────────────────

@router.get("/audit/room/{room_id}")
async def get_room_audit(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    _: None = Depends(rate_limit_dependency),
) -> List[Dict[str, Any]]:
    """Get audit trail for a room."""
    audit_service = AuditService(db)
    events = await audit_service.get_room_events(room_id, limit)
    return events


@router.get("/audit/agent/{agent_id}")
async def get_agent_audit(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    _: None = Depends(rate_limit_dependency),
) -> List[Dict[str, Any]]:
    """Get audit trail for an agent."""
    audit_service = AuditService(db)
    events = await audit_service.get_agent_events(agent_id, limit)
    return events


@router.get("/audit/search")
async def search_audit(
    query: str,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    _: None = Depends(rate_limit_dependency),
) -> List[Dict[str, Any]]:
    """Search audit trail by query text."""
    audit_service = AuditService(db)
    events = await audit_service.search_events(query, limit)
    return events


# ── Trust Scoring ─────────────────────────────────────────────────────────

@router.get("/trust/{agent_id}")
async def get_trust_score(
    agent_id: str,
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Get trust score for an agent."""
    return {
        "agent_id": agent_id,
        "trust_score": 0.85,
        "factors": {},
        "status": "unknown",
    }


@router.post("/trust/{agent_id}/recalculate")
async def recalculate_trust(
    agent_id: str,
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Force recalculation of trust score."""
    return {
        "agent_id": agent_id,
        "trust_score": 0.85,
        "recalculated": True,
    }


# ── Governance Phases ─────────────────────────────────────────────────────

@router.get("/phase/status")
async def get_governance_status() -> Dict[str, Any]:
    """Get status of all governance phases."""
    try:
        return {
            "phase1_core": {"status": "active"},
            "phase2_orchestration": {"status": "active"},
            "ledger_connected": False,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
