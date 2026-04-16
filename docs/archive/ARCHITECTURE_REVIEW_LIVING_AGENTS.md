# Agent World: Living Agents Architecture Review (Continued)

## 11. Revised API Proposal (Continued)

```python
@router.post("/agents/{agent_id}/join", response_model=AgentRoomMembership)
async def join_room(
    agent_id: UUID,
    request: RoomJoinRequest,
    db: Session = Depends(get_db),
    ledger: LedgerClient = Depends(get_ledger),
):
    """Agent joins a room with capacity and permission checks"""
    async with db.begin():
        # Lock room row for capacity check
        room = db.query(Room).filter(
            Room.id == request.room_id
        ).with_for_update().first()
        
        if not room:
            raise HTTPException(404, "Room not found")
        
        # Check capacity
        current_count = db.query(AgentRoom).filter(
            AgentRoom.room_id == room.id,
            AgentRoom.is_active == True
        ).count()
        
        if current_count >= room.max_agents:
            raise HTTPException(409, "Room at capacity")
        
        # Governance check
        if not await ledger.check_permission(
            agent_id=agent_id,
            action="room:join",
            resource=f"room:{room.id}"
        ):
            raise HTTPException(403, "Permission denied")
        
        # Create membership
        membership = AgentRoom(
            agent_id=agent_id,
            room_id=room.id,
            role=request.role or "member",
            is_active=True
        )
        db.add(membership)
        
        # Update agent status
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        agent.updated_at = datetime.utcnow()
        
        # Publish event
        await event_bus.publish(
            channel=f"room:{room.id}:presence",
            event={
                "type": "agent_joined",
                "agent_id": str(agent_id),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return membership

@router.post("/agents/{agent_id}/leave")
async def leave_room(
    agent_id: UUID,
    room_id: UUID,
    db: Session = Depends(get_db),
):
    """Agent leaves room gracefully"""
    membership = db.query(AgentRoom).filter(
        AgentRoom.agent_id == agent_id,
        AgentRoom.room_id == room_id,
        AgentRoom.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(404, "Not in room")
    
    membership.is_active = False
    membership.left_at = datetime.utcnow()
    db.commit()
    
    await event_bus.publish(
        channel=f"room:{room_id}:presence",
        event={
            "type": "agent_left",
            "agent_id": str(agent_id),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return {"status": "left"}

@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(
    agent_id: UUID,
    session_id: UUID,
    status_report: AgentStatusReport,
    redis: Redis = Depends(get_redis),
    db: Session = Depends(get_db),
):
    """Agent heartbeat with session renewal"""
    # Verify session exists
    session_key = f"agent_session:{session_id}"
    session_data = await redis.get(session_key)
    
    if not session_data:
        raise HTTPException(404, "Session not found or expired")
    
    # Renew session TTL (30 seconds)
    await redis.setex(session_key, 30, json.dumps({
        "agent_id": str(agent_id),
        "status": status_report.status,
        "current_task": str(status_report.current_task) if status_report.current_task else None,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    # Update database (async background)
    asyncio.create_task(update_agent_heartbeat_db(agent_id, status_report))
    
    # Check for control signals
    control_signal = await redis.get(f"agent:{agent_id}:control")
    
    return HeartbeatResponse(
        acknowledged=True,
        control_signal=control_signal,
        server_time=datetime.utcnow()
    )

# ============================================================================
# ROOM ENDPOINTS
# ============================================================================

@router.get("/rooms", response_model=PaginatedResponse[RoomSummary])
async def list_rooms(
    room_type: Optional[RoomType] = None,
    include_full: bool = False,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
):
    """List rooms with occupancy info"""
    query = db.query(Room).filter(
        or_(
            Room.business_id == current_business.id,
            Room.scope == BusinessScope.GLOBAL
        ),
        Room.is_active == True,
        Room.archived_at.is_(None)
    )
    
    if room_type:
        query = query.filter(Room.room_type == room_type)
    
    total = query.count()
    rooms = query.offset(offset).limit(limit).all()
    
    # Add occupancy counts
    room_ids = [r.id for r in rooms]
    occupancy = dict(
        db.query(AgentRoom.room_id, func.count(AgentRoom.agent_id))
        .filter(
            AgentRoom.room_id.in_(room_ids),
            AgentRoom.is_active == True
        )
        .group_by(AgentRoom.room_id)
        .all()
    )
    
    return PaginatedResponse(
        items=[
            RoomSummary(
                id=room.id,
                name=room.name,
                room_type=room.room_type,
                occupancy=occupancy.get(room.id, 0),
                max_agents=room.max_agents,
                is_full=occupancy.get(room.id, 0) >= room.max_agents
            )
            for room in rooms
        ],
        total=total,
        limit=limit,
        offset=offset
    )

@router.get("/rooms/{room_id}", response_model=RoomDetail)
async def get_room(
    room_id: UUID,
    include_history: bool = False,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Get room details with current blackboard state"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(404, "Room not found")
    
    # Check membership
    is_member = db.query(AgentRoom).filter(
        AgentRoom.room_id == room_id,
        AgentRoom.agent_id == current_agent.id,
        AgentRoom.is_active == True
    ).first()
    
    if not is_member and room.scope != BusinessScope.GLOBAL:
        raise HTTPException(403, "Not a member of this room")
    
    # Get current blackboard state (latest value per key)
    blackboard = {}
    if include_history:
        events = db.query(BlackboardEvent).filter(
            BlackboardEvent.room_id == room_id
        ).order_by(BlackboardEvent.sequence_number.desc()).all()
        
        # Build state from events
        for event in reversed(events):
            if event.operation == "set":
                blackboard[event.key] = event.value
            elif event.operation == "delete":
                blackboard.pop(event.key, None)
    
    # Get active members
    members = db.query(Agent).join(AgentRoom).filter(
        AgentRoom.room_id == room_id,
        AgentRoom.is_active == True
    ).all()
    
    return RoomDetail(
        id=room.id,
        name=room.name,
        room_type=room.room_type,
        blackboard=blackboard,
        members=[AgentSummary.from_orm(m) for m in members],
        policy=room.policy_config
    )

@router.post("/rooms/{room_id}/blackboard", response_model=BlackboardWriteResponse)
async def write_blackboard(
    room_id: UUID,
    request: BlackboardWriteRequest,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
    ledger: LedgerClient = Depends(get_ledger),
):
    """Write to room blackboard with event sourcing"""
    # Permission check
    if not await ledger.check_permission(
        agent_id=current_agent.id,
        action="blackboard:write",
        resource=f"room:{room_id}"
    ):
        raise HTTPException(403, "Permission denied")
    
    async with db.begin():
        # Get next sequence number
        last_seq = db.query(func.max(BlackboardEvent.sequence_number)).filter(
            BlackboardEvent.room_id == room_id
        ).scalar() or 0
        
        # Check optimistic lock if provided
        if request.expected_version is not None:
            if last_seq != request.expected_version:
                raise HTTPException(409, "Concurrent modification detected")
        
        # Create event
        event = BlackboardEvent(
            room_id=room_id,
            agent_id=current_agent.id,
            sequence_number=last_seq + 1,
            key=request.key,
            value=request.value,
            operation=request.operation
        )
        db.add(event)
        db.flush()  # Get ID without committing
        
        # Publish to event bus
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
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return BlackboardWriteResponse(
            event_id=event.id,
            sequence_number=event.sequence_number,
            timestamp=event.timestamp
        )

@router.get("/rooms/{room_id}/messages", response_model=PaginatedResponse[RoomMessage])
async def get_messages(
    room_id: UUID,
    since: Optional[datetime] = None,
    before: Optional[datetime] = None,
    message_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Get room messages with pagination"""
    query = db.query(RoomMessage).filter(
        RoomMessage.room_id == room_id
    )
    
    if since:
        query = query.filter(RoomMessage.created_at > since)
    if before:
        query = query.filter(RoomMessage.created_at < before)
    if message_type:
        query = query.filter(RoomMessage.message_type == message_type)
    
    messages = query.order_by(RoomMessage.sequence_number.desc()).limit(limit).all()
    
    return PaginatedResponse(
        items=list(reversed(messages)),  # Oldest first
        total=None,  # Don't count for performance
        limit=limit,
        offset=0
    )

@router.post("/rooms/{room_id}/messages", response_model=RoomMessage)
async def send_message(
    room_id: UUID,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
    ledger: LedgerClient = Depends(get_ledger),
):
    """Send message to room"""
    # Rate limit check
    rate_key = f"message_rate:{current_agent.id}"
    message_count = await redis.incr(rate_key)
    if message_count == 1:
        await redis.expire(rate_key, 60)
    if message_count > 60:  # 60 messages per minute
        raise HTTPException(429, "Rate limit exceeded")
    
    # Permission check
    if not await ledger.check_permission(
        agent_id=current_agent.id,
        action="message:send",
        resource=f"room:{room_id}"
    ):
        raise HTTPException(403, "Permission denied")
    
    # Get sequence number
    last_seq = db.query(func.max(RoomMessage.sequence_number)).filter(
        RoomMessage.room_id == room_id
    ).scalar() or 0
    
    message = RoomMessage(
        room_id=room_id,
        agent_id=current_agent.id,
        message_type=request.message_type,
        content=request.content,
        metadata=request.metadata or {},
        sequence_number=last_seq + 1,
        expires_at=datetime.utcnow() + timedelta(days=30)  # 30-day retention
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Publish to event bus
    await event_bus.publish(
        channel=f"room:{room_id}:messages",
        event={
            "type": "new_message",
            "message_id": str(message.id),
            "agent_id": str(current_agent.id),
            "message_type": message.message_type,
            "content": message.content,
            "sequence": message.sequence_number,
            "timestamp": message.created_at.isoformat()
        }
    )
    
    return message

# ============================================================================
# TASK ENDPOINTS
# ============================================================================

@router.post("/tasks/claim", response_model=Optional[TaskClaimResponse])
async def claim_task(
    request: TaskClaimRequest,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
    redis: Redis = Depends(get_redis),
):
    """Claim next available task with distributed locking"""
    # Check agent can claim tasks
    if current_agent.status != AgentStatus.ONLINE:
        raise HTTPException(400, "Agent must be online to claim tasks")
    
    # Try to get distributed lock
    lock_key = f"task_claim:{request.room_id or 'global'}"
    lock_value = str(uuid.uuid4())
    
    got_lock = await redis.set(lock_key, lock_value, nx=True, ex=5)
    if not got_lock:
        return None  # Someone else is claiming, try again
    
    try:
        async with db.begin():
            # Find pending task with FOR UPDATE skip locked
            task = db.query(TaskQueue).filter(
                TaskQueue.status == "pending",
                TaskQueue.room_id == request.room_id if request.room_id else True
            ).order_by(
                TaskQueue.priority.desc(),
                TaskQueue.created_at
            ).with_for_update(skip_locked=True).first()
            
            if not task:
                return None
            
            # Claim task
            task.status = "claimed"
            task.claimed_by = current_agent.id
            task.claimed_at = datetime.utcnow()
            task.lease_expires = datetime.utcnow() + timedelta(minutes=5)
            
            return TaskClaimResponse(
                task_id=task.id,
                task_type=task.task_type,
                payload=task.payload,
                lease_expires=task.lease_expires
            )
    finally:
        await redis.delete(lock_key)

@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: UUID,
    request: TaskCompleteRequest,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Complete claimed task"""
    async with db.begin():
        task = db.query(TaskQueue).filter(
            TaskQueue.id == task_id
        ).with_for_update().first()
        
        if not task:
            raise HTTPException(404, "Task not found")
        
        if task.claimed_by != current_agent.id:
            raise HTTPException(403, "Task not claimed by this agent")
        
        if task.status not in ["claimed", "running"]:
            raise HTTPException(400, f"Task status is {task.status}")
        
        task.status = "completed"
        task.result = request.result
        task.completed_at = datetime.utcnow()
        
        # Audit log
        await ledger.audit_log(
            actor=current_agent.id,
            action="task:completed",
            resource=f"task:{task_id}",
            metadata={"task_type": task.task_type}
        )
        
        return {"status": "completed"}

@router.post("/tasks/{task_id}/renew-lease")
async def renew_task_lease(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Renew task lease while working on it"""
    task = db.query(TaskQueue).filter(
        TaskQueue.id == task_id,
        TaskQueue.claimed_by == current_agent.id
    ).first()
    
    if not task:
        raise HTTPException(404, "Task not found or not claimed")
    
    task.lease_expires = datetime.utcnow() + timedelta(minutes=5)
    db.commit()
    
    return {"lease_expires": task.lease_expires}

# ============================================================================
# CONTROL ENDPOINTS
# ============================================================================

@router.post("/agents/{agent_id}/pause")
async def pause_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ledger: LedgerClient = Depends(get_ledger),
    redis: Redis = Depends(get_redis),
):
    """Pause agent (governor+ only)"""
    if not await ledger.check_permission(
        user_id=current_user.id,
        action="agent:pause",
        resource=f"agent:{agent_id}"
    ):
        raise HTTPException(403, "Permission denied")
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    agent.desired_status = AgentStatus.PAUSED
    db.commit()
    
    # Signal agent via Redis
    await redis.setex(f"agent:{agent_id}:control", 60, "pause")
    
    return {"status": "pause_requested"}

@router.post("/agents/{agent_id}/kill")
async def kill_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ledger: LedgerClient = Depends(get_ledger),
    redis: Redis = Depends(get_redis),
):
    """Kill agent immediately (admin only)"""
    if not await ledger.check_permission(
        user_id=current_user.id,
        action="agent:kill",
        resource=f"agent:{agent_id}"
    ):
        raise HTTPException(403, "Permission denied")
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    agent.status = AgentStatus.SHUTDOWN
    agent.desired_status = AgentStatus.OFFLINE
    db.commit()
    
    # Force kill signal
    await redis.setex(f"agent:{agent_id}:control", 60, "kill")
    
    # Kill any active session
    await redis.delete(f"agent_session:{agent_id}")
    
    return {"status": "killed"}

# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@router.websocket("/ws/rooms/{room_id}")
async def room_websocket(
    websocket: WebSocket,
    room_id: UUID,
    token: str = Query(...),
    redis: Redis = Depends(get_redis),
    db: Session = Depends(get_db),
):
    """Real-time room updates"""
    await websocket.accept()
    
    # Authenticate
    try:
        agent = await authenticate_ws_token(token)
    except:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    # Verify membership
    is_member = db.query(AgentRoom).filter(
        AgentRoom.room_id == room_id,
        AgentRoom.agent_id == agent.id,
        AgentRoom.is_active == True
    ).first()
    
    if not is_member:
        await websocket.close(code=4003, reason="Forbidden")
        return
    
    # Subscribe to channels
    pubsub = redis.pubsub()
    await pubsub.subscribe(
        f"room:{room_id}:messages",
        f"room:{room_id}:blackboard",
        f"room:{room_id}:presence",
        f"agent:{agent.id}:control"
    )
    
    # Send initial presence
    await websocket.send_json({
        "type": "connected",
        "agent_id": str(agent.id),
        "room_id": str(room_id)
    })
    
    try:
        # Create tasks for bidirectional communication
        listen_task = asyncio.create_task(
            listen_to_redis(pubsub, websocket)
        )
        receive_task = asyncio.create_task(
            receive_from_client(websocket, room_id, agent, redis)
        )
        
        await asyncio.gather(listen_task, receive_task)
        
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe()
        await websocket.close()

async def listen_to_redis(pubsub, websocket):
    """Forward Redis events to WebSocket"""
    async for message in pubsub.listen():
        if message["type"] == "message":
            await websocket.send_text(message["data"])

async def receive_from_client(websocket, room_id, agent, redis):
    """Handle client messages"""
    while True:
        data = await websocket.receive_json()
        
        if data["type"] == "typing":
            await redis.publish(
                f"room:{room_id}:presence",
                json.dumps({
                    "type": "agent_typing",
                    "agent_id": str(agent.id)
                })
            )
```

