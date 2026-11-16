"""
Swarm Orchestrator
Multi-agent swarm coordination with task decomposition and parallel execution.

Supports CrewAI, Swarms, and native workflow engine integration.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models import SwarmExecution, Task
from agents.roles.role_definitions import get_role, list_roles
from workflow_engine_native import WorkflowEngineNative, WorkflowDefinition, WorkflowTask
from infrastructure.interfaces.base_storage_provider import BaseStorageProvider

logger = logging.getLogger(__name__)


class SwarmOrchestrator:
    """
    Orchestrates multi-agent swarm execution.
    - Decomposes complex tasks into subtasks
    - Spawns parallel agent execution
    - Tracks progress and aggregates results
    """

    def __init__(self, storage_provider: Optional[BaseStorageProvider] = None):
        self._active_swarms: Dict[str, SwarmExecution] = {}
        self._engine = WorkflowEngineNative()
        self.storage_provider = storage_provider

    async def initialize(self):
        await self._engine.initialize()

    # ── Task Decomposition ────────────────────────────────────────────

    async def decompose_task(self, description: str, complexity: str = "medium") -> List[Dict[str, Any]]:
        """
        Decompose a complex task into subtasks for parallel execution.
        In production, this would use an LLM. For now, uses rule-based decomposition.
        """
        complexity_patterns = {
            "low": [
                {"description": f"Analyze: {description}", "agent_type": "developer", "estimated_time": "5m"},
                {"description": f"Execute: {description}", "agent_type": "developer", "estimated_time": "10m"},
            ],
            "medium": [
                {"description": f"Research and gather data for: {description}", "agent_type": "developer", "estimated_time": "10m"},
                {"description": f"Analyze findings for: {description}", "agent_type": "coo", "estimated_time": "10m"},
                {"description": f"Draft solution for: {description}", "agent_type": "developer", "estimated_time": "15m"},
                {"description": f"Review and validate: {description}", "agent_type": "ceo", "estimated_time": "5m"},
            ],
            "high": [
                {"description": f"Strategic analysis: {description}", "agent_type": "ceo", "estimated_time": "15m"},
                {"description": f"Operational planning: {description}", "agent_type": "coo", "estimated_time": "15m"},
                {"description": f"Technical architecture: {description}", "agent_type": "developer", "estimated_time": "20m"},
                {"description": f"Content strategy: {description}", "agent_type": "content_director", "estimated_time": "15m"},
                {"description": f"Customer impact analysis: {description}", "agent_type": "crm", "estimated_time": "10m"},
                {"description": f"Integration and testing: {description}", "agent_type": "developer", "estimated_time": "15m"},
            ],
        }

        subtasks = complexity_patterns.get(complexity, complexity_patterns["medium"])
        return [
            {
                "id": f"subtask-{i}-{uuid.uuid4().hex[:8]}",
                **subtask,
            }
            for i, subtask in enumerate(subtasks)
        ]

    # ── Swarm Execution ─────────────────────────────────────────────────

    async def spawn_swarm(
        self,
        db: AsyncSession,
        task_description: str,
        complexity: str = "medium",
        framework: str = "native",
    ) -> Dict[str, Any]:
        """
        Spawn a swarm of agents to work on a complex task.
        Returns swarm execution details.
        """
        swarm_id = f"swarm-{uuid.uuid4().hex[:8]}"

        # Decompose task
        subtasks = await self.decompose_task(task_description, complexity)

        # Create swarm execution record
        swarm = SwarmExecution(
            swarm_id=swarm_id,
            framework=framework,
            agents_spawned=len(subtasks),
            agents_completed=0,
            status="spawning",
            decomposition=subtasks,
        )
        db.add(swarm)
        await db.flush()

        self._active_swarms[swarm_id] = swarm

        # Create workflow definition
        tasks = [
            WorkflowTask(
                id=st["id"],
                type="code",
                description=st["description"],
                assigned_to=st["agent_type"],
            )
            for st in subtasks
        ]

        workflow = WorkflowDefinition(
            id=swarm_id,
            name=f"Swarm: {task_description[:50]}",
            tasks=tasks,
        )

        # Start execution asynchronously
        asyncio.create_task(self._run_swarm_workflow(db, swarm_id, workflow))

        return {
            "success": True,
            "swarm_id": swarm_id,
            "framework": framework,
            "agents_spawned": len(subtasks),
            "status": "spawning",
            "subtasks": subtasks,
        }

    async def _run_swarm_workflow(
        self,
        db: AsyncSession,
        swarm_id: str,
        workflow: WorkflowDefinition,
    ) -> None:
        """Internal: Execute the swarm workflow and update status."""
        swarm = self._active_swarms.get(swarm_id)
        if not swarm:
            return

        swarm.status = "in_progress"

        # Execute workflow
        result = await self._engine.execute_workflow(workflow)

        # Update swarm record
        swarm.agents_completed = result.tasks_completed
        swarm.status = result.status
        swarm.completed_at = datetime.now(timezone.utc)

        # Refresh in DB
        await db.flush()

        logger.info(
            "Swarm %s completed: %s (%d/%d tasks)",
            swarm_id,
            result.status,
            result.tasks_completed,
            result.tasks_failed,
        )

    # ── Queries ───────────────────────────────────────────────────────

    async def get_swarm_status(
        self,
        db: AsyncSession,
        swarm_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get current status of a swarm execution."""
        result = await db.execute(
            select(SwarmExecution).where(SwarmExecution.swarm_id == swarm_id)
        )
        swarm = result.scalar_one_or_none()

        if not swarm:
            return None

        return {
            "swarm_id": swarm.swarm_id,
            "status": swarm.status,
            "framework": swarm.framework,
            "agents_spawned": swarm.agents_spawned,
            "agents_completed": swarm.agents_completed,
            "started_at": swarm.started_at.isoformat() if swarm.started_at else None,
            "completed_at": swarm.completed_at.isoformat() if swarm.completed_at else None,
            "decomposition": swarm.decomposition,
        }

    async def list_active_swarms(
        self,
        db: AsyncSession,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List all swarm executions."""
        result = await db.execute(
            select(SwarmExecution)
            .order_by(desc(SwarmExecution.started_at))
            .limit(limit)
        )
        swarms = result.scalars().all()

        return [
            {
                "swarm_id": s.swarm_id,
                "status": s.status,
                "framework": s.framework,
                "agents_spawned": s.agents_spawned,
                "agents_completed": s.agents_completed,
                "started_at": s.started_at.isoformat() if s.started_at else None,
            }
            for s in swarms
        ]

    # ── Metrics ────────────────────────────────────────────────────────

    async def get_swarm_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get aggregate metrics across all swarm executions."""
        result = await db.execute(select(SwarmExecution))
        swarms = result.scalars().all()

        total = len(swarms)
        completed = sum(1 for s in swarms if s.status == "completed")
        failed = sum(1 for s in swarms if s.status == "failed")
        avg_agents = sum(s.agents_spawned for s in swarms) / max(total, 1)

        return {
            "total_swarms": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / max(total, 1),
            "average_agents_per_swarm": avg_agents,
            "active_now": len([s for s in swarms if s.status == "in_progress"]),
        }


# ── Singleton ─────────────────────────────────────────────────────────

_orchestrator: Optional[SwarmOrchestrator] = None


def get_swarm_orchestrator() -> SwarmOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SwarmOrchestrator()
    return _orchestrator
