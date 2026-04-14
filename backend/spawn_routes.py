"""
Spawn Routes — FastAPI API for goal-based agent spawning + live monitoring

Endpoints:
  POST /api/v1/spawn             — spawn a full agent team from a goal
  GET  /api/v1/spawn/{room_id}   — get room state + agents + tasks
  GET  /api/v1/rooms             — list all rooms (all projects)
  GET  /api/v1/tools             — list available tools
  WS   /ws/spawn/{room_id}       — live event stream for a room
"""

import os
import asyncio
import logging
from typing import Optional

from fastapi          import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic         import BaseModel
from sqlalchemy       import create_engine
from sqlalchemy.orm   import sessionmaker

from auto_spawner   import get_spawner
from agent_executor import start_executor
from mcp_registry   import list_tools
from models         import (
    Room, Agent, TaskQueue, AgentRoom, Business,
    RoomMessage, get_current_blackboard_state,
    TaskStatus, AgentStatus,
)

logger       = logging.getLogger(__name__)
router       = APIRouter(prefix="/api/v1", tags=["spawn"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/agentworld")
_engine      = create_engine(DATABASE_URL, pool_pre_ping=True)
_Session     = sessionmaker(bind=_engine)


def _db():
    return _Session()


# ------------------------------------------------------------------ #
# WebSocket connection manager                                         #
# ------------------------------------------------------------------ #

class _RoomConnectionManager:
    """Manages WebSocket connections grouped by room_id."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, room_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(room_id, []).append(ws)

    def disconnect(self, room_id: str, ws: WebSocket):
        room = self._connections.get(room_id, [])
        if ws in room:
            room.remove(ws)

    async def broadcast(self, room_id: str, event: dict):
        dead = []
        for ws in self._connections.get(room_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(room_id, ws)


_manager = _RoomConnectionManager()


async def _drain_broadcast_queue():
    """Background task: drain the room_tool broadcast queue → WebSocket clients."""
    from tools.room_tool import BROADCAST_QUEUE
    while True:
        try:
            room_id, event = await asyncio.wait_for(BROADCAST_QUEUE.get(), timeout=1.0)
            await _manager.broadcast(room_id, event)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Drain error: {e}")


# ------------------------------------------------------------------ #
# Startup hook (call this from your app lifespan)                     #
# ------------------------------------------------------------------ #

async def on_startup():
    """Start the executor + broadcast drain. Call from FastAPI lifespan."""
    await start_executor()
    asyncio.create_task(_drain_broadcast_queue())
    logger.info("[SpawnRoutes] Executor + broadcast drain started.")


# ------------------------------------------------------------------ #
# Models                                                               #
# ------------------------------------------------------------------ #

class SpawnRequest(BaseModel):
    goal:         str
    business_slug: Optional[str] = "default"


# ------------------------------------------------------------------ #
# Routes                                                               #
# ------------------------------------------------------------------ #

@router.post("/spawn")
async def spawn_agents(req: SpawnRequest):
    """
    Spawn a full agent team from a plain-English goal.
    Returns room_id + agent list + task list.
    """
    if not req.goal.strip():
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    spawner = get_spawner()
    result  = await spawner.spawn(req.goal, req.business_slug or "default")

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Spawn failed"))

    return result


@router.get("/rooms")
def list_rooms():
    """List all rooms across all businesses."""
    db = _db()
    try:
        rooms = db.query(Room).filter(Room.is_active == True).all()
        return [
            {
                "id":          str(r.id),
                "name":        r.name,
                "room_type":   r.room_type.value if r.room_type else "unknown",
                "description": r.description,
                "goal":        (r.policy_config or {}).get("goal", ""),
                "spawned_at":  (r.policy_config or {}).get("spawned_at", ""),
                "agent_count": db.query(AgentRoom).filter(
                    AgentRoom.room_id == r.id, AgentRoom.is_active == True
                ).count(),
            }
            for r in rooms
        ]
    finally:
        db.close()


@router.get("/rooms/{room_id}")
def get_room_detail(room_id: str):
    """Get full room state: agents, tasks, recent messages, blackboard."""
    db = _db()
    try:
        import uuid
        rid   = uuid.UUID(room_id)
        room  = db.query(Room).filter(Room.id == rid).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        # Agents
        memberships = db.query(AgentRoom).filter(
            AgentRoom.room_id == rid, AgentRoom.is_active == True
        ).all()
        agents = []
        for m in memberships:
            ag = db.query(Agent).filter(Agent.id == m.agent_id).first()
            if ag:
                agents.append({
                    "id":           str(ag.id),
                    "name":         ag.name,
                    "role":         ag.agent_type,
                    "status":       ag.status.value if ag.status else "unknown",
                    "capabilities": ag.capabilities or [],
                    "current_load": ag.current_load,
                })

        # Tasks
        tasks = db.query(TaskQueue).filter(TaskQueue.room_id == rid).order_by(
            TaskQueue.created_at.asc()
        ).all()
        task_list = [
            {
                "id":         str(t.id),
                "title":      t.payload.get("title", t.task_type),
                "task_type":  t.task_type,
                "status":     t.status.value,
                "priority":   t.priority,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "output":     (t.result or {}).get("output", "")[:300] if t.result else "",
            }
            for t in tasks
        ]

        # Recent messages
        msgs = db.query(RoomMessage).filter(
            RoomMessage.room_id == rid
        ).order_by(RoomMessage.sequence_number.desc()).limit(50).all()
        messages = [
            {
                "id":           str(m.id),
                "agent_id":     str(m.agent_id) if m.agent_id else None,
                "content":      m.content,
                "message_type": m.message_type.value if m.message_type else "chat",
                "created_at":   m.created_at.isoformat(),
            }
            for m in reversed(msgs)
        ]

        # Blackboard
        blackboard = get_current_blackboard_state(db, rid)

        return {
            "room": {
                "id":          str(room.id),
                "name":        room.name,
                "description": room.description,
                "room_type":   room.room_type.value if room.room_type else "unknown",
                "goal":        (room.policy_config or {}).get("goal", ""),
            },
            "agents":     agents,
            "tasks":      task_list,
            "messages":   messages,
            "blackboard": blackboard,
        }
    finally:
        db.close()


@router.get("/tools")
def list_available_tools():
    """List all registered tools agents can use."""
    tools = list_tools()
    return {
        "tools": [
            {
                "name":        name,
                "description": t["schema"].get("description", ""),
                "parameters":  list(t["schema"].get("parameters", {}).get("properties", {}).keys()),
            }
            for name, t in tools.items()
        ],
        "count": len(tools),
    }


@router.get("/businesses")
def list_businesses():
    """List all businesses."""
    db = _db()
    try:
        businesses = db.query(Business).filter(Business.is_active == True).all()
        return [
            {"id": str(b.id), "name": b.name, "slug": b.slug}
            for b in businesses
        ]
    finally:
        db.close()


# ------------------------------------------------------------------ #
# WebSocket                                                            #
# ------------------------------------------------------------------ #

@router.websocket("/ws/spawn/{room_id}")
async def room_live_stream(websocket: WebSocket, room_id: str):
    """
    WebSocket endpoint for real-time room events.
    Sends:  {type: task_started|task_completed|agent_message, ...}
    Client can send: {action: ping}
    """
    await _manager.connect(room_id, websocket)
    logger.info(f"[WS] Client connected to room {room_id}")

    # Send current state immediately
    db = _db()
    try:
        import uuid
        rid  = uuid.UUID(room_id)
        room = db.query(Room).filter(Room.id == rid).first()
        if room:
            await websocket.send_json({
                "type": "connected",
                "room_id": room_id,
                "room_name": room.name,
                "goal": (room.policy_config or {}).get("goal", ""),
            })
    except Exception:
        pass
    finally:
        db.close()

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _manager.disconnect(room_id, websocket)
        logger.info(f"[WS] Client disconnected from room {room_id}")
