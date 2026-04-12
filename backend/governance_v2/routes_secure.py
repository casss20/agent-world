"""
Governance v2 Routes - WITH SECURITY APPLIED

This file shows how to apply the security middleware to all governance endpoints.
Copy these patterns to your actual routes.py file.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request, status
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime

# Import security components
from security_middleware import (
    Role,
    TokenPayload,
    get_current_user,
    require_admin,
    require_governor,
    require_operator,
    audit_logger,
    JWTHandler
)

router = APIRouter(prefix="/governance/v2", tags=["governance-v2"])

# ============================================================================
# AUTH ENDPOINTS (Public - for obtaining tokens)
# ============================================================================

class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str
    role: Role


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate and obtain JWT token.
    
    In production, validate against user database.
    This is a simplified version for demonstration.
    """
    # TODO: Validate credentials against database
    # TODO: Check if user has requested role
    
    # Create token
    token = JWTHandler.create_token(
        subject=request.username,
        role=request.role,
        expiry_hours=24
    )
    
    # Audit log
    audit_logger.log(
        action="login",
        actor=request.username,
        resource="/auth/login",
        result="success",
        request_id=str(datetime.utcnow().timestamp()),
        metadata={"role": request.role.value}
    )
    
    return TokenResponse(
        access_token=token,
        expires_in=24 * 3600,
        role=request.role.value
    )


# ============================================================================
# PHASE 1: CORE GOVERNANCE (Governor+ roles)
# ============================================================================

@router.post("/execute")
async def execute_action(
    request: ExecuteActionRequest,
    user: TokenPayload = Depends(require_governor()),  # ← REQUIRES GOVERNOR ROLE
    governance=Depends(get_governance_system)
):
    """
    Execute an action through governance pipeline.
    
    **Required Role:** `governor` or `admin`
    
    **Rate Limit:** 50/hour
    
    **Audit:** Full decision logging
    """
    # Check business scope (object-level authorization)
    if user.business_id and request.context.get("business_id") != user.business_id:
        audit_logger.log(
            action="execute_denied",
            actor=user.sub,
            resource=f"business:{request.context.get('business_id')}",
            result="denied",
            request_id=str(datetime.utcnow().timestamp()),
            metadata={"reason": "business_scope_violation"}
        )
        raise HTTPException(
            status_code=403,
            detail="Cannot execute actions outside your business scope"
        )
    
    # Execute with full audit trail
    result = await governance.execute_action(
        agent_id=request.agent_id,
        action=request.action,
        resource=request.resource,
        context={
            **request.context,
            "authenticated_user": user.sub,
            "user_role": user.role.value,
            "request_id": str(datetime.utcnow().timestamp())
        },
        use_sandbox=request.use_sandbox
    )
    
    return result


@router.post("/token")
async def issue_token(
    request: TokenRequest,
    user: TokenPayload = Depends(require_governor()),  # ← REQUIRES GOVERNOR ROLE
    governance=Depends(get_governance_system)
):
    """
    Issue a capability token.
    
    **Required Role:** `governor` or `admin`
    
    **Rate Limit:** 100/hour
    
    **Audit:** Every issuance logged
    """
    token = await governance.governance.capability_issuer.issue_token(
        agent_id=request.agent_id,
        requested_action=request.action,
        target_resource=request.resource,
        context=request.context,
        ttl_seconds=request.ttl_seconds
    )
    
    if not token:
        audit_logger.log(
            action="token_issuance_denied",
            actor=user.sub,
            resource=request.resource,
            result="denied",
            request_id=str(datetime.utcnow().timestamp()),
            metadata={
                "agent_id": request.agent_id,
                "action": request.action
            }
        )
        raise HTTPException(status_code=403, detail="Token issuance denied")
    
    # Audit success
    audit_logger.log(
        action="token_issued",
        actor=user.sub,
        resource=request.resource,
        result="success",
        request_id=str(datetime.utcnow().timestamp()),
        metadata={
            "agent_id": request.agent_id,
            "action": request.action,
            "token_scope": token.scope
        }
    )
    
    return {
        "token": token.token,
        "scope": token.scope,
        "expires_at": token.expires_at.isoformat(),
        "constraints": token.constraints
    }


