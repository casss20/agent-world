"""
Background Task Worker
Async job queue with retry, scheduling, and dead-letter handling.

Adapted from Ruflo pattern: WorkflowEngine background execution + retry logic.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, and_

from models import TaskQueue
from utils.retry import retry_with_backoff, RetryExhaustedError
from infrastructure.interfaces.base_storage_provider import BaseStorageProvider
from infrastructure.interfaces.base_queue_provider import BaseQueueProvider

logger = logging.getLogger(__name__)


@dataclass
class JobSpec:
    """Specification for a background job."""
    task_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1 = highest
    max_attempts: int = 3
    scheduled_at: Optional[datetime] = None


class BackgroundWorker:
    """
    Async background task worker with:
    - Priority queue
    - Exponential backoff retry
    - Dead-letter queue for exhausted jobs
    - Graceful shutdown
    - Concurrent execution limit
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        poll_interval: float = 1.0,
        storage_provider: Optional[BaseStorageProvider] = None,
        queue_provider: Optional[BaseQueueProvider] = None,
    ):
        self.max_concurrent = max_concurrent
        self.poll_interval = poll_interval
        self.storage_provider = storage_provider
        self.queue_provider = queue_provider
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._metrics = {
            "processed": 0,
            "failed": 0,
            "retried": 0,
            "dead_lettered": 0,
        }

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the worker loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._work_loop())
            logger.info("Background worker started (max_concurrent=%d)", self.max_concurrent)

    async def stop(self) -> None:
        """Gracefully stop the worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background worker stopped")

    # ── Handlers ────────────────────────────────────────────────────────────

    def register(self, task_type: str, handler: Callable) -> None:
        """Register a handler for a task type."""
        self._handlers[task_type] = handler
        logger.info("Registered handler for task_type=%s", task_type)

    # ── Job Submission ────────────────────────────────────────────────────────

    async def submit(
        self,
        db: AsyncSession,
        spec: JobSpec,
    ) -> str:
        """Submit a job to the queue."""
        job = TaskQueue(
            id=str(uuid.uuid4()),
            task_type=spec.task_type,
            payload=spec.payload,
            priority=spec.priority,
            max_attempts=spec.max_attempts,
            scheduled_at=spec.scheduled_at or datetime.now(timezone.utc),
            status="pending",
            attempts=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)
        logger.info("Job submitted: %s (type=%s)", job.id, spec.task_type)
        return job.id

    async def submit_now(
        self,
        db: AsyncSession,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 5,
    ) -> str:
        """Convenience: submit a job with immediate execution."""
        return await self.submit(
            db,
            JobSpec(
                task_type=task_type,
                payload=payload,
                priority=priority,
                scheduled_at=datetime.now(timezone.utc),
            ),
        )

    # ── Core Loop ───────────────────────────────────────────────────────────

    async def _work_loop(self) -> None:
        """Main worker loop: poll, execute, update."""
        while self._running:
            try:
                await self._process_batch()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker loop error: %s", e)
                await asyncio.sleep(self.poll_interval * 2)

    async def _process_batch(self) -> None:
        """Fetch and process a batch of pending jobs."""
        from database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            # Fetch pending jobs sorted by priority, then scheduled time
            result = await db.execute(
                select(TaskQueue)
                .where(
                    and_(
                        TaskQueue.status.in_(["pending", "failed"]),
                        TaskQueue.attempts < TaskQueue.max_attempts,
                        TaskQueue.scheduled_at <= datetime.now(timezone.utc),
                    )
                )
                .order_by(TaskQueue.priority.asc(), TaskQueue.scheduled_at.asc())
                .limit(self.max_concurrent)
            )
            jobs = result.scalars().all()

            if not jobs:
                return

            # Process concurrently up to semaphore limit
            tasks = [
                asyncio.create_task(self._execute_with_semaphore(db, job))
                for job in jobs
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_with_semaphore(
        self, db: AsyncSession, job: TaskQueue
    ) -> None:
        """Execute a job under the concurrency semaphore."""
        async with self._semaphore:
            await self._execute_job(db, job)

    async def _execute_job(self, db: AsyncSession, job: TaskQueue) -> None:
        """Execute a single job with retry logic."""
        handler = self._handlers.get(job.task_type)
        if not handler:
            logger.warning("No handler for task_type=%s", job.task_type)
            job.status = "dead_letter"
            job.error = f"No handler registered for {job.task_type}"
            await db.flush()
            self._metrics["dead_lettered"] += 1
            return

        job.status = "active"
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        await db.flush()

        try:
            @retry_with_backoff(
                max_retries=job.max_attempts - job.attempts,
                base_delay=2.0,
                retryable_exceptions=(Exception,),
            )
            async def _run():
                return await handler(job.payload)

            result = await _run()

            job.status = "completed"
            job.result = result if isinstance(result, dict) else {"result": result}
            job.completed_at = datetime.now(timezone.utc)
            await db.flush()

            self._metrics["processed"] += 1
            logger.info("Job %s completed (%s)", job.id, job.task_type)

        except RetryExhaustedError:
            job.status = "dead_letter"
            job.error = "Max retry attempts exhausted"
            await db.flush()
            self._metrics["dead_lettered"] += 1
            logger.error("Job %s dead-lettered", job.id)

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            await db.flush()
            self._metrics["failed"] += 1
            logger.error("Job %s failed: %s", job.id, e)

    # ── Queries ─────────────────────────────────────────────────────────────

    async def get_job_status(self, db: AsyncSession, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job."""
        result = await db.execute(select(TaskQueue).where(TaskQueue.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return None
        return {
            "id": job.id,
            "task_type": job.task_type,
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "error": job.error,
            "result": job.result,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    async def list_dead_letter(self, db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
        """List dead-lettered jobs."""
        result = await db.execute(
            select(TaskQueue)
            .where(TaskQueue.status == "dead_letter")
            .order_by(desc(TaskQueue.created_at))
            .limit(limit)
        )
        jobs = result.scalars().all()
        return [
            {
                "id": j.id,
                "task_type": j.task_type,
                "error": j.error,
                "attempts": j.attempts,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]

    def get_metrics(self) -> Dict[str, int]:
        """Get worker processing metrics."""
        return dict(self._metrics)


# ── Global Instance ─────────────────────────────────────────────────────────
background_worker = BackgroundWorker()
