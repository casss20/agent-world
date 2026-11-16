"""
Native Workflow Engine — Agent World
In-house workflow execution with dependency resolution, nested workflows,
rollback, pause/resume, state persistence, event logging, and metrics.

Adapted from Ruflo v3 pattern: WorkflowEngine.ts + Task.ts
Replaces external ChatDev bridge dependency for standalone workflows.
"""

import asyncio
import logging
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
)

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Data classes ───────────────────────────────────────────────────────────


@dataclass
class WorkflowTask:
    """A task inside a workflow — with dependency resolution and lifecycle."""

    id: str
    type: str  # e.g. 'code', 'test', 'review', 'design', 'deploy', 'workflow'
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    nested_workflow: Optional["WorkflowDefinition"] = None
    on_execute: Optional[Callable[["WorkflowTask"], Awaitable[Any]]] = None
    on_rollback: Optional[Callable[["WorkflowTask"], Awaitable[Any]]] = None

    _started_at: Optional[float] = field(default=None, repr=False)
    _completed_at: Optional[float] = field(default=None, repr=False)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.IN_PROGRESS
            self._started_at = datetime.now(timezone.utc).timestamp()

    def complete(self) -> None:
        if self.status == TaskStatus.IN_PROGRESS:
            self.status = TaskStatus.COMPLETED
            self._completed_at = datetime.now(timezone.utc).timestamp()

    def fail(self, error: Optional[str] = None) -> None:
        self.status = TaskStatus.FAILED
        self._completed_at = datetime.now(timezone.utc).timestamp()
        if error:
            self.metadata["error"] = error

    def cancel(self) -> None:
        if self.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            self.status = TaskStatus.CANCELLED
            self._completed_at = datetime.now(timezone.utc).timestamp()

    def is_workflow(self) -> bool:
        return self.type == "workflow" and self.nested_workflow is not None

    def get_duration_ms(self) -> Optional[float]:
        if self._started_at and self._completed_at:
            return (self._completed_at - self._started_at) * 1000
        if self._started_at:
            return (datetime.now(timezone.utc).timestamp() - self._started_at) * 1000
        return None

    def get_priority_value(self) -> int:
        mapping = {TaskPriority.HIGH: 3, TaskPriority.MEDIUM: 2, TaskPriority.LOW: 1}
        return mapping.get(self.priority, 2)

    def are_dependencies_resolved(self, completed_ids: Set[str]) -> bool:
        return all(dep in completed_ids for dep in self.dependencies)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "dependencies": self.dependencies,
            "metadata": {
                **self.metadata,
                "started_at": self._started_at,
                "completed_at": self._completed_at,
                "duration_ms": self.get_duration_ms(),
            },
        }
        if self.nested_workflow:
            d["nested_workflow"] = self.nested_workflow.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowTask":
        task = cls(
            id=data["id"],
            type=data["type"],
            description=data["description"],
            priority=TaskPriority(data.get("priority", "medium")),
            status=TaskStatus(data.get("status", "pending")),
            assigned_to=data.get("assigned_to"),
            dependencies=data.get("dependencies", []),
            metadata={k: v for k, v in data.get("metadata", {}).items()
                      if k not in ("started_at", "completed_at", "duration_ms")},
        )
        task._started_at = data.get("metadata", {}).get("started_at")
        task._completed_at = data.get("metadata", {}).get("completed_at")
        if "nested_workflow" in data:
            task.nested_workflow = WorkflowDefinition.from_dict(data["nested_workflow"])
        return task

    # ── Static utilities ──────────────────────────────────────────────────

    @staticmethod
    def resolve_execution_order(tasks: List["WorkflowTask"]) -> List["WorkflowTask"]:
        """Topological sort by dependencies, then priority."""
        resolved: List[WorkflowTask] = []
        resolved_ids: Set[str] = set()
        remaining = list(tasks)

        while remaining:
            ready = [t for t in remaining if t.are_dependencies_resolved(resolved_ids)]
            if not ready and remaining:
                raise WorkflowEngineError("Circular dependency detected in workflow tasks")

            # Sort ready tasks by priority (high first)
            ready.sort(key=lambda t: t.get_priority_value(), reverse=True)

            for task in ready:
                resolved.append(task)
                resolved_ids.add(task.id)
                remaining.remove(task)

        return resolved

    @staticmethod
    def sort_by_priority(tasks: List["WorkflowTask"]) -> List["WorkflowTask"]:
        return sorted(tasks, key=lambda t: t.get_priority_value(), reverse=True)


