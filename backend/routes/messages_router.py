"""
Messages Router
REST API for messaging: broadcast, DM, threads, search.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional, Any

from database import get_db
from services.message_service import MessageService
from utils.rate_limiter import rate_limit_dependency

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])


# ── Send Messages ───────────────────────────────────────────────────────────

@router.post("/broadcast", status_code=status.HTTP_201_CREATED)
async def broadcast_message(
    room_id: str,
    from_agent_id: str,
    content: str,
    message_type: str = "chat",
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Broadcast a message to all agents in a room."""
    message = await MessageService.broadcast(
        db, room_id, from_agent_id, content, message_type, metadata
    )
    return {
        "id": message.id,
        "room_id": room_id,
        "from_agent_id": from_agent_id,
        "content": content,
        "message_type": message_type,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


@router.post("/dm", status_code=status.HTTP_201_CREATED)
async def direct_message(
    from_agent_id: str,
    to_agent_id: str,
    content: str,
    room_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Send a direct message between two agents."""
    message = await MessageService.direct_message(
        db, from_agent_id, to_agent_id, content, room_id, metadata
    )
    return {
        "id": message.id,
        "from_agent_id": from_agent_id,
        "to_agent_id": to_agent_id,
        "room_id": room_id,
        "content": content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


@router.post("/reply", status_code=status.HTTP_201_CREATED)
async def reply_to_message(
    reply_to_id: str,
    from_agent_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Reply to an existing message (threaded)."""
    try:
        message = await MessageService.threaded_reply(
            db, reply_to_id, from_agent_id, content, metadata
        )
        return {
            "id": message.id,
            "reply_to_id": reply_to_id,
            "from_agent_id": from_agent_id,
            "content": content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Read Messages ───────────────────────────────────────────────────────────

@router.get("/room/{room_id}")
async def get_room_messages(
    room_id: str,
    limit: int = 50,
    offset: int = 0,
    message_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get message history for a room."""
    messages = await MessageService.get_room_history(
        db, room_id, limit, offset, message_type
    )
    return [
        {
            "id": m.id,
            "from_agent_id": m.from_agent_id,
            "to_agent_id": m.to_agent_id,
            "content": m.content,
            "message_type": m.message_type,
            "reply_to_id": m.reply_to_id,
            "metadata": m.metadata,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.get("/thread/{message_id}")
async def get_thread(
    message_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get all messages in a conversation thread."""
    messages = await MessageService.get_conversation_thread(db, message_id)
    return [
        {
            "id": m.id,
            "from_agent_id": m.from_agent_id,
            "to_agent_id": m.to_agent_id,
            "content": m.content,
            "message_type": m.message_type,
            "reply_to_id": m.reply_to_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.get("/agent/{agent_id}")
async def get_agent_messages(
    agent_id: str,
    room_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get messages involving a specific agent."""
    messages = await MessageService.get_agent_conversations(db, agent_id, room_id, limit)
    return [
        {
            "id": m.id,
            "from_agent_id": m.from_agent_id,
            "to_agent_id": m.to_agent_id,
            "content": m.content,
            "room_id": m.room_id,
            "message_type": m.message_type,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


# ── Search ──────────────────────────────────────────────────────────────────

@router.get("/search/{room_id}")
async def search_messages(
    room_id: str,
    q: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Search messages in a room by content."""
    messages = await MessageService.search_messages(db, room_id, q, limit)
    return [
        {
            "id": m.id,
            "from_agent_id": m.from_agent_id,
            "content": m.content,
            "message_type": m.message_type,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


# ── Read Receipts ───────────────────────────────────────────────────────────

@router.post("/{message_id}/read")
async def mark_read(
    message_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Mark a message as read by an agent."""
    success = await MessageService.mark_read(db, message_id, agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message_id": message_id, "agent_id": agent_id, "status": "read"}
