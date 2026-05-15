"""
Message Service
Real-time messaging with broadcast, DM, threading, and history.

Integrates with: models.py (Message table), websocket_manager.py (live delivery)
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_
from sqlalchemy.orm import selectinload

from models import Message, Room, Agent
from websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class MessageService:
    """Handles all message operations: broadcast, DM, threads, history."""

    # ── Core Operations ───────────────────────────────────────────────────────

    @staticmethod
    async def broadcast(
        db: AsyncSession,
        room_id: str,
        from_agent_id: str,
        content: str,
        message_type: str = "chat",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Broadcast a message to all agents in a room.
        Stores in DB + delivers via WebSocket in real-time.
        """
        message = Message(
            id=str(uuid.uuid4()),
            room_id=room_id,
            from_agent_id=from_agent_id,
            to_agent_id=None,  # Broadcast = NULL
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)

        # Real-time delivery
        await ws_manager.broadcast_to_room(
            room_id,
            {
                "type": "message",
                "id": message.id,
                "from_agent_id": from_agent_id,
                "content": content,
                "message_type": message_type,
                "metadata": metadata,
                "created_at": message.created_at.isoformat(),
            },
            exclude=from_agent_id,
        )

        logger.info("Broadcast in room %s from %s", room_id, from_agent_id)
        return message

    @staticmethod
    async def direct_message(
        db: AsyncSession,
        from_agent_id: str,
        to_agent_id: str,
        content: str,
        room_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Send a direct message between two agents (optionally in a room)."""
        message = Message(
            id=str(uuid.uuid4()),
            room_id=room_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            content=content,
            message_type="direct",
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)

        # Deliver to recipient if online
        if room_id:
            await ws_manager.send_to_agent(
                room_id,
                to_agent_id,
                {
                    "type": "direct_message",
                    "id": message.id,
                    "from_agent_id": from_agent_id,
                    "content": content,
                    "created_at": message.created_at.isoformat(),
                },
            )

        logger.info("DM from %s to %s", from_agent_id, to_agent_id)
        return message

    @staticmethod
    async def threaded_reply(
        db: AsyncSession,
        reply_to_id: str,
        from_agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Create a threaded reply to an existing message."""
        # Fetch parent
        result = await db.execute(
            select(Message).where(Message.id == reply_to_id)
        )
        parent = result.scalar_one_or_none()
        if not parent:
            raise ValueError(f"Parent message {reply_to_id} not found")

        message = Message(
            id=str(uuid.uuid4()),
            room_id=parent.room_id,
            from_agent_id=from_agent_id,
            to_agent_id=parent.from_agent_id,
            content=content,
            message_type="reply",
            reply_to_id=reply_to_id,
            thread_root_id=parent.thread_root_id or parent.id,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)

        # Notify thread participants
        if message.room_id:
            await ws_manager.broadcast_to_room(
                message.room_id,
                {
                    "type": "thread_reply",
                    "id": message.id,
                    "reply_to_id": reply_to_id,
                    "from_agent_id": from_agent_id,
                    "content": content,
                    "created_at": message.created_at.isoformat(),
                },
            )

        return message

    # ── Queries ───────────────────────────────────────────────────────────────

    @staticmethod
    async def get_room_history(
        db: AsyncSession,
        room_id: str,
        limit: int = 50,
        offset: int = 0,
        message_type: Optional[str] = None,
    ) -> List[Message]:
        """Get paginated message history for a room."""
        query = (
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(desc(Message.created_at))
            .offset(offset)
            .limit(limit)
        )
        if message_type:
            query = query.where(Message.message_type == message_type)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_thread(db: AsyncSession, message_id: str) -> List[Message]:
        """Alias for get_conversation_thread."""
        return await MessageService.get_conversation_thread(db, message_id)

    @staticmethod
    async def get_conversation_thread(
        db: AsyncSession,
        message_id: str,
    ) -> List[Message]:
        """Get all messages in a thread (parent + all replies)."""
        # Get parent to find thread_root_id
        parent_result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            return []

        root_id = parent.thread_root_id or parent.id

        # Get all messages in thread
        result = await db.execute(
            select(Message)
            .where(
                or_(
                    Message.id == root_id,
                    Message.thread_root_id == root_id,
                    Message.reply_to_id == root_id,
                )
            )
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_agent_conversations(
        db: AsyncSession,
        agent_id: str,
        room_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Message]:
        """Get messages involving a specific agent (sent or received)."""
        query = (
            select(Message)
            .where(
                or_(
                    Message.from_agent_id == agent_id,
                    Message.to_agent_id == agent_id,
                )
            )
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        if room_id:
            query = query.where(Message.room_id == room_id)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def search_messages(
        db: AsyncSession,
        room_id: str,
        query_text: str,
        limit: int = 20,
    ) -> List[Message]:
        """Simple text search within a room's messages."""
        result = await db.execute(
            select(Message)
            .where(
                and_(
                    Message.room_id == room_id,
                    Message.content.ilike(f"%{query_text}%"),
                )
            )
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def mark_read(
        db: AsyncSession,
        message_id: str,
        agent_id: str,
    ) -> bool:
        """Mark a message as read by an agent."""
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            return False

        reads = message.metadata.get("read_by", [])
        if agent_id not in reads:
            reads.append(agent_id)
            message.metadata["read_by"] = reads
            message.metadata["last_read_at"] = datetime.now(timezone.utc).isoformat()
            await db.flush()

        return True
