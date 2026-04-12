"""
Ledger 2.0 Governance API Routes
FastAPI endpoints for all 4 phases WITH RBAC
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime

# Import RBAC dependencies
from .auth import (
    get_current_user, 
    require_admin, 
    require_governor, 
    require_operator,
    require_viewer,
    UserPrincipal,
    audit_log
)

router = APIRouter(prefix="/governance/v2", tags=["governance-v2"])

# This will be set by main.py when including the router
governance_system_instance = None

def set_governance_system(gs):
    global governance_system_instance
    governance_system_instance = gs

def get_governance_system():
    if governance_system_instance is None:
        raise HTTPException(status_code=503, detail="Governance system not initialized")
    return governance_system_instance


# ============ Models ============

class ExecuteActionRequest(BaseModel):
    agent_id: str
    action: str
    resource: str
    context: Dict[str, Any] = {}
    use_sandbox: bool = True


class TokenRequest(BaseModel):
    agent_id: str
    action: str
    resource: str
    context: Dict[str, Any] = {}
    ttl_seconds: int = 3600


class RiskClassificationResponse(BaseModel):
    risk_level: str
    approval_path: str
    reasoning: str


class FeatureFlagStatus(BaseModel):
    enabled: bool
    rollout: int
    businesses: int


class AgentRegistrationRequest(BaseModel):
    agent_id: str
    agent_type: str
    business_id: int
    capabilities: List[Dict]
    max_load: int = 10


class TaskSubmissionRequest(BaseModel):
    task_type: str
    business_id: int
    priority: int = 5
    payload: Dict[str, Any] = {}
    required_capabilities: List[str]


class KillSwitchTriggerRequest(BaseModel):
    switch_name: str
    reason: str


# ============ Auth Routes (Public) ============

class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str
    role: str = "operator"  # viewer, operator, governor, admin


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
    """
    from .auth import create_token
    
    # Map single role to list of inherited roles
    role_hierarchy = {
        "viewer": ["viewer"],
        "operator": ["operator", "viewer"],
        "governor": ["governor", "operator", "viewer"],
        "admin": ["admin", "governor", "operator", "viewer"]
    }
    
    roles = role_hierarchy.get(request.role, ["viewer"])
    
    token = create_token(
        sub=request.username,
        roles=roles
    )
    
    # Audit log
    await audit_log(
        action="login",
        actor=request.username,
        resource="/auth/login",
        result="success",
        metadata={"role": request.role}
    )
    
    return TokenResponse(
        access_token=token,
        expires_in=24 * 3600,
        role=request.role
    )


# ============ Phase 1: Core Governance Routes ============

@router.post("/execute")
async def execute_action(
    request: ExecuteActionRequest,
    user: UserPrincipal = Depends(require_governor),
    governance=Depends(get_governance_system)
):
    """
    Execute an action through the full governance pipeline.
    
    **Required Role:** governor or admin
    
    Pipeline includes:
    - Degradation check
    - Feature flag validation
    - Risk classification
    - Capability token issuance
    - Sandboxed execution
    - Event logging
    """
    # Audit log the execution attempt
    await audit_log(
        action="execute_action",
        actor=user.sub,
        resource=f"agent:{request.agent_id}",
        result="attempt",
        metadata={"action": request.action, "roles": user.roles}
    )
    
    result = await governance.execute_action(
        agent_id=request.agent_id,
        action=request.action,
        resource=request.resource,
        context=request.context,
        use_sandbox=request.use_sandbox
    )
    
    # Audit log the result
    await audit_log(
        action="execute_action",
        actor=user.sub,
        resource=f"agent:{request.agent_id}",
        result="success" if result.get("status") != "denied" else "denied",
        metadata={"action": request.action}
    )
    
    return result


@router.post("/token")
async def issue_token(
    request: TokenRequest,
    governance=Depends(get_governance_system)
):
    """Issue a capability token for an action."""
    token = await governance.governance.capability_issuer.issue_token(
        agent_id=request.agent_id,
        requested_action=request.action,
        target_resource=request.resource,
        context=request.context,
        ttl_seconds=request.ttl_seconds
    )
    
    if not token:
        raise HTTPException(status_code=403, detail="Token issuance denied")
    
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
    governance=Depends(get_governance_system)
):
    """Classify the risk level of an action."""
    risk_level, approval_path, reasoning = await governance.governance.risk_classifier.classify(
        action=action,
        resource=resource,
        context=context
    )
    
    return RiskClassificationResponse(
        risk_level=risk_level.value,
        approval_path=approval_path,
        reasoning=reasoning
    )


