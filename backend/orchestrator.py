"""
Multi-Agent Orchestrator
Swarm coordination, task routing, failure recovery, and load balancing.

Adapted from Ruflo pattern: SwarmCoordinator topology-aware routing + WorkflowEngine.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models import Agent, Task, AgentRoom, Room
from services.task_service import TaskService
from websocket_manager import ws_manager
from utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass
class AgentCapability:
    """Agent capability profile for routing decisions."""
    agent_id: str
    role: str
    capabilities: List[str]
    current_load: int = 0
    success_rate: float = 1.0
    avg_task_duration: float = 0.0
    status: str = "idle"
    last_heartbeat: Optional[datetime] = None


@dataclass
class RoutingDecision:
    """Result of a routing decision."""
    agent_id: str
    strategy: str  # round_robin, least_load, capability_match, random
    confidence: float  # 0.0 - 1.0
    reason: str


class MultiAgentOrchestrator:
    """
    Coordinates multiple agents with:
    - Intelligent task routing
    - Load balancing across agents
    - Failure recovery with re-routing
    - Agent health monitoring
    - Capability-based matching
    """

    def __init__(self):
        self._agents: Dict[str, AgentCapability] = {}
        self._round_robin_idx: int = 0
        self._handlers: Dict[str, Callable] = {}
        self._health_check_interval: float = 30.0
        self._health_task: Optional[asyncio.Task] = None

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start health monitoring."""
        self._health_task = asyncio.create_task(self._health_loop())
        logger.info("Orchestrator started")

    async def stop(self) -> None:
        """Stop health monitoring."""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        logger.info("Orchestrator stopped")

    # ── Agent Registration ─────────────────────────────────────────────────

    async def register_agent(
        self,
        db: AsyncSession,
        agent_id: str,
    ) -> AgentCapability:
        """Register an agent for orchestration."""
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        profile = AgentCapability(
            agent_id=agent.id,
            role=agent.role,
            capabilities=agent.capabilities or [],
            status=agent.status or "idle",
        )
        self._agents[agent_id] = profile
        logger.info("Agent %s registered for orchestration", agent_id)
        return profile

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from orchestration."""
        self._agents.pop(agent_id, None)
        logger.info("Agent %s unregistered", agent_id)

    # ── Routing Strategies ──────────────────────────────────────────────────

    def route_round_robin(self, candidates: List[AgentCapability]) -> Optional[RoutingDecision]:
        """Simple round-robin across candidates."""
        if not candidates:
            return None
        idx = self._round_robin_idx % len(candidates)
        self._round_robin_idx += 1
        agent = candidates[idx]
        return RoutingDecision(
            agent_id=agent.agent_id,
            strategy="round_robin",
            confidence=0.5,
            reason="Even distribution across agents",
        )

    def route_least_load(self, candidates: List[AgentCapability]) -> Optional[RoutingDecision]:
        """Route to agent with lowest current load."""
        if not candidates:
            return None
        agent = min(candidates, key=lambda a: a.current_load)
        return RoutingDecision(
            agent_id=agent.agent_id,
            strategy="least_load",
            confidence=0.7,
            reason=f"Lowest load ({agent.current_load} tasks)",
        )

    def route_capability_match(
        self,
        candidates: List[AgentCapability],
        required_caps: List[str],
    ) -> Optional[RoutingDecision]:
        """Route to agent with best capability match."""
        if not candidates or not required_caps:
            return None

        scored = []
        for agent in candidates:
            matches = sum(1 for cap in required_caps if cap in agent.capabilities)
            score = matches / len(required_caps)
            scored.append((score, agent))

        scored.sort(reverse=True)
        best_score, best_agent = scored[0]

        if best_score == 0:
            return None

        return RoutingDecision(
            agent_id=best_agent.agent_id,
            strategy="capability_match",
            confidence=best_score,
            reason=f"Matches {int(best_score * 100)}% of required capabilities",
        )

    def route_random(self, candidates: List[AgentCapability]) -> Optional[RoutingDecision]:
        """Random selection (for load testing / chaos)."""
        if not candidates:
            return None
        agent = random.choice(candidates)
        return RoutingDecision(
            agent_id=agent.agent_id,
            strategy="random",
            confidence=0.3,
            reason="Random selection",
        )

    # ── Main Routing API ───────────────────────────────────────────────────

    async def route_task(
        self,
        db: AsyncSession,
        task_type: str,
        room_id: str,
        required_caps: Optional[List[str]] = None,
        strategy: str = "auto",
    ) -> RoutingDecision:
        """
        Route a task to the best available agent.
        Strategies: auto, round_robin, least_load, capability_match, random
        """
        # Get active agents in room
        result = await db.execute(
            select(AgentRoom, Agent)
            .join(Agent, AgentRoom.agent_id == Agent.id)
            .where(
                and_(
                    AgentRoom.room_id == room_id,
                    AgentRoom.is_active == True,
                    Agent.status.in_(["idle", "working"]),
                )
            )
        )
        rows = result.all()

        candidates: List[AgentCapability] = []
        for _, agent in rows:
            if agent.id in self._agents:
                candidates.append(self._agents[agent.id])
            else:
                # Auto-register
                cap = await self.register_agent(db, agent.id)
                candidates.append(cap)

        if not candidates:
            raise ValueError(f"No available agents in room {room_id}")

        # Apply strategy
        if strategy == "auto":
            # Priority: capability_match > least_load > round_robin
            decision = self.route_capability_match(candidates, required_caps or [])
            if decision and decision.confidence >= 0.5:
                return decision
            decision = self.route_least_load(candidates)
            if decision:
                return decision
            return self.route_round_robin(candidates)

        elif strategy == "round_robin":
            return self.route_round_robin(candidates)
        elif strategy == "least_load":
            return self.route_least_load(candidates)
        elif strategy == "capability_match":
            return self.route_capability_match(candidates, required_caps or [])
        elif strategy == "random":
            return self.route_random(candidates)
        else:
            return self.route_round_robin(candidates)

    # ── Task Execution with Failover ───────────────────────────────────────

    async def execute_with_failover(
        self,
        db: AsyncSession,
        task_id: str,
        room_id: str,
        strategy: str = "auto",
    ) -> Dict[str, Any]:
        """
        Execute a task with automatic failover to another agent on failure.
        """
        task_service = TaskService()
        task = await task_service.get_task(db, task_id)
        if not task:
            return {"status": "failed", "error": "Task not found"}

        # Get required capabilities from task metadata
        required_caps = task.metadata.get("required_capabilities", [])

        # Try primary agent
        try:
            decision = await self.route_task(
                db, task.task_type, room_id, required_caps, strategy
            )
        except ValueError:
            return {"status": "failed", "error": "No available agents"}

        primary_agent_id = decision.agent_id

        # Execute
        try:
            result = await task_service.execute_task(db, task_id, primary_agent_id)
            if result["status"] == "completed":
                # Update agent stats
                if primary_agent_id in self._agents:
                    self._agents[primary_agent_id].current_load -= 1
                    self._agents[primary_agent_id].success_rate = self._update_success_rate(
                        self._agents[primary_agent_id].success_rate, True
                    )
                return {**result, "routing": decision.__dict__}
        except Exception as e:
            logger.error("Primary execution failed: %s", e)

        # Failover: try another agent
        logger.info("Failover triggered for task %s", task_id)
        self._agents[primary_agent_id].success_rate = self._update_success_rate(
            self._agents[primary_agent_id].success_rate, False
        )

        # Get next best agent (exclude primary)
        try:
            decision2 = await self.route_task(
                db, task.task_type, room_id, required_caps, "least_load"
            )
            if decision2.agent_id == primary_agent_id:
                return {"status": "failed", "error": "No failover agent available"}

            result = await task_service.execute_task(db, task_id, decision2.agent_id)
            return {**result, "routing": decision2.__dict__, "failover": True}
        except Exception as e2:
            logger.error("Failover also failed: %s", e2)
            return {"status": "failed", "error": f"Primary and failover failed: {str(e2)}"}

    # ── Health Monitoring ──────────────────────────────────────────────────

    async def _health_loop(self) -> None:
        """Periodically check agent health and update stats."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                for agent_id, profile in list(self._agents.items()):
                    # Check WebSocket presence
                    conn = None
                    for room_id in ws_manager.active_rooms():
                        conn = ws_manager.get_agent_connection(room_id, agent_id)
                        if conn:
                            break

                    if conn:
                        profile.status = conn.status
                        profile.last_heartbeat = datetime.now(timezone.utc)
                    else:
                        # Agent offline
                        profile.status = "offline"

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health loop error: %s", e)

    # ── Utility ─────────────────────────────────────────────────────────────

    @staticmethod
    def _update_success_rate(current: float, success: bool) -> float:
        """Update rolling success rate (exponential moving average)."""
        alpha = 0.3
        return (1 - alpha) * current + alpha * (1.0 if success else 0.0)

    def get_agent_stats(self) -> Dict[str, Any]:
        """Get orchestration stats for all agents."""
        return {
            agent_id: {
                "role": p.role,
                "load": p.current_load,
                "success_rate": round(p.success_rate, 3),
                "status": p.status,
                "capabilities": p.capabilities,
            }
            for agent_id, p in self._agents.items()
        }

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get aggregate pool statistics."""
        if not self._agents:
            return {}
        loads = [p.current_load for p in self._agents.values()]
        rates = [p.success_rate for p in self._agents.values()]
        return {
            "total_agents": len(self._agents),
            "avg_load": sum(loads) / len(loads),
            "max_load": max(loads),
            "avg_success_rate": sum(rates) / len(rates),
            "healthy_agents": sum(1 for p in self._agents.values() if p.status != "offline"),
        }


# ── Global Instance ─────────────────────────────────────────────────────────
orchestrator = MultiAgentOrchestrator()