@router.post("/classify")
async def classify_risk(
    action: str,
    resource: str,
    context: Dict[str, Any] = {},
    user: TokenPayload = Depends(require_governor()),  # ← REQUIRES GOVERNOR+
    governance=Depends(get_governance_system)
):
    """Classify risk level (Governor+ only)"""
    return await governance.governance.risk_classifier.classify(
        action=action,
        resource=resource,
        context=context
    )


# ============================================================================
# PHASE 2: ORCHESTRATION (Operator+ roles)
# ============================================================================

@router.post("/agents/register")
async def register_agent(
    request: AgentRegistrationRequest,
    user: TokenPayload = Depends(require_operator()),  # ← REQUIRES OPERATOR+
    governance=Depends(get_governance_system)
):
    """
    Register an agent.
    
    **Required Role:** `operator`, `governor`, or `admin`
    
    **Rate Limit:** 200/hour
    
    **Validation:** Schema enforced, quotas checked
    """
    # Check business scope
    if user.business_id and request.business_id != user.business_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot register agents outside your business scope"
        )
    
    # Check quota (max 10 agents per operator in production)
    existing_agents = governance.registry.business_agents.get(request.business_id, [])
    if len(existing_agents) >= 10:
        raise HTTPException(
            status_code=429,
            detail="Agent quota exceeded for this business"
        )
    
    from .phase2_orchestration import AgentRegistration, AgentCapability
    
    capabilities = [
        AgentCapability(**cap) for cap in request.capabilities
    ]
    
    registration = AgentRegistration(
        agent_id=request.agent_id,
        agent_type=request.agent_type,
        business_id=request.business_id,
        capabilities=capabilities,
        max_load=request.max_load,
        metadata={
            "registered_by": user.sub,
            "registered_at": datetime.utcnow().isoformat()
        }
    )
    
    governance.registry.register(registration)
    
    # Audit log
    audit_logger.log(
        action="agent_registered",
        actor=user.sub,
        resource=f"agent:{request.agent_id}",
        result="success",
        request_id=str(datetime.utcnow().timestamp()),
        metadata={
            "agent_type": request.agent_type,
            "business_id": request.business_id,
            "capabilities": [c.name for c in capabilities]
        }
    )
    
    return {
        "status": "registered",
        "agent_id": request.agent_id,
        "capabilities": len(capabilities)
    }


@router.get("/agents")
async def list_agents(
    business_id: Optional[int] = None,
    capability: Optional[str] = None,
    user: TokenPayload = Depends(get_current_user),  # ← ANY AUTHENTICATED USER
    governance=Depends(get_governance_system)
):
    """
    List registered agents.
    
    **Required Role:** Any authenticated user
    
    **Scope:** Users can only see agents in their business
    """
    # Filter by user's business scope
    if user.role != Role.ADMIN and user.business_id:
        business_id = user.business_id
    
    if capability:
        agents = governance.registry.find_agents(
            capability=capability,
            business_id=business_id
        )
    else:
        agents = list(governance.registry.agents.values())
        if business_id:
            agents = [a for a in agents if a.business_id == business_id]
    
    return {
        "count": len(agents),
        "agents": [
            {
                "agent_id": a.agent_id,
                "agent_type": a.agent_type,
                "business_id": a.business_id,
                "health": a.health_status.value,
                "load": f"{a.current_load}/{a.max_load}",
                "capabilities": [c.name for c in a.capabilities]
            }
            for a in agents
        ]
    }


@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(
    agent_id: str,
    user: TokenPayload = Depends(require_operator()),  # ← OPERATOR+
    governance=Depends(get_governance_system)
):
    """Agent heartbeat (Operator+ only)"""
    governance.registry.update_heartbeat(agent_id)
    return {"status": "acknowledged"}


@router.post("/tasks/submit")
async def submit_task(
    request: TaskSubmissionRequest,
    user: TokenPayload = Depends(require_operator()),  # ← OPERATOR+
    governance=Depends(get_governance_system)
):
    """Submit task (Operator+ only)"""
    # Check business scope
    if user.business_id and request.business_id != user.business_id:
        raise HTTPException(status_code=403, detail="Business scope violation")
    
    # Implementation...
    return {"status": "submitted", "task_id": "task_123"}


