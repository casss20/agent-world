"""
Tasks Router
REST API for task CRUD, execution, handoff, and workflow management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional, Any

from database import get_db
from services.task_service import TaskService
from ledger_client import LedgerClient
from utils.rate_limiter import rate_limit_dependency

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
ledger = None  # Initialized per-request to avoid missing db_session at module load


# ── Task CRUD ───────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    room_id: str,
    owner_agent_id: str,
    title: str,
    task_type: str,
    description: str = "",
    estimated_impact: int = 0,
    priority: str = "medium",
    depends_on: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Create a new task in a room."""
    service = TaskService(None)
    task = await service.create_task(
        db, room_id, owner_agent_id, title, task_type,
        description, estimated_impact, priority, depends_on, metadata
    )
    return {
        "id": task.id,
        "title": task.title,
        "type": task_type,
        "owner": owner_agent_id,
        "status": task.status,
        "priority": priority,
        "estimated_impact": estimated_impact,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get task details."""
    service = TaskService(None)
    task = await service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "type": task.task_type,
        "status": task.status,
        "priority": task.priority,
        "owner": task.owner_agent_id,
        "depends_on": task.depends_on,
        "estimated_impact": task.estimated_impact,
        "metadata": task.metadata,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.get("/room/{room_id}")
async def list_room_tasks(
    room_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List tasks in a room."""
    service = TaskService(None)
    tasks = await service.list_room_tasks(db, room_id, status)
    return [
        {
            "id": t.id,
            "title": t.title,
            "type": t.task_type,
            "status": t.status,
            "priority": t.priority,
            "owner": t.owner_agent_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


# ── Task Execution ──────────────────────────────────────────────────────────

@router.post("/{task_id}/execute")
async def execute_task(
    task_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Execute a task with the specified agent."""
    service = TaskService(None)
    result = await service.execute_task(db, task_id, agent_id)
    return result


@router.post("/{task_id}/transition")
async def transition_task(
    task_id: str,
    agent_id: str,
    new_status: str,
    reason: str = "",
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Transition task status (with validation)."""
    service = TaskService(None)
    try:
        task = await service.transition_status(db, task_id, new_status, agent_id, reason)
        return {
            "task_id": task.id,
            "status": task.status,
            "previous_status": task.metadata.get("previous_status"),
            "transitioned_by": agent_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Handoff ─────────────────────────────────────────────────────────────────

@router.post("/{task_id}/handoff")
async def handoff_task(
    task_id: str,
    from_agent_id: str,
    to_agent_id: str,
    context: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Handoff task to another agent with context preservation."""
    service = TaskService(None)
    result = await service.handoff_task(db, task_id, from_agent_id, to_agent_id, context)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ── Workflow ────────────────────────────────────────────────────────────────

@router.post("/workflow/execute/{room_id}")
async def execute_workflow(
    room_id: str,
    task_ids: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Execute a workflow: resolve dependencies and run tasks in order.
    If task_ids provided, only those tasks. Otherwise all room tasks.
    """
    service = TaskService(None)
    try:
        results = await service.execute_workflow(db, room_id, task_ids)
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}/metrics")
async def get_task_metrics(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get execution metrics for a task."""
    service = TaskService(None)
    metrics = await service.get_task_metrics(db, task_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Task not found")
    return metrics


@router.get("/{task_id}/history")
async def get_task_history(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get task audit trail (activity log)."""
    from sqlalchemy import select
    from models import Activity

    result = await db.execute(
        select(Activity)
        .where(Activity.details.contains({"task_id": task_id}))
        .order_by(Activity.created_at.desc())
    )
    activities = result.scalars().all()

    return [
        {
            "timestamp": a.created_at.isoformat() if a.created_at else None,
            "agent_id": a.agent_id,
            "action": a.action,
            "details": a.details,
        }
        for a in activities
    ]
