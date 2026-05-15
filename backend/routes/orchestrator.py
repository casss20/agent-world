"""
Orchestrator Routes
API endpoints for swarm execution, monitoring, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from services.orchestrator_service import get_swarm_orchestrator

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


# ── Swarm Management ─────────────────────────────────────────────────────


@router.post("/swarm/spawn", response_model=dict)
async def spawn_swarm(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Spawn a swarm of agents to work on a complex task."""
    orchestrator = get_swarm_orchestrator()
    result = await orchestrator.spawn_swarm(
        db=db,
        task_description=payload.get("description", ""),
        complexity=payload.get("complexity", "medium"),
        framework=payload.get("framework", "native"),
    )
    return result


@router.get("/swarm/{swarm_id}/status", response_model=dict)
async def get_swarm_status(
    swarm_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the current status of a swarm execution."""
    orchestrator = get_swarm_orchestrator()
    status = await orchestrator.get_swarm_status(db, swarm_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")
    return status


@router.get("/swarms", response_model=dict)
async def list_swarms(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all swarm executions."""
    orchestrator = get_swarm_orchestrator()
    swarms = await orchestrator.list_active_swarms(db, limit)
    return {"swarms": swarms, "count": len(swarms)}


@router.get("/metrics", response_model=dict)
async def get_orchestrator_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate swarm metrics."""
    orchestrator = get_swarm_orchestrator()
    metrics = await orchestrator.get_swarm_metrics(db)
    return metrics


# ── WebSocket Monitoring ─────────────────────────────────────────────────


@router.websocket("/ws/monitor/{swarm_id}")
async def swarm_monitor_websocket(websocket: WebSocket, swarm_id: str):
    """WebSocket endpoint for real-time swarm monitoring."""
    await websocket.accept()
    try:
        await websocket.send_json({
            "type": "connected",
            "swarm_id": swarm_id,
            "message": "Monitoring started",
        })

        # Send periodic updates
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "status")

            if action == "status":
                await websocket.send_json({
                    "type": "status_update",
                    "swarm_id": swarm_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except Exception:
        pass
    finally:
        await websocket.close()
