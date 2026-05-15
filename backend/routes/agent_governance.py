"""
Agent Governance Routes
API endpoints for governance, approval gates, audit logging, and kill switches
for role-based agents.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from services.agent_governance_service import (
    get_agent_governance,
    GovernanceAction,
)
from agents.roles.role_definitions import list_roles

router = APIRouter(prefix="/api/governance/agents", tags=["agent-governance"])


# ── Approval Gates ─────────────────────────────────────────────────────


@router.post("/{agent_id}/check", response_model=dict)
async def check_agent_action(
    agent_id: str,
    payload: dict,
):
    """Check if an agent action is allowed (approval gate)."""
    gov = get_agent_governance()
    action = payload.get("action", "")
    
    try:
        gov_action = GovernanceAction(action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    
    result = await gov.check_action(agent_id, gov_action, payload.get("context"))
    return result


@router.post("/approve/{approval_id}", response_model=dict)
async def approve_action(
    approval_id: str,
    payload: dict,
):
    """Approve a pending agent action."""
    gov = get_agent_governance()
    approver = payload.get("approver", "admin")
    return await gov.approve_action(approval_id, approver)


# ── Audit ────────────────────────────────────────────────────────────


@router.get("/audit", response_model=dict)
async def get_audit_trail(
    agent_id: Optional[str] = None,
    limit: int = 100,
):
    """Get audit trail for agent actions."""
    gov = get_agent_governance()
    logs = gov.get_audit_trail(agent_id, limit)
    return {"logs": logs, "count": len(logs)}


# ── Kill Switches ──────────────────────────────────────────────────────


@router.post("/{agent_id}/kill", response_model=dict)
async def activate_kill_switch(
    agent_id: str,
    payload: dict,
):
    """Emergency kill switch — disable an agent immediately."""
    gov = get_agent_governance()
    reason = payload.get("reason", "Emergency stop")
    return gov.enable_kill_switch(agent_id, reason)


@router.post("/{agent_id}/enable", response_model=dict)
async def deactivate_kill_switch(
    agent_id: str,
):
    """Re-enable an agent after kill switch."""
    gov = get_agent_governance()
    return gov.disable_kill_switch(agent_id)


@router.get("/{agent_id}/status", response_model=dict)
async def get_agent_governance_status(agent_id: str):
    """Get governance status for an agent (permissions, kill switch, etc.)."""
    gov = get_agent_governance()
    return gov.get_agent_permissions(agent_id)


@router.get("/status/all", response_model=dict)
async def get_all_agent_status():
    """Get governance status for all agents."""
    gov = get_agent_governance()
    roles = list_roles()
    
    return {
        "agents": [
            gov.get_agent_permissions(r.id)
            for r in roles
        ],
        "kill_switches": gov.get_kill_switch_status(),
    }
