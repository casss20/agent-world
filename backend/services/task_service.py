"""
Task Service
Task lifecycle, workflow execution, handoff, and Ledger governance integration.

Integrates with: models.py (Task), ledger_client.py, agent_brain.py
Adapted from Ruflo pattern: WorkflowEngine (dependency resolution, rollback, metrics).
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, desc

from models import Task, Room, Agent, Activity
from ledger_client import LedgerClient
from infrastructure.interfaces.base_storage_provider import BaseStorageProvider
from utils.retry import retry_with_backoff
from websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# Task status transitions
VALID_TRANSITIONS = {
    "pending": ["active", "cancelled"],
    "active": ["paused", "completed", "failed", "handed_off"],
    "paused": ["active", "cancelled"],
    "handed_off": ["active", "completed", "failed"],
    "completed": [],
    "failed": ["active"],
    "cancelled": ["active"],
    "approved": ["active", "rejected"],
    "rejected": ["pending"],
}


class TaskService:
    """
    Manages task lifecycle with:
    - CRUD operations
    - Status transitions with validation
    - Task dependencies and workflow resolution
    - Agent handoff with context preservation
    - Ledger governance integration
    - Metrics tracking
    """

    def __init__(self, ledger: Optional[LedgerClient] = None, storage_provider: Optional[BaseStorageProvider] = None, queue_provider: Optional[Any] = None, auth_provider: Optional[Any] = None, repository: Optional[Any] = None):
        self.ledger = ledger
        self.storage_provider = storage_provider
        self.queue_provider = queue_provider
        self.auth_provider = auth_provider
        self.repository = repository
        self._handlers: Dict[str, List[Callable]] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create_task(
        self,
        db: AsyncSession,
        room_id: str,
        owner_agent_id: str,
        title: str,
        task_type: str,
        description: str = "",
        estimated_impact: int = 0,
        priority: str = "medium",
        depends_on: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Create a new task in a room."""
        task = Task(
            id=str(uuid.uuid4()),
            room_id=room_id,
            owner_agent_id=owner_agent_id,
            title=title,
            description=description,
            task_type=task_type,
            status="pending",
            priority=priority,
            estimated_impact=estimated_impact,
            depends_on=depends_on or [],
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)

        # Ledger: log task creation
        if self.ledger:
            try:
                await self.ledger.log_action(
                    action="task_created",
                    agent_id=owner_agent_id,
                    room_id=room_id,
                    details={
                        "task_id": task.id,
                        "title": title,
                        "type": task_type,
                        "impact": estimated_impact,
                    },
                )
            except Exception as e:
                logger.warning("Ledger log failed: %s", e)

        # Notify room
        await ws_manager.broadcast_to_room(
            room_id,
            {
                "type": "task_created",
                "task_id": task.id,
                "title": title,
                "owner": owner_agent_id,
                "priority": priority,
            },
        )

        return task

    async def get_task(self, db: AsyncSession, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        result = await db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def list_room_tasks(
        self, db: AsyncSession, room_id: str, status: Optional[str] = None
    ) -> List[Task]:
        """List tasks in a room, optionally filtered by status."""
        query = (
            select(Task)
            .where(Task.room_id == room_id)
            .order_by(desc(Task.created_at))
        )
        if status:
            query = query.where(Task.status == status)
        result = await db.execute(query)
        return list(result.scalars().all())

    # ── Status Transitions ────────────────────────────────────────────────────

    async def transition_status(
        self,
        db: AsyncSession,
        task_id: str,
        new_status: str,
        agent_id: str,
        reason: str = "",
    ) -> Task:
        """
        Transition task status with validation.
        Raises ValueError if transition is invalid.
        """
        task = await self.get_task(db, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        current = task.status
        allowed = VALID_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {current} -> {new_status}. Allowed: {allowed}"
            )

        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)

        # Log activity
        activity = Activity(
            id=str(uuid.uuid4()),
            room_id=task.room_id,
            agent_id=agent_id,
            action=f"task_{new_status}",
            details={
                "task_id": task_id,
                "previous_status": current,
                "new_status": new_status,
                "reason": reason,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(activity)
        await db.flush()

        # Notify
        await ws_manager.broadcast_to_room(
            task.room_id,
            {
                "type": "task_status_change",
                "task_id": task_id,
                "status": new_status,
                "agent_id": agent_id,
                "reason": reason,
            },
        )

        return task

    # ── Task Execution ──────────────────────────────────────────────────────

    @retry_with_backoff(
        max_retries=2,
        base_delay=1.0,
        retryable_exceptions=(ConnectionError, TimeoutError),
    )
    async def execute_task(
        self,
        db: AsyncSession,
        task_id: str,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        Execute a task with an agent.
        Includes dependency checks, Ledger approval, and metrics.
        """
        task = await self.get_task(db, task_id)
        if not task:
            return {"status": "failed", "error": "Task not found"}

        # Check dependencies
        if task.depends_on:
            for dep_id in task.depends_on:
                dep = await self.get_task(db, dep_id)
                if not dep or dep.status != "completed":
                    return {
                        "status": "blocked",
                        "error": f"Dependency {dep_id} not completed",
                        "task_id": task_id,
                    }

        # Ledger approval for high-impact tasks
        if task.estimated_impact > 50 and self.ledger:
            try:
                approval = await self.ledger.request_approval(
                    task_id=task_id,
                    agent_id=agent_id,
                    reason=f"High-impact task: {task.title}",
                )
                if approval.get("status") != "approved":
                    return {
                        "status": "pending_approval",
                        "approval_id": approval.get("id"),
                        "task_id": task_id,
                    }
            except Exception as e:
                logger.warning("Ledger approval check failed: %s", e)

        # Transition to active
        await self.transition_status(db, task_id, "active", agent_id)

        start_time = datetime.now(timezone.utc)
        try:
            # Execute via agent brain (or other executor)
            result = await self._execute_with_agent(task, agent_id)

            # Mark completed
            await self.transition_status(db, task_id, "completed", agent_id)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Update metrics
            task.metadata["execution_count"] = task.metadata.get("execution_count", 0) + 1
            task.metadata["last_duration"] = duration
            task.metadata["average_duration"] = self._update_average(
                task.metadata.get("average_duration", 0),
                task.metadata["execution_count"],
                duration,
            )
            await db.flush()

            return {
                "status": "completed",
                "task_id": task_id,
                "agent_id": agent_id,
                "duration": duration,
                "result": result,
            }

        except Exception as e:
            logger.error("Task execution failed: %s", e)
            await self.transition_status(db, task_id, "failed", agent_id, reason=str(e))
            return {
                "status": "failed",
                "task_id": task_id,
                "agent_id": agent_id,
                "error": str(e),
            }

    async def _execute_with_agent(
        self, task: Task, agent_id: str
    ) -> Dict[str, Any]:
        """Dispatch task execution to the appropriate handler."""
        handlers = self._handlers.get(task.task_type, [])
        if not handlers:
            # Default: simulate execution
            import asyncio
            await asyncio.sleep(0.5)
            return {"message": f"Task '{task.title}' executed by {agent_id}"}

        # Call first registered handler
        return await handlers[0](task, agent_id)

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """Register a handler for a specific task type."""
        if task_type not in self._handlers:
            self._handlers[task_type] = []
        self._handlers[task_type].append(handler)

    # ── Handoff ───────────────────────────────────────────────────────────────

    async def handoff_task(
        self,
        db: AsyncSession,
        task_id: str,
        from_agent_id: str,
        to_agent_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transfer task ownership with context preservation.
        Ledger-validated for security.
        """
        task = await self.get_task(db, task_id)
        if not task:
            return {"success": False, "error": "Task not found"}

        if task.owner_agent_id != from_agent_id:
            return {"success": False, "error": "Only the owner can handoff"}

        # Ledger validation
        if self.ledger:
            try:
                valid = await self.ledger.validate_handoff(
                    task_id=task_id,
                    from_agent=from_agent_id,
                    to_agent=to_agent_id,
                )
                if not valid:
                    return {"success": False, "error": "Handoff not authorized by Ledger"}
            except Exception as e:
                logger.warning("Ledger handoff validation failed: %s", e)

        # Preserve context
        handoff_context = {
            "previous_owner": from_agent_id,
            "handoff_at": datetime.now(timezone.utc).isoformat(),
            "previous_context": task.metadata.get("context", {}),
            "new_context": context or {},
        }

        task.owner_agent_id = to_agent_id
        task.status = "handed_off"
        task.metadata["handoff_history"] = task.metadata.get("handoff_history", [])
        task.metadata["handoff_history"].append(handoff_context)
        task.metadata["context"] = context or {}
        task.updated_at = datetime.now(timezone.utc)
        await db.flush()

        # Notify
        await ws_manager.broadcast_to_room(
            task.room_id,
            {
                "type": "task_handoff",
                "task_id": task_id,
                "from": from_agent_id,
                "to": to_agent_id,
                "context": context,
            },
        )

        return {
            "success": True,
            "task_id": task_id,
            "from": from_agent_id,
            "to": to_agent_id,
            "context": handoff_context,
        }

    # ── Aliases for compatibility ───────────────────────────────────────────
    async def update_task_status(
        self, db: AsyncSession, task_id: str, new_status: str, **kwargs
    ) -> Task:
        """Alias for transition_status."""
        return await self.transition_status(
            db, task_id, new_status,
            agent_id=kwargs.get("agent_id", "system"),
            reason=kwargs.get("reason", ""),
        )

    async def resolve_dependencies(self, db: AsyncSession, task_id: str) -> List[str]:
        """Return dependency IDs for a task in topological order."""
        task = await self.get_task(db, task_id)
        if not task:
            return []

        # BFS/DFS to find all transitive dependencies
        all_deps: List[str] = []
        visited: set = set()
        queue = list(task.depends_on or [])

        while queue:
            dep_id = queue.pop(0)
            if dep_id in visited:
                continue
            visited.add(dep_id)
            dep = await self.get_task(db, dep_id)
            if dep:
                all_deps.append(dep_id)
                queue.extend(dep.depends_on or [])

        all_deps.reverse()  # Reverse to get topological order (deps before dependents)
        return all_deps

    # ── Workflow / Dependencies ─────────────────────────────────────────────

    async def resolve_execution_order(
        self, db: AsyncSession, room_id: str
    ) -> List[Task]:
        """
        Resolve task execution order using topological sort.
        Returns tasks sorted by dependencies.
        """
        tasks = await self.list_room_tasks(db, room_id)

        # Build adjacency list
        task_map = {t.id: t for t in tasks}
        in_degree = {t.id: 0 for t in tasks}
        adj: Dict[str, List[str]] = {t.id: [] for t in tasks}

        for task in tasks:
            for dep_id in task.depends_on or []:
                if dep_id in task_map:
                    adj[dep_id].append(task.id)
                    in_degree[task.id] += 1

        # Kahn's algorithm
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            # Sort by priority
            queue.sort(
                key=lambda tid: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(
                    task_map[tid].priority, 2
                )
            )
            tid = queue.pop(0)
            order.append(tid)

            for neighbor in adj[tid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(tasks):
            raise ValueError("Cyclic dependency detected in tasks")

        return [task_map[tid] for tid in order]

    async def execute_workflow(
        self,
        db: AsyncSession,
        room_id: str,
        task_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a workflow: resolve dependencies and run tasks in order.
        Adapted from Ruflo WorkflowEngine pattern.
        """
        if task_ids:
            # Get specific tasks
            tasks = []
            for tid in task_ids:
                task = await self.get_task(db, tid)
                if task:
                    tasks.append(task)
        else:
            # All tasks in room
            tasks = await self.list_room_tasks(db, room_id)

        ordered = await self.resolve_execution_order(db, room_id)
        # Filter to requested tasks if specified
        if task_ids:
            ordered = [t for t in ordered if t.id in task_ids]

        results: List[Dict[str, Any]] = []
        for task in ordered:
            result = await self.execute_task(db, task.id, task.owner_agent_id)
            results.append(result)

            if result["status"] == "failed":
                # Stop workflow on failure (could be configured)
                logger.error("Workflow halted: task %s failed", task.id)
                break

        return results

    # ── Metrics ───────────────────────────────────────────────────────────────

    @staticmethod
    def _update_average(current_avg: float, count: int, new_value: float) -> float:
        """Rolling average update."""
        return (current_avg * (count - 1) + new_value) / count

    async def get_task_metrics(
        self, db: AsyncSession, task_id: str
    ) -> Dict[str, Any]:
        """Get execution metrics for a task."""
        task = await self.get_task(db, task_id)
        if not task:
            return {}

        return {
            "task_id": task.id,
            "status": task.status,
            "execution_count": task.metadata.get("execution_count", 0),
            "average_duration": task.metadata.get("average_duration", 0),
            "last_duration": task.metadata.get("last_duration", 0),
            "handoff_count": len(task.metadata.get("handoff_history", [])),
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
