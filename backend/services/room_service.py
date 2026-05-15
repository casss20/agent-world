"""
Room Service
Room lifecycle, shared context, agent membership, and state management.

Integrates with: models.py (Room, AgentRoom), websocket_manager.py
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload

from models import Room, Project, Agent, AgentRoom, BlackboardEvent, BlackboardOperation
from infrastructure.interfaces.base_storage_provider import BaseStorageProvider
from websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class RoomService:
    """Manages room lifecycle, context, membership, and coordination."""

    def __init__(self, storage_provider: Optional[BaseStorageProvider] = None):
        self.storage_provider = storage_provider

    # ── Room CRUD ─────────────────────────────────────────────────────────────

    @staticmethod
    async def create_room(
        db: AsyncSession,
        project_id: str,
        name: str,
        description: str = "",
        room_type: str = "collaboration",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Room:
        """Create a new room within a project."""
        room = Room(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            room_type=room_type,
            shared_context={},
            metadata=metadata or {},
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        db.add(room)
        await db.flush()
        await db.refresh(room)
        logger.info("Room created: %s (%s)", room.id, name)
        return room

    @staticmethod
    async def get_room(db: AsyncSession, room_id: str) -> Optional[Room]:
        """Get room by ID with eager-loaded relationships."""
        result = await db.execute(
            select(Room)
            .where(Room.id == room_id)
            .options(selectinload(Room.members))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_project_rooms(
        db: AsyncSession, project_id: str
    ) -> List[Room]:
        """List all rooms in a project."""
        result = await db.execute(
            select(Room)
            .where(Room.project_id == project_id)
            .order_by(Room.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_room(db: AsyncSession, room_id: str) -> bool:
        """Delete a room and all associated data."""
        room = await RoomService.get_room(db, room_id)
        if not room:
            return False

        await db.delete(room)
        await db.flush()
        logger.info("Room deleted: %s", room_id)
        return True

    # ── Shared Context (Blackboard) ─────────────────────────────────────────

    @staticmethod
    async def get_shared_context(
        db: AsyncSession, room_id: str
    ) -> Dict[str, Any]:
        """Build current shared context from event sourcing."""
        result = await db.execute(
            select(BlackboardEvent)
            .where(BlackboardEvent.room_id == room_id)
            .order_by(BlackboardEvent.sequence_number.asc())
        )
        events = result.scalars().all()

        state: Dict[str, Any] = {}
        for event in events:
            op = event.operation
            if op == BlackboardOperation.SET:
                state[event.key] = event.value
            elif op == BlackboardOperation.DELETE:
                state.pop(event.key, None)
            elif op == BlackboardOperation.APPEND:
                if event.key not in state:
                    state[event.key] = []
                if isinstance(state[event.key], list):
                    state[event.key].append(event.value)

        return state

    @staticmethod
    async def update_context(
        db: AsyncSession,
        room_id: str,
        agent_id: str,
        key: str,
        value: Any,
        operation: BlackboardOperation = BlackboardOperation.SET,
    ) -> Dict[str, Any]:
        """Agent updates shared context (with conflict resolution via event sourcing)."""
        # Get next sequence number
        result = await db.execute(
            select(BlackboardEvent.sequence_number)
            .where(BlackboardEvent.room_id == room_id)
            .order_by(BlackboardEvent.sequence_number.desc())
            .limit(1)
        )
        seq = (result.scalar() or 0) + 1

        event = BlackboardEvent(
            id=str(uuid.uuid4()),
            room_id=room_id,
            agent_id=agent_id,
            sequence_number=seq,
            key=key,
            value=value,
            operation=operation,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.flush()

        # Build and return updated state
        state = await RoomService.get_shared_context(db, room_id)

        # Broadcast context change
        await ws_manager.broadcast_to_room(
            room_id,
            {
                "type": "context_update",
                "agent_id": agent_id,
                "key": key,
                "value": value,
                "operation": operation.value,
                "state": state,
            },
        )

        return state

    # ── Agent Membership ──────────────────────────────────────────────────────

    @staticmethod
    async def add_agent_to_room(
        db: AsyncSession,
        room_id: str,
        agent_id: str,
        role: str = "participant",
    ) -> AgentRoom:
        """Add an agent to a room."""
        membership = AgentRoom(
            id=str(uuid.uuid4()),
            room_id=room_id,
            agent_id=agent_id,
            role=role,
            is_active=True,
            joined_at=datetime.now(timezone.utc),
        )
        db.add(membership)
        await db.flush()
        await db.refresh(membership)

        # Notify room
        await ws_manager.broadcast_to_room(
            room_id,
            {
                "type": "agent_joined",
                "agent_id": agent_id,
                "role": role,
            },
        )

        return membership

    @staticmethod
    async def remove_agent_from_room(
        db: AsyncSession, room_id: str, agent_id: str
    ) -> bool:
        """Remove an agent from a room."""
        result = await db.execute(
            select(AgentRoom)
            .where(
                and_(
                    AgentRoom.room_id == room_id,
                    AgentRoom.agent_id == agent_id,
                )
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            return False

        membership.is_active = False
        membership.left_at = datetime.now(timezone.utc)
        await db.flush()

        await ws_manager.broadcast_to_room(
            room_id,
            {
                "type": "agent_left",
                "agent_id": agent_id,
            },
        )
        return True

    @staticmethod
    async def get_room_members(
        db: AsyncSession, room_id: str
    ) -> List[Dict[str, Any]]:
        """Get all active members of a room with their presence status."""
        result = await db.execute(
            select(AgentRoom)
            .where(
                and_(
                    AgentRoom.room_id == room_id,
                    AgentRoom.is_active == True,
                )
            )
            .options(selectinload(AgentRoom.agent))
        )
        memberships = result.scalars().all()

        # Merge with WebSocket presence
        ws_presence = ws_manager.get_room_presence(room_id)

        members = []
        for m in memberships:
            agent = m.agent
            presence = ws_presence.get(agent.id, {})
            members.append(
                {
                    "agent_id": agent.id,
                    "name": agent.name,
                    "role": m.role,
                    "status": presence.get("status", "offline"),
                    "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                    "metadata": agent.metadata,
                }
            )
        return members

    @staticmethod
    async def get_room_state(
        db: AsyncSession, room_id: str
    ) -> Dict[str, Any]:
        """Get complete room state: info, members, context, recent activity."""
        room = await RoomService.get_room(db, room_id)
        if not room:
            return {}

        members = await RoomService.get_room_members(db, room_id)
        context = await RoomService.get_shared_context(db, room_id)
        presence = ws_manager.get_room_presence(room_id)

        return {
            "room": {
                "id": room.id,
                "name": room.name,
                "description": room.description,
                "type": room.room_type,
                "status": room.status,
                "created_at": room.created_at.isoformat() if room.created_at else None,
            },
            "members": members,
            "member_count": len(members),
            "active_count": len([m for m in members if m["status"] == "online"]),
            "shared_context": context,
            "presence": presence,
        }

    # ── Utility ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def set_agent_status(
        db: AsyncSession, room_id: str, agent_id: str, status: str
    ) -> bool:
        """Update an agent's status in a room."""
        result = await db.execute(
            select(AgentRoom)
            .where(
                and_(
                    AgentRoom.room_id == room_id,
                    AgentRoom.agent_id == agent_id,
                )
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            return False

        # Update presence via WebSocket manager
        conn = ws_manager.get_agent_connection(room_id, agent_id)
        if conn:
            conn.status = status

        await ws_manager.broadcast_to_room(
            room_id,
            {
                "type": "presence",
                "agent_id": agent_id,
                "status": status,
            },
        )
        return True
