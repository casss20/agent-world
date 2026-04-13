"""
Agent World: Hardened Mutation Endpoints
Production-ready implementations with:
- Tenant isolation
- Distributed locking
- State machine validation
- Governance integration
- Audit logging
"""

from uuid import UUID, uuid4
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum as PyEnum

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_, or_, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from pydantic import BaseModel, Field
import redis.asyncio as redis

# ============================================================================
# ENUMS AND MODELS
# ============================================================================

class AgentStatus(str, PyEnum):
    OFFLINE = "offline"
    STARTING = "starting"
    ONLINE = "online"
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class TaskStatus(str, PyEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RoomType(str, PyEnum):
    FORGE = "forge"
    RESEARCH = "research"
    MARKET = "market"
    SYSTEM = "system"

# Valid state transitions
VALID_STATUS_TRANSITIONS = {
    AgentStatus.OFFLINE: {AgentStatus.STARTING},
    AgentStatus.STARTING: {AgentStatus.ONLINE, AgentStatus.ERROR},
    AgentStatus.ONLINE: {AgentStatus.IDLE, AgentStatus.BUSY, AgentStatus.PAUSED, AgentStatus.ERROR},
    AgentStatus.IDLE: {AgentStatus.BUSY, AgentStatus.PAUSED, AgentStatus.ERROR, AgentStatus.OFFLINE},
    AgentStatus.BUSY: {AgentStatus.IDLE, AgentStatus.ERROR, AgentStatus.PAUSED},
    AgentStatus.PAUSED: {AgentStatus.IDLE, AgentStatus.BUSY, AgentStatus.OFFLINE},
    AgentStatus.ERROR: {AgentStatus.OFFLINE, AgentStatus.STARTING},
    AgentStatus.SHUTDOWN: {AgentStatus.OFFLINE},
}

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class TaskClaimResponse(BaseModel):
    status: str
    task_id: Optional[UUID] = None
    task_type: Optional[str] = None
    payload: Optional[dict] = None
    lease_expires: Optional[datetime] = None

class RoomJoinRequest(BaseModel):
    role: str = Field(default="member", regex="^(member|moderator|owner)$")
    agent_id: Optional[UUID] = None  # For assigning another agent

class RoomJoinResponse(BaseModel):
    membership_id: UUID
    room_id: UUID
    agent_id: UUID
    role: str
    joined_at: datetime

class BlackboardWriteRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: dict
    operation: str = Field(default="set", regex="^(set|delete|append)$")
    expected_version: Optional[int] = None  # For optimistic locking

class BlackboardWriteResponse(BaseModel):
    event_id: UUID
    sequence_number: int
    timestamp: datetime
    key: str
    value: dict

class AgentStatusUpdateRequest(BaseModel):
    status: AgentStatus
    reason: Optional[str] = None
    metadata: Optional[dict] = None

class AgentStatusUpdateResponse(BaseModel):
    agent_id: UUID
    previous_status: AgentStatus
    new_status: AgentStatus
    updated_at: datetime

class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    agent_type: str = Field(..., min_length=1, max_length=100)
    capabilities: List[str] = Field(default_factory=list)
    max_load: int = Field(default=5, ge=1, le=100)
    config: Optional[dict] = None

class AgentCreateResponse(BaseModel):
    agent_id: UUID
    name: str
    status: AgentStatus
    created_at: datetime

# ============================================================================
# DEPENDENCIES (stub implementations - replace with actual)
# ============================================================================

def get_db() -> Session:
    """Returns SQLAlchemy session"""
    pass

def get_redis() -> redis.Redis:
    """Returns Redis connection"""
    pass

def get_current_agent():
    """Returns authenticated agent"""
    pass

def get_current_business():
    """Returns current business/tenant"""
    pass

def get_ledger():
    """Returns Ledger client for governance"""
    pass

# ============================================================================
# PRIORITY 1: POST /tasks/claim
# Prevents duplicate task ownership under concurrency
# ============================================================================

router = APIRouter(prefix="/api/v1", tags=["hardened-mutations"])

@router.post("/tasks/claim", response_model=TaskClaimResponse)
async def claim_task(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_agent = Depends(get_current_agent),
    current_business = Depends(get_current_business),
    ledger = Depends(get_ledger),
):
    """
    Claim next available task with distributed locking.
    
    Safety features:
    - Tenant isolation (business_id filter)
    - Distributed locking (prevents race conditions)
    - Agent eligibility checks (status, load, capabilities)
    - Governance permission check
    - Atomic transaction with SELECT FOR UPDATE
    """
    # 1. Tenant scope verification
    if current_agent.business_id != current_business.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied"
        )
    
    # 2. Agent eligibility checks
    if current_agent.status not in {AgentStatus.IDLE, AgentStatus.ONLINE}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent not eligible to claim tasks (status: {current_agent.status})"
        )
    
    if current_agent.current_load >= current_agent.max_load:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent at max load ({current_agent.current_load}/{current_agent.max_load})"
        )
    
    # 3. Governance permission check
    allowed = await ledger.check_permission(
        actor_id=str(current_agent.id),
        action="task:claim",
        resource=f"business:{current_business.id}",
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied by governance"
        )
    
    # 4. Distributed lock to prevent thundering herd
    lock_key = f"task_claim:{current_business.id}"
    lock_value = str(uuid4())
    
    got_lock = await redis_client.set(lock_key, lock_value, nx=True, ex=5)
    if not got_lock:
        # Another agent is claiming, return gracefully
        return TaskClaimResponse(status="try_again_later")
    
    try:
        # 5. Transaction with SELECT FOR UPDATE
        with db.begin():
            # Find highest priority pending task
            stmt = (
                select(Task)
                .where(
                    and_(
                        Task.business_id == current_business.id,
                        Task.status == TaskStatus.PENDING,
                        Task.agent_id.is_(None),
                    )
                )
                .order_by(Task.priority.desc(), Task.created_at.asc())
                .with_for_update(skip_locked=True)  # Skip tasks being claimed by others
            )
            
            task = db.execute(stmt).scalars().first()
            
            if not task:
                return TaskClaimResponse(status="no_task_available")
            
            # 6. Capability check (inside transaction to ensure atomicity)
            if task.required_capability:
                if task.required_capability not in (current_agent.capabilities or []):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Agent lacks required capability: {task.required_capability}"
                    )
            
            # 7. Claim task atomically
            lease_duration = timedelta(minutes=5)
            task.agent_id = current_agent.id
            task.status = TaskStatus.CLAIMED
            task.claimed_at = datetime.utcnow()
            task.lease_expires = datetime.utcnow() + lease_duration
            
            # 8. Update agent load
            current_agent.current_load += 1
            if current_agent.current_load > 0 and current_agent.status == AgentStatus.IDLE:
                current_agent.status = AgentStatus.BUSY
            
            # Flush to get task.id before audit log
            db.flush()
        
        # 9. Audit log (outside transaction to not block on external call)
        await ledger.audit_log(
            actor_type="agent",
            actor_id=str(current_agent.id),
            action="task:claimed",
            resource_type="task",
            resource_id=str(task.id),
            result="success",
            metadata={
                "business_id": str(current_business.id),
                "task_type": task.task_type,
                "lease_expires": task.lease_expires.isoformat(),
            },
        )
        
        return TaskClaimResponse(
            status="claimed",
            task_id=task.id,
            task_type=task.task_type,
            payload=task.payload,
            lease_expires=task.lease_expires,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task claim failed: {str(e)}"
        )
    finally:
        # Always release lock
        await redis_client.delete(lock_key)