@dataclass
class WorkflowDefinition:
    """Blueprint for a workflow."""

    id: str
    name: str
    tasks: List[WorkflowTask] = field(default_factory=list)
    rollback_on_failure: bool = False
    debug: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tasks": [t.to_dict() for t in self.tasks],
            "rollback_on_failure": self.rollback_on_failure,
            "debug": self.debug,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        return cls(
            id=data["id"],
            name=data["name"],
            tasks=[WorkflowTask.from_dict(t) for t in data.get("tasks", [])],
            rollback_on_failure=data.get("rollback_on_failure", False),
            debug=data.get("debug", False),
        )


@dataclass
class WorkflowState:
    """Mutable runtime state of a workflow execution."""

    id: str
    name: str
    status: WorkflowStatus
    tasks: List[WorkflowTask] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    current_task: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "tasks": [t.to_dict() for t in self.tasks],
            "completed_tasks": self.completed_tasks,
            "current_task": self.current_task,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class TaskResult:
    """Result of a single task execution."""

    task_id: str
    status: str  # 'completed' | 'failed'
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    agent_id: Optional[str] = None


@dataclass
class WorkflowResult:
    """Final result of a workflow execution."""

    id: str
    status: str  # 'completed' | 'failed' | 'cancelled'
    tasks_completed: int = 0
    tasks_failed: int = 0
    errors: List[str] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowMetrics:
    """Performance metrics for a workflow run."""

    tasks_total: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_duration_ms: float = 0.0
    average_task_duration_ms: float = 0.0
    success_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowDebugInfo:
    """Debug/trace information for a workflow run."""

    execution_trace: List[Dict[str, Any]] = field(default_factory=list)
    task_timings: Dict[str, Dict[str, float]] = field(default_factory=dict)
    memory_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    event_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Exceptions ─────────────────────────────────────────────────────────────


class WorkflowEngineError(Exception):
    """Base exception for workflow engine errors."""
    pass


class NoAgentAvailableError(WorkflowEngineError):
    """Raised when no agent is available to execute a task."""
    pass


# ── Workflow Engine ────────────────────────────────────────────────────────


Dispatcher = Callable[[WorkflowTask, str], Awaitable[TaskResult]]
AgentSelector = Callable[[WorkflowTask, List[Dict[str, Any]]], Optional[str]]
StatePersister = Callable[[str, Dict[str, Any]], Awaitable[None]]
StateLoader = Callable[[str], Awaitable[Optional[Dict[str, Any]]]]


@dataclass
class WorkflowExecution:
    """Internal mutable tracking for a single workflow run."""

    id: str
    state: WorkflowState
    execution_order: List[str] = field(default_factory=list)
    task_timings: Dict[str, Dict[str, float]] = field(default_factory=dict)
    event_log: List[Dict[str, Any]] = field(default_factory=list)
    memory_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    results: Dict[str, TaskResult] = field(default_factory=dict)