---

## 12. Final Recommendation

### What to Keep

| Component | Why |
|-----------|-----|
 **Room-based isolation** | Correct pattern for multi-agent systems |
| **Event sourcing for blackboard** | Append-only history is the right approach |
| **Distributed locking for tasks** | Essential for correctness |
| **Heartbeat/session model** | Required for failure detection |
| **Governance integration points** | Security must be built-in |

### What to Redesign

| Component | Current | Redesign |
|-----------|---------|----------|
| **Agent-room relationship** | Single room | Many-to-many via AgentRoom |
| **Blackboard storage** | JSON blob | Event sourcing table |
| **Agent memory** | JSON blob | Structured AgentMemory table |
| **Permission system** | Ad-hoc | RBAC + Ledger integration |
| **Task claiming** | Naive SELECT/UPDATE | Distributed locking |
| **Agent lifecycle** | Simple while loop | Session manager + heartbeats |
| **Message ordering** | Auto-increment ID | Sequence numbers per room |
| **Tenant isolation** | Missing | business_id on all tables |

### Minimum Viable Path to Production (This Week)

**Day 1-2: Schema Fixes**
```bash
# Priority migrations
001_add_business_id_to_all_tables.py
002_create_agent_rooms_junction.py
003_create_blackboard_events_table.py
004_create_agent_sessions_table.py
005_add_sequence_numbers.py
```

