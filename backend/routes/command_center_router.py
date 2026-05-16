"""
Command Center Routes — Phase 8
Dashboard API for the Unified Command Center.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional, Any

from services.command_center import get_command_center
from security_middleware import get_current_user, TokenPayload

router = APIRouter(prefix="/api/v1/command-center", tags=["command-center"])


@router.get("/dashboard")
async def get_dashboard(
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get full dashboard state for all agents."""
    cc = await get_command_center()
    dashboard = await cc.get_dashboard()
    return dashboard.to_dict()


@router.get("/agent/{agent_id}")
async def get_agent_detail(
    agent_id: str,
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get detailed status for a single agent."""
    cc = await get_command_center()
    detail = await cc.get_agent_detail(agent_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return detail


@router.get("/health")
async def get_system_health() -> Dict[str, str]:
    """Quick system health check."""
    return {"status": "healthy", "version": "2.0.0"}
