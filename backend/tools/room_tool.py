"""
Tool: room_tool
Agents broadcast messages to their room — visible on the live dashboard.
Writes to DB + pushes to the in-memory broadcast queue for WebSocket delivery.
"""

import os
import uuid as _uuid
from typing import Any, Dict
from datetime import datetime


# ------------------------------------------------------------------ #
# In-process broadcast queue                                          #
# Push (room_id, event_dict) tuples here.                            #
# The WebSocket dispatcher (spawn_routes.py) drains this queue.      #
# ------------------------------------------------------------------ #
import asyncio
BROADCAST_QUEUE: asyncio.Queue = asyncio.Queue()


def _get_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/agentworld")
    engine       = create_engine(DATABASE_URL)
    Session      = sessionmaker(bind=engine)
    return Session()


async def broadcast_to_room(
    message:      str,
    message_type: str = "info",
    _agent_id:    str = "",
    _task_id:     str = "",
    _room_id:     str = "",
) -> Dict[str, Any]:
    """
    Post a message to the room (visible on dashboard + stored in DB).
    message_type: info | update | alert | completed
    """
    try:
        from models import RoomMessage, MessageType

        db = _get_db()
        try:
            room_uuid  = _uuid.UUID(_room_id)  if _room_id  else None
            agent_uuid = _uuid.UUID(_agent_id) if _agent_id else None

            if not room_uuid:
                return {"success": False, "error": "No room_id provided"}

            # Get next sequence number
            from sqlalchemy import func
            from models import RoomMessage as RM
            max_seq = db.query(func.max(RM.sequence_number)).filter(
                RM.room_id == room_uuid
            ).scalar() or 0

            msg = RoomMessage(
                room_id         = room_uuid,
                agent_id        = agent_uuid,
                message_type    = MessageType.CHAT,
                content         = f"[{message_type.upper()}] {message}",
                sequence_number = max_seq + 1,
                metadata        = {"message_type": message_type},
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)

            # Push to live broadcast queue
            event = {
                "type":         "agent_message",
                "room_id":      _room_id,
                "message_id":   str(msg.id),
                "agent_id":     _agent_id,
                "content":      message,
                "message_type": message_type,
                "timestamp":    datetime.utcnow().isoformat(),
            }
            await BROADCAST_QUEUE.put((_room_id, event))

            return {
                "success":    True,
                "message_id": str(msg.id),
                "room_id":    _room_id,
            }

        finally:
            db.close()

    except Exception as e:
        return {"success": False, "error": str(e)}
