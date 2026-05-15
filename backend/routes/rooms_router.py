"""
Rooms Router
REST API for room CRUD, context management, and agent membership.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional, Any

from database import get_db
from services.room_service import RoomService
from services.message_service import MessageService
from utils.rate_limiter import rate_limit_dependency

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


# ── Room CRUD ───────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_room(
    project_id: str,
    name: str,
    description: str = "",
    room_type: str = "collaboration",
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Create a new collaboration room within a project."""
    room = await RoomService.create_room(
        db, project_id, name, description, room_type, metadata
    )
    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
        "project_id": project_id,
        "room_type": room_type,
        "shared_context": {},
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


@router.get("/{room_id}")
async def get_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get complete room state: info, members, context, presence."""
    state = await RoomService.get_room_state(db, room_id)
    if not state:
        raise HTTPException(status_code=404, detail="Room not found")
    return state


@router.get("/project/{project_id}")
async def list_project_rooms(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List all rooms in a project."""
    rooms = await RoomService.list_project_rooms(db, project_id)
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "type": r.room_type,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rooms
    ]


@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete a room and all associated data."""
    success = await RoomService.delete_room(db, room_id)
    if not success:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"status": "deleted", "room_id": room_id}


# ── Context Management ──────────────────────────────────────────────────────

@router.get("/{room_id}/context")
async def get_context(
    room_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get current shared context (blackboard state)."""
    context = await RoomService.get_shared_context(db, room_id)
    return {"room_id": room_id, "context": context}


@router.put("/{room_id}/context")
async def update_context(
    room_id: str,
    agent_id: str,
    key: str,
    value: Any,
    operation: str = "set",  # set, delete, append
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update room shared context."""
    from models import BlackboardOperation

    op_map = {
        "set": BlackboardOperation.SET,
        "delete": BlackboardOperation.DELETE,
        "append": BlackboardOperation.APPEND,
    }
    op = op_map.get(operation, BlackboardOperation.SET)

    state = await RoomService.update_context(db, room_id, agent_id, key, value, op)
    return {"room_id": room_id, "shared_context": state}


# ── Agent Membership ────────────────────────────────────────────────────────

@router.post("/{room_id}/agents/{agent_id}")
async def add_agent(
    room_id: str,
    agent_id: str,
    role: str = "participant",
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Add an agent to a room."""
    membership = await RoomService.add_agent_to_room(db, room_id, agent_id, role)
    return {
        "room_id": room_id,
        "agent_id": agent_id,
        "role": role,
        "status": "joined",
        "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
    }


@router.delete("/{room_id}/agents/{agent_id}")
async def remove_agent(
    room_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Remove an agent from a room."""
    success = await RoomService.remove_agent_from_room(db, room_id, agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not in room")
    return {"status": "left", "room_id": room_id, "agent_id": agent_id}


@router.get("/{room_id}/agents")
async def list_room_agents(
    room_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List all agents in a room with presence."""
    return await RoomService.get_room_members(db, room_id)


@router.put("/{room_id}/agents/{agent_id}/status")
async def set_agent_status(
    room_id: str,
    agent_id: str,
    status: str,  # online, away, busy, offline
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update an agent's status in a room."""
    success = await RoomService.set_agent_status(db, room_id, agent_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found in room")
    return {"room_id": room_id, "agent_id": agent_id, "status": status}


# ── Messages ───────────────────────────────────────────────────────────────

@router.get("/{room_id}/messages")
async def get_room_messages(
    room_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get message history for a room."""
    messages = await MessageService.get_room_history(db, room_id, limit, offset)
    return [
        {
            "id": m.id,
            "from_agent_id": m.from_agent_id,
            "to_agent_id": m.to_agent_id,
            "content": m.content,
            "message_type": m.message_type,
            "metadata": m.metadata,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