@router.get("/flags/{capability}")
async def check_feature_flag(
    capability: str,
    business_id: int,
    governance=Depends(get_governance_system)
):
    """Check if a capability is enabled for a business."""
    enabled = governance.governance.feature_flags.can_use(capability, business_id)
    
    flag_config = governance.governance.feature_flags.flags.get(capability, {})
    
    return {
        "capability": capability,
        "business_id": business_id,
        "enabled": enabled,
        "rollout_percentage": flag_config.get("rollout_percentage", 0),
        "requires_approval": flag_config.get("requires_ledger_approval", False)
    }


@router.get("/flags")
async def list_feature_flags(
    governance=Depends(get_governance_system)
):
    """List all feature flags and their status."""
    return governance.governance.feature_flags.get_status()


@router.post("/flags/{capability}/kill")
async def emergency_kill(
    capability: str,
    reason: str = "emergency",
    governance=Depends(get_governance_system)
):
    """Emergency kill switch for a capability."""
    governance.governance.feature_flags.emergency_kill(capability, reason)
    return {"status": "killed", "capability": capability, "reason": reason}


# ============ Phase 2: Orchestration Routes ============

@router.post("/agents/register")
async def register_agent(
    request: AgentRegistrationRequest,
    user: UserPrincipal = Depends(require_operator),
    governance=Depends(get_governance_system)
):
    """
    Register an agent with the capability registry.
    
    **Required Role:** operator, governor, or admin
    """
    from .phase2_orchestration import AgentRegistration, AgentCapability
    
    capabilities = [
        AgentCapability(**cap) for cap in request.capabilities
    ]
    
    registration = AgentRegistration(
        agent_id=request.agent_id,
        agent_type=request.agent_type,
        business_id=request.business_id,
        capabilities=capabilities,
        max_load=request.max_load
    )
    
    governance.registry.register(registration)
    
    # Audit log
    await audit_log(
        action="register_agent",
        actor=user.sub,
        resource=f"agent:{request.agent_id}",
        result="success",
        metadata={
            "agent_type": request.agent_type,
            "business_id": request.business_id,
            "roles": user.roles
        }
    )
    
    return {
        "status": "registered",
        "agent_id": request.agent_id,
        "capabilities": len(capabilities),
        "registered_by": user.sub
    }


@router.get("/agents")
async def list_agents(
    business_id: Optional[int] = None,
    capability: Optional[str] = None,
    governance=Depends(get_governance_system)
):
    """List registered agents, optionally filtered."""
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


@router.get("/agents/{agent_id}/health")
async def get_agent_health(
    agent_id: str,
    governance=Depends(get_governance_system)
):
    """Get health status of a specific agent."""
    if agent_id not in governance.registry.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = governance.registry.agents[agent_id]
    return {
        "agent_id": agent_id,
        "health": agent.health_status.value,
        "last_heartbeat": agent.last_heartbeat.isoformat(),
        "current_load": agent.current_load,
        "max_load": agent.max_load
    }


@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(
    agent_id: str,
    health_status: str = "healthy",
    governance=Depends(get_governance_system)
):
    """Receive heartbeat from an agent."""
    from .phase2_orchestration import AgentHealth
    
    status = AgentHealth(health_status)
    governance.registry.update_health(agent_id, status)
    
    return {"status": "acknowledged"}


@router.post("/tasks/submit")
async def submit_task(
    request: TaskSubmissionRequest,
    governance=Depends(get_governance_system)
):
    """Submit a task for execution."""
    from .phase2_orchestration import Task
    import uuid
    
    task = Task(
        task_id=str(uuid.uuid4()),
        task_type=request.task_type,
        business_id=request.business_id,
        priority=request.priority,
        payload=request.payload,
        required_capabilities=request.required_capabilities
    )
    
    task_id = await governance.chief_of_staff.submit_task(task)
    
    return {
        "task_id": task_id,
        "status": "submitted",
        "queue_position": len(governance.chief_of_staff.task_queue)
    }