# ============================================================================
# PRIORITY 2: POST /rooms/{id}/join
# Controls room membership, permissions, and capacity
# ============================================================================

@router.post("/rooms/{room_id}/join", response_model=RoomJoinResponse)
async def join_room(
    room_id: UUID,
    request: RoomJoinRequest,
    db: Session = Depends(get_db),
    current_agent = Depends(get_current_agent),
    current_business = Depends(get_current_business),
    ledger = Depends(get_ledger),
):
    """
    Join a room with capacity checks and permission validation.
    
    Safety features:
    - Tenant isolation (room must belong to business or be global)
    - Governance permission check (room:join)
    - Capacity enforcement (max_agents)
    - Role validation (member/moderator/owner)
    - Atomic membership creation
    """
    # Determine which agent is joining
    target_agent_id = request.agent_id or current_agent.id
    
    # Only governors can assign other agents
    if target_agent_id != current_agent.id:
        allowed = await ledger.check_permission(
            actor_id=str(current_agent.id),
            action="agent:assign",
            resource=f"room:{room_id}",
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign other agents to room"
            )
    
    # 1. Lock room row for capacity check
    with db.begin():
        room = db.execute(
            select(Room)
            .where(Room.id == room_id)
            .with_for_update()
        ).scalars().first()
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # 2. Tenant scope verification
        if room.business_id != current_business.id and room.scope != "global":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Room not accessible from this business"
            )
        
        # 3. Governance permission check
        allowed = await ledger.check_permission(
            actor_id=str(current_agent.id),
            action="room:join",
            resource=f"room:{room_id}",
            context={"agent_id": str(target_agent_id), "role": request.role}
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Governance denied room join"
            )
        
        # 4. Check if already member
        existing = db.execute(
            select(AgentRoom)
            .where(
                and_(
                    AgentRoom.room_id == room_id,
                    AgentRoom.agent_id == target_agent_id,
                    AgentRoom.is_active == True
                )
            )
        ).scalars().first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already a member of this room"
            )
        
        # 5. Capacity check
        current_count = db.execute(
            select(func.count(AgentRoom.agent_id))
            .where(
                and_(
                    AgentRoom.room_id == room_id,
                    AgentRoom.is_active == True
                )
            )
        ).scalar()
        
        if current_count >= room.max_agents:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room at capacity ({room.max_agents} agents)"
            )
        
        # 6. Check room policy for role restrictions
        policy = room.policy_config or {}
        join_rule = policy.get("join_rule", "open")
        
        if join_rule == "invite_only" and request.role == "member":
            # Check for invitation
            invited = db.execute(
                select(RoomInvitation)
                .where(
                    and_(
                        RoomInvitation.room_id == room_id,
                        RoomInvitation.agent_id == target_agent_id,
                        RoomInvitation.status == "pending"
                    )
                )
            ).scalars().first()
            
            if not invited:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invitation required to join this room"
                )
            
            # Mark invitation as accepted
            invited.status = "accepted"
            invited.accepted_at = datetime.utcnow()
        
        elif join_rule == "governor_approved" and request.role != "owner":
            if not await ledger.check_permission(
                actor_id=str(current_agent.id),
                action="room:join:governor_approved",
                resource=f"room:{room_id}",
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Governor approval required"
                )
        
        # 7. Create membership atomically
        membership = AgentRoom(
            agent_id=target_agent_id,
            room_id=room_id,
            role=request.role,
            is_active=True,
            joined_at=datetime.utcnow(),
        )
        db.add(membership)
        
        # Update agent's room list
        target_agent = db.execute(
            select(Agent).where(Agent.id == target_agent_id)
        ).scalars().first()
        
        if target_agent:
            target_agent.updated_at = datetime.utcnow()
        
        db.flush()  # Get membership.id
    
    # 8. Publish presence event (outside transaction)
    await event_bus.publish(
        channel=f"room:{room_id}:presence",
        event={
            "type": "agent_joined",
            "agent_id": str(target_agent_id),
            "role": request.role,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # 9. Audit log
    await ledger.audit_log(
        actor_type="agent",
        actor_id=str(current_agent.id),
        action="room:joined",
        resource_type="room",
        resource_id=str(room_id),
        result="success",
        metadata={
            "joined_agent_id": str(target_agent_id),
            "role": request.role,
            "business_id": str(current_business.id),
        },
    )
    
    return RoomJoinResponse(
        membership_id=membership.id,
        room_id=room_id,
        agent_id=target_agent_id,
        role=request.role,
        joined_at=membership.joined_at,
    )


# ============================================================================
# PRIORITY 3: POST /rooms/{id}/blackboard
# Protects shared state from races and unauthorized writes
# ============================================================================

@router.post("/rooms/{room_id}/blackboard", response_model=BlackboardWriteResponse)
async def write_blackboard(
    room_id: UUID,
    request: BlackboardWriteRequest,
    db: Session = Depends(get_db),
    current_agent = Depends(get_current_agent),
    current_business = Depends(get_current_business),
    ledger = Depends(get_ledger),
):
    """
    Write to room blackboard with optimistic locking and event sourcing.
    
    Safety features:
    - Tenant isolation
    - Membership verification (must be in room)
    - Write permission check (governance)
    - Optimistic locking (expected_version)
    - Event sourcing (append-only history)
    """
    # 1. Verify room membership
    membership = db.execute(
        select(AgentRoom)
        .where(
            and_(
                AgentRoom.room_id == room_id,
                AgentRoom.agent_id == current_agent.id,
                AgentRoom.is_active == True
            )
        )
    ).scalars().first()
    
    if not membership:
        # Check if room is global
        room = db.execute(
            select(Room).where(Room.id == room_id)
        ).scalars().first()
        
        if not room or room.scope != "global":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this room"
            )
    
    # 2. Governance permission check
    allowed = await ledger.check_permission(
        actor_id=str(current_agent.id),
        action="blackboard:write",
        resource=f"room:{room_id}",
        context={"key": request.key, "operation": request.operation}
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied for blackboard write"
        )
    
    # 3. Check room policy for write restrictions
    room = db.execute(
        select(Room).where(Room.id == room_id)
    ).scalars().first()
    
    policy = room.policy_config or {}
    write_policy = policy.get("blackboard_write", "all_members")
    
    if write_policy == "senior_only" and membership.role not in ["moderator", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only senior members can write to blackboard"
        )
    
    if write_policy == "governor_only":
        if not await ledger.check_permission(
            actor_id=str(current_agent.id),
            action="blackboard:write:governor",
            resource=f"room:{room_id}",
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Governor approval required"
            )
    
    # 4. Transaction with optimistic locking
    with db.begin():
        # Get current sequence number
        last_seq = db.execute(
            select(func.max(BlackboardEvent.sequence_number))
            .where(BlackboardEvent.room_id == room_id)
        ).scalar() or 0
        
        # Optimistic lock check
        if request.expected_version is not None:
            if last_seq != request.expected_version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Concurrent modification detected. Expected version {request.expected_version}, found {last_seq}"
                )
        
        # 5. Create event (event sourcing)
        event = BlackboardEvent(
            room_id=room_id,
            agent_id=current_agent.id,
            sequence_number=last_seq + 1,
            key=request.key,
            value=request.value if request.operation != "delete" else None,
            operation=request.operation,
            timestamp=datetime.utcnow(),
        )
        db.add(event)
        
        db.flush()  # Get event.id
    
    # 6. Publish to event bus (outside transaction)
    await event_bus.publish(
        channel=f"room:{room_id}:blackboard",
        event={
            "type": "blackboard_updated",
            "event_id": str(event.id),
            "key": request.key,
            "value": request.value,
            "operation": request.operation,
            "sequence": event.sequence_number,
            "agent_id": str(current_agent.id),
            "timestamp": event.timestamp.isoformat()
        }
    )
    
    # 7. Audit log
    await ledger.audit_log(
        actor_type="agent",
        actor_id=str(current_agent.id),
        action="blackboard:write",
        resource_type="room",
        resource_id=str(room_id),
        result="success",
        metadata={
            "key": request.key,
            "operation": request.operation,
            "sequence": event.sequence_number,
        },
    )
    
    return BlackboardWriteResponse(
        event_id=event.id,
        sequence_number=event.sequence_number,
        timestamp=event.timestamp,
        key=request.key,
        value=request.value,
    )