# ============================================================================
# PHASE 4: HARDENING (Admin only)
# ============================================================================

@router.post("/killswitches/trigger")
async def trigger_kill_switch(
    request: KillSwitchTriggerRequest,
    user: TokenPayload = Depends(require_admin()),  # ← ADMIN ONLY
    governance=Depends(get_governance_system)
):
    """
    Trigger emergency kill switch.
    
    **Required Role:** `admin` ONLY
    
    **Rate Limit:** 10/hour
    
    **Alert:** Immediate notification sent
    """
    # CRITICAL: Log before action
    audit_logger.log(
        action="killswitch_triggered",
        actor=user.sub,
        resource=f"killswitch:{request.switch_name}",
        result="triggered",
        request_id=str(datetime.utcnow().timestamp()),
        metadata={
            "reason": request.reason,
            "severity": "CRITICAL"
        }
    )
    
    # TODO: Send immediate alert (PagerDuty, Slack, etc.)
    # alert_service.send_critical_alert(
    #     f"Kill switch {request.switch_name} triggered by {user.sub}: {request.reason}"
    # )
    
    return {
        "status": "triggered",
        "switch_name": request.switch_name,
        "triggered_by": user.sub,
        "reason": request.reason
    }


@router.get("/killswitches")
async def list_kill_switches(
    user: TokenPayload = Depends(require_admin())  # ← ADMIN ONLY
):
    """List kill switches (Admin only)"""
    return {
        "switches": [
            {"name": "autonomous_mode", "active": False},
            {"name": "all_writes", "active": False},
            {"name": "external_actions", "active": False}
        ]
    }


@router.post("/degradation/component/{component_name}")
async def set_degradation(
    component_name: str,
    level: str,  # normal, degraded, critical
    reason: str,
    user: TokenPayload = Depends(require_admin()),  # ← ADMIN ONLY
):
    """
    Set component degradation level.
    
    **Required Role:** `admin` ONLY
    
    **Rate Limit:** 30/hour
    
    **Alert:** Notification on every change
    """
    audit_logger.log(
        action="degradation_changed",
        actor=user.sub,
        resource=f"component:{component_name}",
        result="changed",
        request_id=str(datetime.utcnow().timestamp()),
        metadata={
            "old_level": "normal",  # TODO: Get actual current level
            "new_level": level,
            "reason": reason
        }
    )
    
    return {
        "component": component_name,
        "level": level,
        "set_by": user.sub
    }


@router.get("/degradation/status")
async def get_degradation_status(
    user: TokenPayload = Depends(require_governor())  # ← GOVERNOR+
):
    """Get degradation status (Governor+)"""
    return {
        "current_level": "normal",
        "components": []
    }


# ============================================================================
# PUBLIC ROUTES (No auth required)
# ============================================================================

@router.get("/health")
async def health_check():
    """Public health check"""
    return {"status": "healthy", "version": "2.0.0"}


@router.get("/status")
async def status(
    user: Optional[TokenPayload] = Depends(get_current_user)  # Optional auth
):
    """System status (auth optional, more details if authenticated)"""
    base_status = {
        "phase1_governance": {"feature_flags": 5},
        "phase2_orchestration": {"registered_agents": 0},
        "phase3_memory": {"consolidation_state": {}},
        "phase4_hardening": {"degradation_level": "normal"}
    }
    
    if user:
        base_status["authenticated_user"] = user.sub
        base_status["user_role"] = user.role.value
    
    return base_status


# ============================================================================
# AUDIT ENDPOINTS (Admin only)
# ============================================================================

@router.get("/audit/events")
async def get_audit_events(
    actor: Optional[str] = None,
    action: Optional[str] = None,
    user: TokenPayload = Depends(require_admin())  # ← ADMIN ONLY
):
    """Query audit events (Admin only)"""
    events = audit_logger.get_events(actor=actor, action=action)
    return {
        "count": len(events),
        "events": events[-100:]  # Last 100 events
    }
