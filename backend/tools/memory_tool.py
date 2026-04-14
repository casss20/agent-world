"""
Tool: memory_tool
Agents can save and recall memories across sessions.
Backed by the AgentMemory DB table.
"""

import os
import json
from typing import Any, Dict, Optional
from datetime import datetime


def _get_db():
    """Get a fresh DB session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/agentworld")
    engine       = create_engine(DATABASE_URL)
    Session      = sessionmaker(bind=engine)
    return Session()


async def save_memory(
    key:         str,
    value:       str,
    memory_type: str = "long_term",
    _agent_id:   str = "",
    _task_id:    str = "",
    _room_id:    str = "",
) -> Dict[str, Any]:
    """Save a memory entry for the agent."""
    if not _agent_id:
        return {"success": False, "error": "No agent_id provided"}

    try:
        import uuid
        from models import AgentMemory

        db = _get_db()
        try:
            agent_uuid = uuid.UUID(_agent_id)

            # Upsert: update if exists, insert if not
            existing = db.query(AgentMemory).filter(
                AgentMemory.agent_id   == agent_uuid,
                AgentMemory.key        == key,
                AgentMemory.memory_type == memory_type,
            ).first()

            if existing:
                existing.value       = {"data": value}
                existing.accessed_at = datetime.utcnow()
            else:
                mem = AgentMemory(
                    agent_id    = agent_uuid,
                    key         = key,
                    value       = {"data": value},
                    memory_type = memory_type,
                    importance  = 5,
                )
                db.add(mem)

            db.commit()
            return {"success": True, "key": key, "memory_type": memory_type}

        finally:
            db.close()

    except Exception as e:
        return {"success": False, "error": str(e)}


async def load_memory(
    key:         str,
    memory_type: str = "long_term",
    _agent_id:   str = "",
    _task_id:    str = "",
    _room_id:    str = "",
) -> Dict[str, Any]:
    """Recall a saved memory entry."""
    if not _agent_id:
        return {"success": False, "error": "No agent_id provided"}

    try:
        import uuid
        from models import AgentMemory

        db = _get_db()
        try:
            agent_uuid = uuid.UUID(_agent_id)

            mem = db.query(AgentMemory).filter(
                AgentMemory.agent_id    == agent_uuid,
                AgentMemory.key         == key,
                AgentMemory.memory_type == memory_type,
            ).first()

            if not mem:
                return {"success": False, "found": False, "key": key}

            # Update last access
            mem.accessed_at = datetime.utcnow()
            db.commit()

            value = mem.value.get("data", mem.value) if isinstance(mem.value, dict) else mem.value
            return {"success": True, "found": True, "key": key, "value": value}

        finally:
            db.close()

    except Exception as e:
        return {"success": False, "error": str(e)}