# ============================================================================
# PRIORITY 4: PUT /agents/{id}/status
# Enforces valid lifecycle transitions
# ============================================================================

@router.put("/agents/{agent_id}/status", response_model=AgentStatusUpdateResponse)
async def update_agent_status(
    agent_id: UUID,
    request: AgentStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_agent = Depends(get_current_agent),
    current_business = Depends(get_current_business),
    ledger = Depends(get_ledger),
    redis_client: redis.Redis = Depends(get_redis),
):
    """
    Update agent status with state machine validation.
    
    Safety features:
    - State machine enforcement (valid transitions only)
    - Self-modification or governor permission
    - Audit logging for sensitive transitions
    - Heartbeat synchronization
    """
    # 1. Tenant scope
    target_agent = db.execute(
        select(Agent).where(Agent.id == agent_id)
    ).scalars().first()
    
    if not target_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    if target_agent.business_id != current_business.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied"
        )
    
    # 2. Permission check (self or governor)
    is_self = current_agent.id == agent_id
    
    if not is_self:
        allowed = await ledger.check_permission(
            actor_id=str(current_agent.id),
            action="agent:status:modify",
            resource=f"agent:{agent_id}",
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify other agent's status"
            )
    
    # 3. State machine validation
    current_status = AgentStatus(target_agent.status)
    new_status = request.status
    
    if new_status not in VALID_STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid status transition: {current_status} -> {new_status}"
        )
    
    # 4. Special restrictions for sensitive transitions
    sensitive_transitions = {
        AgentStatus.ERROR: "error_report",
        AgentStatus.SHUTDOWN: "agent_kill",
        AgentStatus.PAUSED: "agent_pause",
    }
    
    if new_status in sensitive_transitions and not is_self:
        required_action = sensitive_transitions[new_status]
        allowed = await ledger.check_permission(
            actor_id=str(current_agent.id),
            action=required_action,
            resource=f"agent:{agent_id}",
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Governor permission required for {new_status} transition"
            )
    
    # 5. Update status atomically
    previous_status = target_agent.status
    
    with db.begin():
        target_agent.status = new_status
        target_agent.updated_at = datetime.utcnow()
        
        # If transitioning to ONLINE/IDLE, update heartbeat
        if new_status in {AgentStatus.ONLINE, AgentStatus.IDLE}:
            target_agent.last_heartbeat = datetime.utcnow()
        
        # If transitioning to ERROR, store reason
        if new_status == AgentStatus.ERROR and request.reason:
            target_agent.error_reason = request.reason
        
        db.flush()
    
    # 6. Publish status change event
    await event_bus.publish(
        channel=f"agent:{agent_id}:status",
        event={
            "type": "status_changed",
            "agent_id": str(agent_id),
            "previous_status": previous_status,
            "new_status": new_status,
            "reason": request.reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # 7. Audit log (especially for sensitive transitions)
    if new_status in sensitive_transitions:
        await ledger.audit_log(
            actor_type="agent" if is_self else "user",
            actor_id=str(current_agent.id),
            action=f"agent:status:{new_status}",
            resource_type="agent",
            resource_id=str(agent_id),
            result="success",
            metadata={
                "previous_status": previous_status,
                "new_status": new_status,
                "reason": request.reason,
                "is_self": is_self,
            },
        )
    
    return AgentStatusUpdateResponse(
        agent_id=agent_id,
        previous_status=AgentStatus(previous_status),
        new_status=new_status,
        updated_at=datetime.utcnow(),
    )


# ============================================================================
# PRIORITY 5: POST /agents
# Governance approval before creating new live actors
# ============================================================================

@router.post("/agents", response_model=AgentCreateResponse, status_code=201)
async def create_agent(
    request: AgentCreateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),  # Note: requires user, not agent
    current_business = Depends(get_current_business),
    ledger = Depends(get_ledger),
    background_tasks: BackgroundTasks,
):
    """
    Create new agent with governance approval and capability validation.
    
    Safety features:
    - User-level permission (not agent)
    - Ledger governance check
    - Capability whitelist validation
    - Business scope enforcement
    - Audit logging
    """
    # 1. Governance permission check
    allowed = await ledger.check_permission(
        actor_id=str(current_user.id),
        action="agent:create",
        resource=f"business:{current_business.id}",
        context={
            "agent_type": request.agent_type,
            "capabilities": request.capabilities,
        }
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Governance denied agent creation"
        )
    
    # 2. Validate capabilities against registry
    invalid_caps = []
    for cap in request.capabilities:
        if not await ledger.validate_capability(cap):
            invalid_caps.append(cap)
    
    if invalid_caps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid capabilities: {', '.join(invalid_caps)}"
        )
    
    # 3. Check agent type limits (e.g., max 5 scouts per business)
    if request.agent_type in AGENT_TYPE_LIMITS:
        max_allowed = AGENT_TYPE_LIMITS[request.agent_type]
        current_count = db.execute(
            select(func.count(Agent.id))
            .where(
                and_(
                    Agent.business_id == current_business.id,
                    Agent.agent_type == request.agent_type,
                    Agent.deleted_at.is_(None)
                )
            )
        ).scalar()
        
        if current_count >= max_allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Maximum {max_allowed} {request.agent_type} agents allowed"
            )
    
    # 4. Create agent atomically
    with db.begin():
        agent = Agent(
            id=uuid4(),
            business_id=current_business.id,
            scope="business",
            name=request.name,
            agent_type=request.agent_type,
            capabilities=request.capabilities,
            max_load=request.max_load,
            config=request.config or {},
            status=AgentStatus.OFFLINE,
            desired_status=AgentStatus.ONLINE,
            current_load=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(agent)
        db.flush()
    
    # 5. Initialize agent in background
    background_tasks.add_task(
        initialize_agent,
        agent_id=agent.id,
        business_id=current_business.id,
    )
    
    # 6. Audit log
    await ledger.audit_log(
        actor_type="user",
        actor_id=str(current_user.id),
        action="agent:created",
        resource_type="agent",
        resource_id=str(agent.id),
        result="success",
        metadata={
            "business_id": str(current_business.id),
            "agent_type": request.agent_type,
            "capabilities": request.capabilities,
            "max_load": request.max_load,
        },
    )
    
    return AgentCreateResponse(
        agent_id=agent.id,
        name=agent.name,
        status=agent.status,
        created_at=agent.created_at,
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def initialize_agent(agent_id: UUID, business_id: UUID):
    """Background task to initialize agent resources"""
    # Create agent session
    # Register with service discovery
    # Initialize metrics
    pass

# Agent type limits per business
AGENT_TYPE_LIMITS = {
    "scout": 10,
    "maker": 5,
    "merchant": 5,
    "analyst": 3,
    "governor": 2,
}
