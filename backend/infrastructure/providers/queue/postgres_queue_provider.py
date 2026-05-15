"""Postgres queue provider."""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from infrastructure.interfaces.base_queue_provider import BaseQueueProvider


class PostgresQueueProvider(BaseQueueProvider):
    """PostgreSQL-backed queue provider using TaskQueue table."""

    def __init__(self, db_session=None):
        self._db = db_session
        self._dead: List[Dict[str, Any]] = []

    async def enqueue(self, task: Dict[str, Any], priority: int = 0, queue_name: str = "default") -> str:
        if self._db is None:
            return "no-db"
        from models import TaskQueue
        task_id = str(uuid.uuid4())
        job = TaskQueue(
            id=task_id,
            task_type=queue_name,
            payload=task,
            priority=priority,
            status="pending",
            attempts=0,
            created_at=datetime.utcnow(),
        )
        self._db.add(job)
        await self._db.flush()
        return task_id

    async def dequeue(self, queue_name: str = "default") -> Optional[Dict[str, Any]]:
        if self._db is None:
            return None
        from models import TaskQueue
        from sqlalchemy import select, asc
        result = await self._db.execute(
            select(TaskQueue)
            .where(TaskQueue.task_type == queue_name, TaskQueue.status == "pending")
            .order_by(asc(TaskQueue.priority), asc(TaskQueue.created_at))
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if job:
            job.status = "active"
            job.started_at = datetime.utcnow()
            await self._db.flush()
            return {"id": job.id, **job.payload, "priority": job.priority}
        return None

    async def acknowledge(self, task_id: str) -> bool:
        if self._db is None:
            return False
        from models import TaskQueue
        job = await self._db.get(TaskQueue, task_id)
        if job:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            await self._db.flush()
            return True
        return False

    async def dead_letter(self, task_id: str, reason: str) -> bool:
        if self._db is None:
            return False
        from models import TaskQueue
        job = await self._db.get(TaskQueue, task_id)
        if job:
            job.status = "dead_letter"
            job.error = reason
            await self._db.flush()
            return True
        self._dead.append({"id": task_id, "reason": reason})
        return True

    async def queue_depth(self, queue_name: str = "default") -> int:
        if self._db is None:
            return 0
        from models import TaskQueue
        from sqlalchemy import select, func
        result = await self._db.execute(
            select(func.count(TaskQueue.id))
            .where(TaskQueue.task_type == queue_name, TaskQueue.status == "pending")
        )
        return result.scalar() or 0

    async def health_check(self) -> bool:
        return self._db is not None
