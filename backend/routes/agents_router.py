"""
Agents Router
REST API for agent CRUD, status, and discovery.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Dict, List, Optional, Any

from database import get_db
from models import Agent
from utils.rate_limiter import rate_limit_dependency

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


# ── Agent CRUD ──────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    name: str,
    role: str,
    agent_type: str = "assistant",
    capabilities: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Create a new agent."""
    import uuid
    from datetime import datetime, timezone

    agent = Agent(
        id=str(uuid.uuid4()),
        name=name,
        role=role,
        agent_type=agent_type,
        status="idle",
        capabilities=capabilities or [],
        metadata=metadata or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)

    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "type": agent_type,
        "status": agent.status,
        "capabilities": agent.capabilities,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


@router.get("")
async def list_agents(
    status: Optional[str] = None,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List all agents with optional filtering."""
    query = select(Agent).order_by(desc(Agent.created_at))
    if status:
        query = query.where(Agent.status == status)
    if role:
        query = query.where(Agent.role == role)

    result = await db.execute(query)
    agents = result.scalars().all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "role": a.role,
            "type": a.agent_type,
            "status": a.status,
            "capabilities": a.capabilities,
            "metadata": a.metadata,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in agents
    ]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get agent details."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "type": agent.agent_type,
        "status": agent.status,
        "capabilities": agent.capabilities,
        "metadata": agent.metadata,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    name: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update agent fields."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if name:
        agent.name = name
    if role:
        agent.role = role
    if status:
        agent.status = status
    if capabilities is not None:
        agent.capabilities = capabilities
    if metadata is not None:
        agent.metadata.update(metadata)

    from datetime import datetime, timezone
    agent.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "status": agent.status,
        "capabilities": agent.capabilities,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.delete(agent)
    await db.flush()
    return {"status": "deleted", "agent_id": agent_id}


# ── Status ──────────────────────────────────────────────────────────────────

@router.put("/{agent_id}/status")
async def set_agent_status(
    agent_id: str,
    status: str,  # idle, working, paused, error, offline
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update agent status."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = status
    from datetime import datetime, timezone
    agent.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {"agent_id": agent_id, "status": status}


@router.get("/{agent_id}/rooms")
async def get_agent_rooms(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get rooms this agent is a member of."""
    from models import AgentRoom, Room
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(AgentRoom)
        .where(AgentRoom.agent_id == agent_id)
        .where(AgentRoom.is_active == True)
        .options(selectinload(AgentRoom.room))
    )
    memberships = result.scalars().all()

    return [
        {
            "room_id": m.room.id,
            "room_name": m.room.name,
            "role": m.role,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m in memberships
    ]
