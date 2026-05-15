"""
Agent Chat Routes
API endpoints for individual agent conversations, task assignment, and history.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from database import get_db
from services.agent_chat_service import get_agent_chat_service, list_all_roles
from agents.roles.role_definitions import get_role

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ── Agent Management ─────────────────────────────────────────────────────


@router.get("/", response_model=dict)
async def list_agents():
    """List all available role-based agents."""
    roles = list_all_roles()
    return {
        "agents": [
            {
                "id": r.id,
                "name": r.name,
                "role": r.role,
                "emoji": r.avatar_emoji,
                "goal": r.goal,
                "responsibilities": r.responsibilities[:3],
            }
            for r in roles
        ]
    }


@router.get("/{agent_id}", response_model=dict)
async def get_agent(agent_id: str):
    """Get details for a specific agent."""
    role = get_role(agent_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {
        "id": role.id,
        "name": role.name,
        "role": role.role,
        "emoji": role.avatar_emoji,
        "goal": role.goal,
        "backstory": role.backstory,
        "responsibilities": role.responsibilities,
        "escalation_rules": role.escalation_rules,
        "allowed_tools": role.allowed_tools,
        "priority": role.priority,
    }


# ── Chat ─────────────────────────────────────────────────────────────────


@router.post("/{agent_id}/chat", response_model=dict)
async def chat_with_agent(
    agent_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Send a message to an agent and get a response."""
    service = get_agent_chat_service()
    result = await service.chat(
        db=db,
        agent_id=agent_id,
        user_id=payload.get("user_id", "anonymous"),
        message=payload.get("message", ""),
        context=payload.get("context"),
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/{agent_id}/history", response_model=dict)
async def get_agent_history(
    agent_id: str,
    user_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get conversation history with a specific agent."""
    service = get_agent_chat_service()
    history = await service.get_history(db, agent_id, user_id, limit)
    return {"agent_id": agent_id, "history": history}


@router.get("/conversations/all", response_model=dict)
async def get_all_conversations(
    user_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get all conversations grouped by agent."""
    service = get_agent_chat_service()
    conversations = await service.get_all_conversations(db, user_id, limit)
    return {"user_id": user_id, "conversations": conversations}


# ── Task Assignment ────────────────────────────────────────────────────────


@router.post("/{agent_id}/task", response_model=dict)
async def assign_task_to_agent(
    agent_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Assign a task to a specific agent."""
    service = get_agent_chat_service()
    result = await service.assign_task(
        db=db,
        agent_id=agent_id,
        user_id=payload.get("user_id", "anonymous"),
        task_description=payload.get("description", ""),
        priority=payload.get("priority", "medium"),
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/{agent_id}/tasks", response_model=dict)
async def get_agent_tasks(
    agent_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get tasks assigned to a specific agent."""
    service = get_agent_chat_service()
    tasks = await service.get_agent_tasks(db, agent_id, status)
    return {"agent_id": agent_id, "tasks": tasks}


# ── WebSocket Real-Time Chat ───────────────────────────────────────────


@router.websocket("/{agent_id}/ws")
async def agent_websocket(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for real-time agent chat."""
    role = get_role(agent_id)
    if not role:
        await websocket.close(code=4004, reason=f"Agent '{agent_id}' not found")
        return

    await websocket.accept()
    try:
        await websocket.send_json({
            "type": "connected",
            "agent": {
                "id": role.id,
                "name": role.name,
                "role": role.role,
                "emoji": role.avatar_emoji,
            }
        })

        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            user_id = data.get("user_id", "anonymous")

            # Placeholder response (would integrate with LLM)
            response = (
                f"[{role.name}] I received: '{message}'. "
                f"As {role.role}, I'm here to help with: {', '.join(role.responsibilities[:2])}."
            )

            await websocket.send_json({
                "type": "message",
                "agent_id": agent_id,
                "message": message,
                "response": response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "error": str(e)})
        await websocket.close()