class WorkflowEngineNative:
    """
    Native workflow execution engine.

    Features:
      - Dependency-aware topological task ordering
      - Nested workflows (task type == 'workflow')
      - Rollback on failure (reverse-order rollback hooks)
      - Pause / resume during execution
      - State persistence (optional callback)
      - Event logging and debug traces
      - Metrics collection
      - Distributed execution across multiple dispatchers

    Usage:
        engine = WorkflowEngineNative(task_dispatcher=my_dispatcher)
        result = await engine.execute_workflow(workflow_def)
    """

    def __init__(
        self,
        *,
        task_dispatcher: Optional[Dispatcher] = None,
        agent_selector: Optional[AgentSelector] = None,
        state_persister: Optional[StatePersister] = None,
        state_loader: Optional[StateLoader] = None,
        plugin_manager: Optional[Any] = None,
    ):
        self._task_dispatcher = task_dispatcher
        self._agent_selector = agent_selector
        self._state_persister = state_persister
        self._state_loader = state_loader
        self._plugin_manager = plugin_manager
        self._workflows: Dict[str, WorkflowExecution] = {}
        self._initialized = False

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        logger.info("WorkflowEngineNative initialized")

    async def shutdown(self) -> None:
        """Cancel all running workflows and clean up."""
        for exec_id, execution in list(self._workflows.items()):
            if execution.state.status == WorkflowStatus.IN_PROGRESS:
                execution.state.status = WorkflowStatus.CANCELLED
                logger.warning("Workflow %s cancelled due to engine shutdown", exec_id)
        self._workflows.clear()
        self._initialized = False
        logger.info("WorkflowEngineNative shutdown")

    # ── Core: Execute Workflow ────────────────────────────────────────────

    async def execute_workflow(self, workflow: WorkflowDefinition) -> WorkflowResult:
        """Execute a workflow to completion."""
        execution = self._create_execution(workflow)
        self._workflows[workflow.id] = execution

        # Plugin hook: before execute
        if self._plugin_manager:
            try:
                await self._plugin_manager.invoke_extension_point(
                    "workflow.beforeExecute", workflow.to_dict()
                )
            except Exception as e:
                logger.warning("Plugin hook workflow.beforeExecute failed: %s", e)

        self._log_event(execution, "workflow:started", {"workflow_id": workflow.id})

        try:
            result = await self._run_workflow(execution, workflow)

            # Final state persistence after completion
            await self.persist_state(workflow.id)

            # Plugin hook: after execute
            if self._plugin_manager:
                try:
                    await self._plugin_manager.invoke_extension_point(
                        "workflow.afterExecute", result.to_dict()
                    )
                except Exception as e:
                    logger.warning("Plugin hook workflow.afterExecute failed: %s", e)

            self._log_event(execution, "workflow:completed", {"workflow_id": workflow.id})
            return result

        except Exception as e:
            error_msg = str(e)
            failed_result = WorkflowResult(
                id=workflow.id,
                status="failed",
                tasks_completed=len(execution.state.completed_tasks),
                tasks_failed=1,
                errors=[error_msg],
                execution_order=execution.execution_order,
            )

            # Plugin hook: on error
            if self._plugin_manager:
                try:
                    await self._plugin_manager.invoke_extension_point(
                        "workflow.onError",
                        {"workflow_id": workflow.id, "error": error_msg},
                    )
                except Exception as pe:
                    logger.warning("Plugin hook workflow.onError failed: %s", pe)

            # Rollback if configured
            if workflow.rollback_on_failure:
                await self._rollback_workflow(execution, workflow)

            self._log_event(
                execution,
                "workflow:failed",
                {"workflow_id": workflow.id, "error": error_msg},
            )
            return failed_result

    async def start_workflow(self, workflow: WorkflowDefinition) -> asyncio.Task[WorkflowResult]:
        """Start a workflow asynchronously — returns an asyncio Task."""
        return asyncio.create_task(self.execute_workflow(workflow))

    # ── Pause / Resume / Cancel ───────────────────────────────────────────

    async def pause_workflow(self, workflow_id: str) -> None:
        execution = self._workflows.get(workflow_id)
        if execution and execution.state.status == WorkflowStatus.IN_PROGRESS:
            execution.state.status = WorkflowStatus.PAUSED
            self._log_event(execution, "workflow:paused", {"workflow_id": workflow_id})
            logger.info("Workflow %s paused", workflow_id)

    async def resume_workflow(self, workflow_id: str) -> None:
        execution = self._workflows.get(workflow_id)
        if execution and execution.state.status == WorkflowStatus.PAUSED:
            execution.state.status = WorkflowStatus.IN_PROGRESS
            self._log_event(execution, "workflow:resumed", {"workflow_id": workflow_id})
            logger.info("Workflow %s resumed", workflow_id)

    async def cancel_workflow(self, workflow_id: str) -> None:
        execution = self._workflows.get(workflow_id)
        if execution and execution.state.status in (
            WorkflowStatus.IN_PROGRESS,
            WorkflowStatus.PAUSED,
        ):
            execution.state.status = WorkflowStatus.CANCELLED
            self._log_event(execution, "workflow:cancelled", {"workflow_id": workflow_id})
            logger.info("Workflow %s cancelled", workflow_id)

    # ── Queries ───────────────────────────────────────────────────────────

    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        execution = self._workflows.get(workflow_id)
        return execution.state if execution else None

    def get_workflow_metrics(self, workflow_id: str) -> Optional[WorkflowMetrics]:
        execution = self._workflows.get(workflow_id)
        if not execution:
            return None

        total = len(execution.state.tasks)
        completed = len(execution.state.completed_tasks)
        durations = [t["duration_ms"] for t in execution.task_timings.values() if "duration_ms" in t]
        total_dur = sum(durations) if durations else 0.0
        avg_dur = total_dur / len(durations) if durations else 0.0

        return WorkflowMetrics(
            tasks_total=total,
            tasks_completed=completed,
            tasks_failed=total - completed,
            total_duration_ms=total_dur,
            average_task_duration_ms=avg_dur,
            success_rate=completed / total if total > 0 else 0.0,
        )

    def get_workflow_debug_info(self, workflow_id: str) -> Optional[WorkflowDebugInfo]:
        execution = self._workflows.get(workflow_id)
        if not execution:
            return None
        return WorkflowDebugInfo(
            execution_trace=[
                {
                    "task_id": tid,
                    "timestamp": execution.task_timings.get(tid, {}).get("start_ms", 0),
                    "action": "execute",
                }
                for tid in execution.execution_order
            ],
            task_timings=execution.task_timings,
            memory_snapshots=execution.memory_snapshots,
            event_log=execution.event_log,
        )

    # ── State Persistence ─────────────────────────────────────────────────

    async def persist_state(self, workflow_id: str) -> None:
        if not self._state_persister:
            return
        execution = self._workflows.get(workflow_id)
        if not execution:
            return
        try:
            await self._state_persister(workflow_id, execution.state.to_dict())
        except Exception as e:
            logger.warning("State persistence failed for %s: %s", workflow_id, e)

    async def restore_state(self, workflow_id: str) -> Optional[WorkflowState]:
        if not self._state_loader:
            return None
        try:
            data = await self._state_loader(workflow_id)
            if not data:
                return None
            # Rehydrate tasks
            tasks = [WorkflowTask.from_dict(t) for t in data.get("tasks", [])]
            state = WorkflowState(
                id=data["id"],
                name=data["name"],
                status=WorkflowStatus(data.get("status", "pending")),
                tasks=tasks,
                completed_tasks=data.get("completed_tasks", []),
                current_task=data.get("current_task"),
                started_at=data.get("started_at"),
                completed_at=data.get("completed_at"),
            )
            return state
        except Exception as e:
            logger.warning("State restore failed for %s: %s", workflow_id, e)
            return None

    # ── Distributed Execution ───────────────────────────────────────────────

    async def execute_distributed(
        self,
        workflow: WorkflowDefinition,
        dispatchers: List[Dispatcher],
    ) -> WorkflowResult:
        """
        Distribute tasks across multiple task dispatchers.
        Each dispatcher is treated as a separate execution pool.
        """
        if not dispatchers:
            raise WorkflowEngineError("No dispatchers provided for distributed execution")

        chunks = self._chunk_tasks(workflow.tasks, len(dispatchers))
        all_results: List[TaskResult] = []
        all_errors: List[str] = []

        async def run_chunk(tasks: List[WorkflowTask], dispatcher: Dispatcher) -> None:
            engine = WorkflowEngineNative(
                task_dispatcher=dispatcher,
                plugin_manager=self._plugin_manager,
            )
            sub_workflow = WorkflowDefinition(
                id=f"{workflow.id}-{uuid.uuid4().hex[:8]}",
                name=f"{workflow.name} (distributed chunk)",
                tasks=tasks,
                rollback_on_failure=workflow.rollback_on_failure,
            )
            result = await engine.execute_workflow(sub_workflow)
            # Aggregate
            for tid in result.execution_order:
                # Find the corresponding task result from the sub-engine
                sub_exec = engine._workflows.get(sub_workflow.id)
                if sub_exec and tid in sub_exec.results:
                    all_results.append(sub_exec.results[tid])
            all_errors.extend(result.errors)

        await asyncio.gather(
            *[run_chunk(chunk, dispatchers[i]) for i, chunk in enumerate(chunks)]
        )

        completed = sum(1 for r in all_results if r.status == "completed")
        status = "completed" if not all_errors else "failed"

        return WorkflowResult(
            id=workflow.id,
            status=status,
            tasks_completed=completed,
            tasks_failed=len(all_results) - completed,
            errors=all_errors,
            execution_order=[r.task_id for r in all_results],
        )

    # ── Private: Execution Core ───────────────────────────────────────────

    def _create_execution(self, workflow: WorkflowDefinition) -> WorkflowExecution:
        return WorkflowExecution(
            id=workflow.id,
            state=WorkflowState(
                id=workflow.id,
                name=workflow.name,
                status=WorkflowStatus.IN_PROGRESS,
                tasks=deepcopy(workflow.tasks),
                started_at=datetime.now(timezone.utc).timestamp(),
            ),
        )

    async def _run_workflow(
        self, execution: WorkflowExecution, workflow: WorkflowDefinition
    ) -> WorkflowResult:
        tasks = execution.state.tasks
        ordered = WorkflowTask.resolve_execution_order(tasks)
        completed_ids: Set[str] = set()
        errors: List[str] = []

        for task in ordered:
            # Check pause
            while execution.state.status == WorkflowStatus.PAUSED:
                await asyncio.sleep(0.1)

            if execution.state.status == WorkflowStatus.CANCELLED:
                break

            execution.state.current_task = task.id
            start_ts = datetime.now(timezone.utc).timestamp()

            try:
                # Nested workflow
                if task.is_workflow() and task.nested_workflow:
                    nested_result = await self.execute_workflow(task.nested_workflow)
                    if nested_result.status == "failed":
                        raise WorkflowEngineError(
                            f"Nested workflow '{task.nested_workflow.id}' failed"
                        )
                    task.complete()

                # Custom on_execute hook
                elif task.on_execute:
                    raw = await task.on_execute(task)
                    task.complete()
                    execution.results[task.id] = TaskResult(
                        task_id=task.id,
                        status="completed",
                        result=raw,
                    )

                # Dispatcher-based execution
                elif self._task_dispatcher:
                    agent_id = task.assigned_to
                    result = await self._task_dispatcher(task, agent_id)
                    execution.results[task.id] = result
                    if result.status == "failed":
                        raise WorkflowEngineError(
                            result.error or f"Task '{task.id}' execution failed"
                        )
                    task.complete()

                else:
                    # No dispatcher — just mark complete (for testing / dry-run)
                    task.complete()
                    execution.results[task.id] = TaskResult(
                        task_id=task.id, status="completed"
                    )

                end_ts = datetime.now(timezone.utc).timestamp()
                execution.task_timings[task.id] = {
                    "start_ms": start_ts * 1000,
                    "end_ms": end_ts * 1000,
                    "duration_ms": (end_ts - start_ts) * 1000,
                }
                completed_ids.add(task.id)
                execution.state.completed_tasks.append(task.id)
                execution.execution_order.append(task.id)

                self._log_event(
                    execution,
                    "task:completed",
                    {"task_id": task.id, "duration_ms": (end_ts - start_ts) * 1000},
                )

                # Persist state after each task
                await self.persist_state(workflow.id)

            except Exception as e:
                error_msg = str(e)
                task.fail(error_msg)
                errors.append(error_msg)
                self._log_event(
                    execution,
                    "task:failed",
                    {"task_id": task.id, "error": error_msg},
                )

                if workflow.rollback_on_failure:
                    raise  # Let outer handler trigger rollback

        end_ts = datetime.now(timezone.utc).timestamp()
        execution.state.status = (
            WorkflowStatus.CANCELLED
            if execution.state.status == WorkflowStatus.CANCELLED
            else WorkflowStatus.FAILED
            if errors
            else WorkflowStatus.COMPLETED
        )
        execution.state.completed_at = end_ts

        return WorkflowResult(
            id=workflow.id,
            status=(
                "cancelled"
                if execution.state.status == WorkflowStatus.CANCELLED
                else "failed"
                if errors
                else "completed"
            ),
            tasks_completed=len(completed_ids),
            tasks_failed=len(errors),
            errors=errors,
            execution_order=execution.execution_order,
            duration_ms=(end_ts - (execution.state.started_at or end_ts)) * 1000,
        )

    async def _rollback_workflow(
        self, execution: WorkflowExecution, workflow: WorkflowDefinition
    ) -> None:
        """Execute rollback hooks in reverse completion order, including failed tasks."""
        # Collect tasks with rollback hooks from execution state (which has the actual statuses)
        tasks_with_rollback = [
            t for t in execution.state.tasks
            if t.on_rollback is not None and t.id in execution.execution_order or t.status == TaskStatus.FAILED
        ]
        # Include failed tasks that never completed
        failed_task_ids = {t.id for t in execution.state.tasks if t.status == TaskStatus.FAILED}
        completed_ids = set(execution.state.completed_tasks)
        all_rollback_ids = list(reversed(execution.state.completed_tasks)) + list(failed_task_ids - completed_ids)

        for task_id in all_rollback_ids:
            task = next((t for t in execution.state.tasks if t.id == task_id), None)
            if task and task.on_rollback:
                try:
                    await task.on_rollback(task)
                    self._log_event(
                        execution, "task:rolledback", {"task_id": task_id}
                    )
                except Exception as e:
                    self._log_event(
                        execution,
                        "rollback:error",
                        {"task_id": task_id, "error": str(e)},
                    )

    @staticmethod
    def _log_event(
        execution: WorkflowExecution, event: str, data: Dict[str, Any]
    ) -> None:
        execution.event_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "data": data,
            }
        )

    @staticmethod
    def _chunk_tasks(tasks: List[WorkflowTask], num_chunks: int) -> List[List[WorkflowTask]]:
        """Split tasks into roughly equal chunks."""
        if num_chunks <= 0:
            return [tasks]
        chunk_size = max(1, len(tasks) // num_chunks)
        chunks: List[List[WorkflowTask]] = []
        for i in range(0, len(tasks), chunk_size):
            chunks.append(tasks[i : i + chunk_size])
        # If we have more chunks than dispatchers, merge extras
        while len(chunks) > num_chunks and len(chunks) > 1:
            last = chunks.pop()
            chunks[-1].extend(last)
        return chunks


# ── Convenience: build from dict ───────────────────────────────────────────


def build_workflow(data: Dict[str, Any]) -> WorkflowDefinition:
    """Build a WorkflowDefinition from a plain dict."""
    return WorkflowDefinition.from_dict(data)