**Day 3: Core API Fixes**
- Fix all routes to filter by business_id
- Add distributed locking to task claiming
- Implement heartbeat endpoint

**Day 4: Lifecycle Manager**
- Build AgentSession model
- Create heartbeat monitor job
- Implement graceful shutdown

**Day 5: Governance Integration**
- Add Ledger permission checks to all routes
- Implement audit logging
- Add kill switch functionality

**Weekend: Testing**
- Load test with 100 concurrent agents
- Test failure scenarios (kill -9, network partition)
- Verify tenant isolation

### What Should Be Built First

1. **AgentSession + Heartbeat** - Without this, you can't detect dead agents
2. **Distributed Locking** - Without this, you'll have duplicate work
3. **business_id Isolation** - Without this, customers see each other's data
4. **Event Sourcing** - Without this, blackboard has race conditions
5. **Governance Integration** - Without this, agents can do anything

### Architecture Decision Records

**ADR-1: Agent-Room Relationship**
- Decision: Many-to-many via AgentRoom table
- Rationale: Agents can exist in multiple rooms simultaneously (Forge + Research)

**ADR-2: Blackboard Storage**
- Decision: Event sourcing with BlackboardEvent table
- Rationale: Append-only prevents lost updates, provides audit history

**ADR-3: Task Claiming**
- Decision: Redis distributed lock + SELECT FOR UPDATE
- Rationale: Prevents race conditions without polling

**ADR-4: Agent Lifecycle**
- Decision: Session model with Redis heartbeats
- Rationale: Fast failure detection, graceful shutdown support

**ADR-5: Tenant Isolation**
- Decision: business_id column on all tables
- Rationale: Simple, works with existing query patterns

---

## Conclusion

The Living Agents design direction is **architecturally sound** but has **critical gaps** that would cause production failures:

1. **Data integrity issues** from JSON blackboard and race conditions
2. **Security violations** from missing tenant isolation
3. **Operational instability** from ghost agents and stuck tasks
4. **Scalability limits** from naive locking

**The good news:** These are all solvable with the patterns in this review.

**Bottom line:** Budget 1 week for the MVP fixes (Day 1-5 plan), then 2 more weeks for hardening before production traffic.

---

*Architecture review completed by KC (Kimi Claw)*  
*For: Agent World Living Agents v2.1*  
*Date: April 13, 2026*
