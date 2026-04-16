"""
Agent World: Real-Time Streaming
WebSocket endpoints for room activity, agent presence, and task state
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

import redis.asyncio as redis

from models import (
    Agent, Room, AgentRoom, AgentSession, TaskQueue,
    AgentStatus, TaskStatus, get_room_member_count
)

router = APIRouter(prefix="/ws", tags=["websocket"])

# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time streaming"""
    
    def __init__(self):
        # room_id -> set of WebSocket connections
        self.room_connections: Dict[str, Set[WebSocket]] = {}
        # agent_id -> WebSocket connection (for direct messages)
        self.agent_connections: Dict[str, WebSocket] = {}
        # Connection metadata
        self.connection_info: Dict[WebSocket, dict] = {}
    
    async def connect_room(self, websocket: WebSocket, room_id: str, agent_id: str):
        """Connect agent to room stream"""
        await websocket.accept()
        
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        
        self.room_connections[room_id].add(websocket)
        self.connection_info[websocket] = {
            "room_id": room_id,
            "agent_id": agent_id,
            "connected_at": datetime.utcnow().isoformat()
        }
    
    async def connect_agent(self, websocket: WebSocket, agent_id: str):
        """Connect agent for direct messages and control signals"""
        await websocket.accept()
        
        self.agent_connections[agent_id] = websocket
        self.connection_info[websocket] = {
            "agent_id": agent_id,
            "connected_at": datetime.utcnow().isoformat()
        }
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection"""
        info = self.connection_info.pop(websocket, None)
        
        if info:
            room_id = info.get("room_id")
            agent_id = info.get("agent_id")
            
            if room_id and room_id in self.room_connections:
                self.room_connections[room_id].discard(websocket)
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]
            
            if agent_id and agent_id in self.agent_connections:
                if self.agent_connections[agent_id] == websocket:
                    del self.agent_connections[agent_id]
    
    async def broadcast_to_room(self, room_id: str, message: dict):
        """Broadcast message to all connections in a room"""
        if room_id not in self.room_connections:
            return
        
        disconnected = []
        message_json = json.dumps(message)
        
        for connection in self.room_connections[room_id]:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.append(connection)
        
        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_to_agent(self, agent_id: str, message: dict):
        """Send direct message to agent"""
        if agent_id not in self.agent_connections:
            return False
        
        try:
            await self.agent_connections[agent_id].send_text(json.dumps(message))
            return True
        except Exception:
            self.disconnect(self.agent_connections[agent_id])
            return False
    
    def get_room_subscriber_count(self, room_id: str) -> int:
        """Get number of subscribers to a room"""
        return len(self.room_connections.get(room_id, set()))
    
    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_room_connections": sum(len(conns) for conns in self.room_connections.values()),
            "unique_rooms": len(self.room_connections),
            "unique_agents": len(self.agent_connections),
            "total_connections": len(self.connection_info)
        }

# Global connection manager
manager = ConnectionManager()

# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

def get_redis():
    """Get Redis client"""
    raise NotImplementedError("Override with actual Redis dependency")

def get_db():
    """Get database session"""
    raise NotImplementedError("Override with actual DB dependency")

def get_current_agent_ws(websocket: WebSocket):
    """Authenticate WebSocket connection and return agent"""
    # Extract token from query params
    token = websocket.query_params.get("token")
    if not token:
        raise HTTPException(status_code=4001, detail="Missing token")
    
    # TODO: Validate JWT token and return agent
    # For now, stub implementation
    return {"id": "test-agent", "business_id": "test-business"}

@router.websocket("/rooms/{room_id}")
async def room_websocket(
    websocket: WebSocket,
    room_id: str,
    redis_client: redis.Redis = Depends(get_redis),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time room activity.
    
    Streams:
    - Agent joins/leaves
    - Messages
    - Blackboard updates
    - Task claims/completions
    - Presence changes
    """
    # Authenticate
    try:
        current_agent = get_current_agent_ws(websocket)
    except HTTPException as e:
        await websocket.close(code=e.status_code, reason=e.detail)
        return
    
    agent_id = str(current_agent["id"])
    
    # Verify room membership
    room = db.execute(
        select(Room).where(Room.id == room_id)
    ).scalars().first()
    
    if not room:
        await websocket.close(code=4004, reason="Room not found")
        return
    
    # Check membership (or global room)
    is_member = db.execute(
        select(AgentRoom).where(
            and_(
                AgentRoom.room_id == room_id,
                AgentRoom.agent_id == agent_id,
                AgentRoom.is_active == True
            )
        )
    ).scalars().first()
    
    if not is_member and room.scope != "global":
        await websocket.close(code=4003, reason="Not a member of this room")
        return
    
    # Connect to room
    await manager.connect_room(websocket, room_id, agent_id)
    
    # Subscribe to Redis channels for this room
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(
        f"room:{room_id}:messages",
        f"room:{room_id}:blackboard",
        f"room:{room_id}:presence",
        f"room:{room_id}:tasks"
    )
    
    # Send initial presence update
    await manager.broadcast_to_room(room_id, {
        "type": "presence",
        "event": "agent_online",
        "agent_id": agent_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Update agent status
    await redis_client.setex(
        f"agent:{agent_id}:presence",
        60,
        json.dumps({
            "status": "online",
            "room_id": room_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    )
    
    try:
        # Create tasks for concurrent handling
        redis_task = asyncio.create_task(
            handle_redis_messages(pubsub, room_id)
        )
        client_task = asyncio.create_task(
            handle_client_messages(websocket, room_id, agent_id, redis_client, db)
        )
        
        # Wait for either to complete (or fail)
        done, pending = await asyncio.wait(
            [redis_task, client_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            
    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        manager.disconnect(websocket)
        await pubsub.unsubscribe()
        
        # Broadcast offline presence
        await manager.broadcast_to_room(room_id, {
            "type": "presence",
            "event": "agent_offline",
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await redis_client.delete(f"agent:{agent_id}:presence")

async def handle_redis_messages(pubsub, room_id: str):
    """Forward Redis pub/sub messages to WebSocket"""
    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                data = json.loads(message["data"])
                await manager.broadcast_to_room(room_id, data)
            except json.JSONDecodeError:
                pass

async def handle_client_messages(
    websocket: WebSocket,
    room_id: str,
    agent_id: str,
    redis_client: redis.Redis,
    db: Session
):
    """Handle messages from client"""
    while True:
        try:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "ping":
                # Heartbeat from client
                await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                
                # Update presence
                await redis_client.setex(
                    f"agent:{agent_id}:presence",
                    60,
                    json.dumps({
                        "status": "online",
                        "room_id": room_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                )
            
            elif message_type == "typing":
                # Broadcast typing indicator
                await manager.broadcast_to_room(room_id, {
                    "type": "presence",
                    "event": "agent_typing",
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif message_type == "message":
                # Client sending message (will be handled by REST endpoint)
                # Acknowledge receipt
                await websocket.send_json({
                    "type": "ack",
                    "message_id": data.get("message_id"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            # Log error but keep connection alive
            print(f"Error handling client message: {e}")

@router.websocket("/agents/{agent_id}/control")
async def agent_control_websocket(
    websocket: WebSocket,
    agent_id: str,
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    WebSocket endpoint for agent control signals.
    
    Used for:
    - Pause/resume commands
    - Kill signals
    - Configuration updates
    - Task assignments
    """
    # Authenticate
    try:
        current_agent = get_current_agent_ws(websocket)
    except HTTPException as e:
        await websocket.close(code=e.status_code, reason=e.detail)
        return
    
    # Verify ownership (or governor permission)
    if str(current_agent["id"]) != agent_id:
        # TODO: Check governor permission
        await websocket.close(code=4003, reason="Cannot control other agent")
        return
    
    await manager.connect_agent(websocket, agent_id)
    
    # Subscribe to control channel
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"agent:{agent_id}:control")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                except json.JSONDecodeError:
                    pass
                    
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
        await pubsub.unsubscribe()

# ============================================================================
# SERVER-SENT EVENTS (SSE) - Alternative to WebSocket
# ============================================================================

from fastapi.responses import StreamingResponse

@router.get("/rooms/{room_id}/events")
async def room_events_sse(
    room_id: str,
    last_event_id: Optional[str] = None,
    redis_client: redis.Redis = Depends(get_redis),
    db: Session = Depends(get_db)
):
    """
    Server-Sent Events endpoint for room activity.
    
    Use this when WebSocket is not available (e.g., mobile, proxies).
    """
    # Verify room exists
    room = db.execute(select(Room).where(Room.id == room_id)).scalars().first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    async def event_generator():
        """Generate SSE events"""
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"room:{room_id}:messages")
        
        # Send initial connection event
        yield f"id: {datetime.utcnow().timestamp()}\nevent: connected\ndata: {json.dumps({'room_id': room_id})}\n\n"
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    event_id = datetime.utcnow().timestamp()
                    yield f"id: {event_id}\nevent: message\ndata: {message['data']}\n\n"
        finally:
            await pubsub.unsubscribe()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

# ============================================================================
# PRESENCE API
# ============================================================================

@router.get("/presence/rooms/{room_id}")
async def get_room_presence(
    room_id: str,
    redis_client: redis.Redis = Depends(get_redis),
    db: Session = Depends(get_db)
):
    """Get current presence state for a room"""
    # Get online agents from Redis
    pattern = f"agent:*:presence"
    online_agents = []
    
    async for key in redis_client.scan_iter(match=pattern):
        data = await redis_client.get(key)
        if data:
            presence = json.loads(data)
            if presence.get("room_id") == room_id:
                agent_id = key.decode().split(":")[1]
                online_agents.append({
                    "agent_id": agent_id,
                    "status": presence.get("status"),
                    "timestamp": presence.get("timestamp")
                })
    
    # Get total members
    total_members = get_room_member_count(db, UUID(room_id))
    
    return {
        "room_id": room_id,
        "online_count": len(online_agents),
        "total_members": total_members,
        "online_agents": online_agents
    }

@router.get("/presence/agents/{agent_id}")
async def get_agent_presence(
    agent_id: str,
    redis_client: redis.Redis = Depends(get_redis)
):
    """Get current presence state for an agent"""
    data = await redis_client.get(f"agent:{agent_id}:presence")
    
    if data:
        presence = json.loads(data)
        return {
            "agent_id": agent_id,
            "status": presence.get("status", "offline"),
            "room_id": presence.get("room_id"),
            "last_seen": presence.get("timestamp")
        }
    
    return {
        "agent_id": agent_id,
        "status": "offline"
    }

# ============================================================================
# ACTIVITY STREAM API
# ============================================================================

@router.get("/activity")
async def get_global_activity(
    limit: int = 50,
    redis_client: redis.Redis = Depends(get_redis)
):
    """Get global activity stream (recent events across all rooms)"""
    # Get recent events from Redis stream
    events = await redis_client.xrevrange(
        "activity:global",
        count=limit
    )
    
    return {
        "events": [
            {
                "id": event_id.decode(),
                "data": {k.decode(): v.decode() for k, v in fields.items()}
            }
            for event_id, fields in events
        ]
    }


# ============================================================================
# TASK WEBSOCKET - Real-time task updates for HumanTaskQueue
# ============================================================================

class TaskConnectionManager:
    """Manages WebSocket connections for real-time task updates"""
    
    def __init__(self):
        # business_id -> set of WebSocket connections
        self.business_connections: Dict[str, Set[WebSocket]] = {}
        # Connection metadata
        self.connection_info: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, business_id: str, user_id: str):
        """Connect user to business task stream"""
        await websocket.accept()
        
        if business_id not in self.business_connections:
            self.business_connections[business_id] = set()
        
        self.business_connections[business_id].add(websocket)
        self.connection_info[websocket] = {
            "business_id": business_id,
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat()
        }
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "business_id": business_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect from task stream"""
        info = self.connection_info.get(websocket)
        if info:
            business_id = info["business_id"]
            if business_id in self.business_connections:
                self.business_connections[business_id].discard(websocket)
                if not self.business_connections[business_id]:
                    del self.business_connections[business_id]
            del self.connection_info[websocket]
    
    async def broadcast_task_update(self, business_id: str, task_data: dict):
        """Broadcast task update to all connected clients for a business"""
        if business_id not in self.business_connections:
            return
        
        message = {
            "type": "task_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": task_data
        }
        
        disconnected = []
        for connection in self.business_connections[business_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Global task connection manager
task_manager = TaskConnectionManager()


@router.websocket("/tasks/{business_id}")
async def task_websocket(
    websocket: WebSocket,
    business_id: str,
    token: str = None
):
    """
    WebSocket endpoint for real-time task updates.
    
    Clients connect to receive instant notifications when:
    - New tasks are created
    - Task status changes
    - Tasks are assigned/reassigned
    - Human intervention is required
    """
    # Verify token (simplified - should use proper auth)
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    user_id = f"user_{token[:8]}"  # Simplified - extract from JWT in production
    
    try:
        await task_manager.connect(websocket, business_id, user_id)
        
        # Listen for messages from client
        while True:
            try:
                data = await websocket.receive_json()
                
                # Handle client actions
                if data.get("action") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif data.get("action") == "subscribe_task":
                    # Client wants updates for specific task
                    task_id = data.get("task_id")
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "task_id": task_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        pass
    finally:
        task_manager.disconnect(websocket)


# ============================================================================
# TASK BROADCAST HELPER - Call from other endpoints to trigger real-time updates
# ============================================================================

async def broadcast_task_created(business_id: str, task: dict):
    """Broadcast new task creation to connected clients"""
    await task_manager.broadcast_task_update(business_id, {
        "event": "created",
        "task": task
    })


async def broadcast_task_status_change(
    business_id: str, 
    task_id: str, 
    old_status: str, 
    new_status: str,
    assigned_to: str = None
):
    """Broadcast task status change to connected clients"""
    await task_manager.broadcast_task_update(business_id, {
        "event": "status_changed",
        "task_id": task_id,
        "old_status": old_status,
        "new_status": new_status,
        "assigned_to": assigned_to
    })


async def broadcast_human_intervention_required(business_id: str, task: dict):
    """Broadcast when human intervention is needed"""
    await task_manager.broadcast_task_update(business_id, {
        "event": "human_intervention_required",
        "task": task,
        "priority": "high",
        "message": "Your input is needed to continue"
    })
