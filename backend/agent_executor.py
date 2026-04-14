"""
AgentExecutor — Background Task Runner

Polls the TaskQueue for PENDING tasks, runs them through AgentBrain,
and broadcasts progress via WebSocket.

Start with:
  asyncio.create_task(start_executor())
"""

import os
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from agent_brain import AgentBrain
from models      import (
    Agent, TaskQueue, TaskStatus, AgentStatus,
    Room, Business, get_current_blackboard_state,
)

logger = logging.getLogger(__name__)

DATABASE_URL  = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/agentworld")
POLL_INTERVAL = float(os.getenv("EXECUTOR_POLL_INTERVAL", "3"))   # seconds
LEASE_TTL     = int(os.getenv("EXECUTOR_LEASE_TTL", "120"))        # seconds

_engine  = create_engine(DATABASE_URL, pool_pre_ping=True)
_Session = sessionmaker(bind=_engine)


def _get_db() -> Session:
    return _Session()


# ------------------------------------------------------------------ #
# WebSocket broadcast helper                                           #
# ------------------------------------------------------------------ #

async def _broadcast(room_id: str, event: dict):
    """Push an event to the room_tool broadcast queue."""
    try:
        from tools.room_tool import BROADCAST_QUEUE
        await BROADCAST_QUEUE.put((room_id, event))
    except Exception as e:
        logger.debug(f"Broadcast error: {e}")


# ------------------------------------------------------------------ #
# Core executor logic                                                  #
# ------------------------------------------------------------------ #

async def _run_task(task_id: uuid.UUID):
    """Claim and execute a single task."""
    db = _get_db()
    try:
        # Re-fetch with lock
        task = db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
        if not task or task.status != TaskStatus.PENDING:
            return

        # Claim it
        task.status       = TaskStatus.CLAIMED
        task.claimed_at   = datetime.utcnow()
        task.lease_expires = datetime.utcnow() + timedelta(seconds=LEASE_TTL)
        db.commit()

        # Get agent config
        agent_row = db.query(Agent).filter(
            Agent.id       == task.agent_id,
            Agent.is_active.isnot(False),  # compatibility
        ).first() if task.agent_id else None

        if not agent_row:
            # No specific agent — look for first available
            business_id  = task.business_id
            agent_row    = db.query(Agent).filter(
                Agent.business_id == business_id,
                Agent.status.in_([AgentStatus.IDLE, AgentStatus.ONLINE]),
            ).first()

        if not agent_row:
            # Return to pending
            task.status = TaskStatus.PENDING
            db.commit()
            logger.warning(f"No agent available for task {task_id}")
            return

        agent_config = {
            "id":           str(agent_row.id),
            "name":         agent_row.name,
            "role":         agent_row.agent_type,
            "system_prompt": agent_row.config.get("system_prompt", ""),
            "capabilities": agent_row.capabilities or [],
            "config":       agent_row.config or {},
        }

        # Get room blackboard context
        room_context = {}
        if task.room_id:
            try:
                room_context = get_current_blackboard_state(db, task.room_id)
            except Exception:
                room_context = {}

        # Update task to RUNNING
        task.status = TaskStatus.RUNNING
        db.commit()

        room_id_str = str(task.room_id) if task.room_id else ""

        # Broadcast: agent started
        await _broadcast(room_id_str, {
            "type":      "task_started",
            "task_id":   str(task.id),
            "agent_id":  str(agent_row.id),
            "agent_name": agent_row.name,
            "task_title": task.payload.get("title", task.task_type),
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Mark agent busy
        agent_row.status       = AgentStatus.BUSY
        agent_row.current_load = (agent_row.current_load or 0) + 1
        db.commit()

        logger.info(f"[Executor] Running task {task_id} with agent {agent_row.name}")

        # ---- Run the brain ----
        brain  = AgentBrain(agent_config)
        result = await brain.run(
            task={
                "id":        str(task.id),
                "room_id":   room_id_str,
                "task_type": task.task_type,
                "title":     task.payload.get("title", task.task_type),
                "payload":   task.payload,
            },
            room_context=room_context,
        )

        # ---- Store result ----
        task.status       = TaskStatus.COMPLETED if result["status"] == "completed" else TaskStatus.FAILED
        task.result       = result
        task.completed_at = datetime.utcnow()
        task.lease_expires = None

        agent_row.status       = AgentStatus.IDLE
        agent_row.current_load = max(0, (agent_row.current_load or 1) - 1)
        db.commit()

        # Broadcast: task completed
        await _broadcast(room_id_str, {
            "type":      "task_completed",
            "task_id":   str(task.id),
            "agent_id":  str(agent_row.id),
            "agent_name": agent_row.name,
            "status":    task.status.value,
            "output":    result.get("output", "")[:500],  # truncate for WS
            "steps":     result.get("steps", 0),
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.info(f"[Executor] Task {task_id} → {task.status.value}")

    except Exception as e:
        logger.error(f"[Executor] Task {task_id} failed: {e}", exc_info=True)
        try:
            task = db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
            if task:
                task.status        = TaskStatus.FAILED
                task.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def _poll_loop():
    """Main polling loop — finds PENDING tasks and runs them."""
    logger.info("[Executor] Polling loop started.")
    while True:
        try:
            db = _get_db()
            try:
                pending = db.query(TaskQueue).filter(
                    TaskQueue.status == TaskStatus.PENDING
                ).order_by(
                    TaskQueue.priority.desc(),
                    TaskQueue.created_at.asc(),
                ).limit(5).all()

                task_ids = [t.id for t in pending]
            finally:
                db.close()

            # Fire off each task concurrently (up to 5)
            if task_ids:
                await asyncio.gather(*[_run_task(tid) for tid in task_ids])

        except Exception as e:
            logger.error(f"[Executor] Poll error: {e}", exc_info=True)

        await asyncio.sleep(POLL_INTERVAL)


# ------------------------------------------------------------------ #
# Public entry-point                                                   #
# ------------------------------------------------------------------ #

_executor_task: Optional[asyncio.Task] = None


async def start_executor():
    """Start the background executor. Call once at app startup."""
    global _executor_task
    if _executor_task is None or _executor_task.done():
        _executor_task = asyncio.create_task(_poll_loop())
        logger.info("[Executor] Started.")
    return _executor_task


def stop_executor():
    """Cancel the executor gracefully."""
    global _executor_task
    if _executor_task and not _executor_task.done():
        _executor_task.cancel()
        logger.info("[Executor] Stopped.")