@router.get("/tasks/queue")
async def get_queue_status(
    governance=Depends(get_governance_system)
):
    """Get current task queue status."""
    return governance.chief_of_staff.get_queue_status()


@router.get("/businesses/{business_id}/health")
async def get_business_health(
    business_id: int,
    governance=Depends(get_governance_system)
):
    """Get health summary for all agents in a business."""
    return governance.registry.get_business_health(business_id)


# ============ Phase 3: Memory & Audit Routes ============

@router.get("/events")
async def query_events(
    business_id: Optional[int] = None,
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    governance=Depends(get_governance_system)
):
    """Query governance events."""
    from .phase3_memory import EventType
    
    events = governance.event_stream.query(
        business_id=business_id,
        agent_id=agent_id,
        event_type=EventType(event_type) if event_type else None,
        limit=limit
    )
    
    return {
        "count": len(events),
        "events": [e.to_dict() for e in events]
    }


@router.post("/consolidate")
async def trigger_consolidation(
    background_tasks: BackgroundTasks,
    governance=Depends(get_governance_system)
):
    """Trigger memory consolidation (runs in background)."""
    async def run_consolidation():
        result = await governance.memory_consolidator.consolidate()
        if result:
            print(f"Consolidation complete: {result.decisions_processed} decisions")
    
    background_tasks.add_task(run_consolidation)
    
    return {
        "status": "started",
        "last_state": governance.memory_consolidator._get_state()
    }


@router.get("/consolidate/status")
async def get_consolidation_status(
    governance=Depends(get_governance_system)
):
    """Get memory consolidation status."""
    should_run = await governance.memory_consolidator.should_consolidate()
    
    return {
        "should_run": should_run,
        "state": governance.memory_consolidator._get_state(),
        "min_hours": governance.memory_consolidator.min_hours,
        "min_decisions": governance.memory_consolidator.min_decisions
    }


# ============ Phase 4: Hardening Routes ============

@router.get("/degradation/status")
async def get_degradation_status(
    governance=Depends(get_governance_system)
):
    """Get current degradation status."""
    return governance.degradation.get_status()


@router.post("/degradation/component/{name}")
async def update_component_health(
    name: str,
    healthy: bool,
    governance=Depends(get_governance_system)
):
    """Update component health status."""
    governance.degradation.update_component_health(name, healthy)
    
    return {
        "component": name,
        "healthy": healthy,
        "system_level": governance.degradation.current_level
    }


@router.get("/killswitches")
async def list_kill_switches(
    governance=Depends(get_governance_system)
):
    """List all kill switches and their status."""
    return governance.kill_switches.get_status()


@router.post("/killswitches/trigger")
async def trigger_kill_switch(
    request: KillSwitchTriggerRequest,
    user: UserPrincipal = Depends(require_admin),
    governance=Depends(get_governance_system)
):
    """
    Trigger an emergency kill switch.
    
    **Required Role:** admin only
    """
    success = governance.kill_switches.trigger(
        switch_name=request.switch_name,
        reason=request.reason
    )
    
    # Audit log critical action
    await audit_log(
        action="trigger_killswitch",
        actor=user.sub,
        resource=f"killswitch:{request.switch_name}",
        result="success" if success else "failed",
        metadata={"reason": request.reason}
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Kill switch not found")
    
    return {
        "status": "triggered",
        "switch": request.switch_name,
        "reason": request.reason,
        "triggered_by": user.sub
    }


@router.post("/killswitches/{name}/reset")
async def reset_kill_switch(
    name: str,
    authorized_by: str,
    governance=Depends(get_governance_system)
):
    """Reset a kill switch (requires authorization)."""
    success = governance.kill_switches.reset(name, authorized_by)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reset")
    
    return {
        "status": "reset",
        "switch": name,
        "authorized_by": authorized_by
    }


# ============ System Status ============

@router.get("/status")
async def get_full_status(
    governance=Depends(get_governance_system)
):
    """Get full system status across all phases."""
    return governance.get_status()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "phases": ["core", "orchestration", "memory", "hardening"]
    }
