# Phase 2: Orchestration Implementation
## Chief of Staff + Agent Registry + AutoGovernor

import asyncio
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import croniter


class AgentHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class AgentCapability:
    """Describes what an agent can do"""
    name: str
    risk_level: str = "safe"  # safe, medium, critical
    requires_approval: bool = False
    rate_limit: int = 100  # calls per minute
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: int = 30  # seconds


@dataclass
class AgentRegistration:
    """Full agent registration with capabilities and health"""
    agent_id: str
    agent_type: str  # scout, maker, merchant, etc.
    business_id: int
    capabilities: List[AgentCapability]
    current_load: int = 0
    max_load: int = 10
    health_status: AgentHealth = AgentHealth.HEALTHY
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)


class AgentCapabilityRegistry:
    """
    Central registry for all agent capabilities.
    Enables dynamic discovery and routing.
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentRegistration] = {}
        self.capability_index: Dict[str, List[str]] = {}  # capability -> agent_ids
        self.business_agents: Dict[int, List[str]] = {}  # business_id -> agent_ids
        
    def register(self, registration: AgentRegistration) -> bool:
        """Register a new agent or update existing."""
        self.agents[registration.agent_id] = registration
        
        # Index by business
        if registration.business_id not in self.business_agents:
            self.business_agents[registration.business_id] = []
        if registration.agent_id not in self.business_agents[registration.business_id]:
            self.business_agents[registration.business_id].append(registration.agent_id)
        
        # Index capabilities
        for cap in registration.capabilities:
            if cap.name not in self.capability_index:
                self.capability_index[cap.name] = []
            if registration.agent_id not in self.capability_index[cap.name]:
                self.capability_index[cap.name].append(registration.agent_id)
        
        return True
    
    def unregister(self, agent_id: str):
        """Remove agent from registry."""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        
        # Remove from business index
        if agent.business_id in self.business_agents:
            self.business_agents[agent.business_id] = [
                aid for aid in self.business_agents[agent.business_id] 
                if aid != agent_id
            ]
        
        # Remove from capability index
        for cap in agent.capabilities:
            if cap.name in self.capability_index:
                self.capability_index[cap.name] = [
                    aid for aid in self.capability_index[cap.name]
                    if aid != agent_id
                ]
        
        del self.agents[agent_id]
    
    def find_agents(
        self,
        capability: str,
        business_id: Optional[int] = None,
        healthy_only: bool = True
    ) -> List[AgentRegistration]:
        """
        Find agents that can perform a capability.
        
        Args:
            capability: Required capability name
            business_id: Optional business filter
            healthy_only: Only return healthy agents
        """
        agent_ids = self.capability_index.get(capability, [])
        results = []
        
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if not agent:
                continue
            
            # Filter by business
            if business_id and agent.business_id != business_id:
                continue
            
            # Filter by health
            if healthy_only and agent.health_status != AgentHealth.HEALTHY:
                continue
            
            # Filter by load
            if agent.current_load >= agent.max_load:
                continue
            
            results.append(agent)
        
        # Sort by load (least loaded first)
        results.sort(key=lambda a: a.current_load)
        return results
    
    def update_health(self, agent_id: str, status: AgentHealth):
        """Update agent health status."""
        if agent_id in self.agents:
            self.agents[agent_id].health_status = status
            self.agents[agent_id].last_heartbeat = datetime.utcnow()
    
    def update_load(self, agent_id: str, delta: int):
        """Update agent load (positive for increase, negative for decrease)."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.current_load = max(0, agent.current_load + delta)
    
    def get_business_health(self, business_id: int) -> Dict:
        """Get health summary for all agents in a business."""
        agent_ids = self.business_agents.get(business_id, [])
        agents = [self.agents[aid] for aid in agent_ids if aid in self.agents]
        
        if not agents:
            return {"status": "no_agents", "healthy": 0, "total": 0}
        
        healthy = sum(1 for a in agents if a.health_status == AgentHealth.HEALTHY)
        degraded = sum(1 for a in agents if a.health_status == AgentHealth.DEGRADED)
        down = sum(1 for a in agents if a.health_status == AgentHealth.DOWN)
        
        status = "healthy" if healthy == len(agents) else "degraded" if down == 0 else "critical"
        
        return {
            "status": status,
            "healthy": healthy,
            "degraded": degraded,
            "down": down,
            "total": len(agents),
            "avg_load": sum(a.current_load for a in agents) / len(agents)
        }


@dataclass
class Task:
    """A task to be executed by an agent"""
    task_id: str
    task_type: str
    business_id: int
    priority: int  # 1-10, higher is more urgent
    payload: Dict
    required_capabilities: List[str]
    assigned_agent: Optional[str] = None
    status: str = "pending"  # pending, assigned, executing, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


class ChiefOfStaff:
    """
    Orchestrates agent workflows and task routing.
    Acts as central coordinator between Ledger and agents.
    """
    
    def __init__(self, registry: AgentCapabilityRegistry, ledger):
        self.registry = registry
        self.ledger = ledger
        self.task_queue: List[Task] = []
        self.active_tasks: Dict[str, Task] = {}
        self.task_history: List[Task] = []
        self.max_history = 1000
        
        # Task handlers (agent_type -> handler function)
        self.handlers: Dict[str, Callable] = {}
    
    def register_handler(self, agent_type: str, handler: Callable):
        """Register a handler function for an agent type."""
        self.handlers[agent_type] = handler
    
    async def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution.
        
        Flow:
        1. Add to queue
        2. Sort by priority
        3. Try to assign immediately
        """
        self.task_queue.append(task)
        
        # Sort by priority (descending) then creation time
        self.task_queue.sort(key=lambda t: (-t.priority, t.created_at))
        
        # Try to assign
        await self._process_queue()
        
        return task.task_id
    
    async def _process_queue(self):
        """Process pending tasks in queue."""
        pending = [t for t in self.task_queue if t.status == "pending"]
        
        for task in pending:
            assigned = await self._assign_task(task)
            if assigned:
                self.task_queue.remove(task)
                self.active_tasks[task.task_id] = task
    
    async def _assign_task(self, task: Task) -> bool:
        """
        Try to assign task to an available agent.
        
        Returns True if assigned successfully.
        """
        # Find agents with required capabilities
        for capability in task.required_capabilities:
            candidates = self.registry.find_agents(
                capability=capability,
                business_id=task.business_id,
                healthy_only=True
            )
            
            if not candidates:
                continue
            
            # Pick least loaded agent
            agent = candidates[0]
            
            # Check with Ledger if needed
            agent_cap = next(
                (c for c in agent.capabilities if c.name == capability),
                None
            )
            
            if agent_cap and agent_cap.requires_approval:
                approved, reason = await self.ledger.check_command(
                    f"Assign {task.task_type} to {agent.agent_id}",
                    {"task": task.to_dict() if hasattr(task, 'to_dict') else str(task)}
                )
                if not approved:
                    continue
            
            # Assign task
            task.assigned_agent = agent.agent_id
            task.status = "assigned"
            task.started_at = datetime.utcnow()
            
            # Update agent load
            self.registry.update_load(agent.agent_id, 1)
            
            # Start execution
            asyncio.create_task(self._execute_task(task))
            
            return True
        
        return False
    
    async def _execute_task(self, task: Task):
        """Execute assigned task."""
        task.status = "executing"
        
        try:
            # Get agent type
            agent = self.registry.agents.get(task.assigned_agent)
            if not agent:
                raise Exception("Agent not found")
            
            # Get handler
            handler = self.handlers.get(agent.agent_type)
            if not handler:
                raise Exception(f"No handler for agent type: {agent.agent_type}")
            
            # Execute
            result = await handler(task.payload)
            
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.utcnow()
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.utcnow()
        
        # Update agent load
        self.registry.update_load(task.assigned_agent, -1)
        
        # Move to history
        if len(self.task_history) >= self.max_history:
            self.task_history.pop(0)
        self.task_history.append(task)
        
        # Remove from active
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        
        # Process more tasks
        await self._process_queue()
    
    def get_queue_status(self) -> Dict:
        """Get current queue status."""
        return {
            "pending": len([t for t in self.task_queue if t.status == "pending"]),
            "active": len(self.active_tasks),
            "completed_last_hour": len([
                t for t in self.task_history
                if t.completed_at and t.completed_at > datetime.utcnow() - timedelta(hours=1)
            ])
        }


@dataclass
class ScheduledJob:
    """A cron-scheduled job"""
    job_id: str
    name: str
    cron_expression: str
    task_template: Task
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0


class AutoGovernor:
    """
    Autonomous background oversight system.
    Runs scheduled health checks, anomaly detection, and optimization scans.
    """
    
    def __init__(self, chief_of_staff: ChiefOfStaff, registry: AgentCapabilityRegistry):
        self.chief = chief_of_staff
        self.registry = registry
        self.jobs: Dict[str, ScheduledJob] = {}
        self.running = False
        self.anomaly_detectors: List[Callable] = []
        self.opportunity_scanners: List[Callable] = []
        
        # Default jobs
        self._setup_default_jobs()
    
    def _setup_default_jobs(self):
        """Set up default scheduled jobs."""
        # Health check every 5 minutes
        self.add_job(
            job_id="health_check",
            name="Business Health Monitor",
            cron="*/5 * * * *",  # Every 5 minutes
            task_type="health_check"
        )
        
        # Anomaly scan every 15 minutes
        self.add_job(
            job_id="anomaly_scan",
            name="Anomaly Detection",
            cron="*/15 * * * *",
            task_type="anomaly_scan"
        )
        
        # Opportunity scan every 30 minutes
        self.add_job(
            job_id="opportunity_scan",
            name="Opportunity Scanner",
            cron="*/30 * * * *",
            task_type="opportunity_scan"
        )
    
    def add_job(self, job_id: str, name: str, cron: str, task_type: str):
        """Add a scheduled job."""
        job = ScheduledJob(
            job_id=job_id,
            name=name,
            cron_expression=cron,
            task_template=Task(
                task_id=f"scheduled_{job_id}",
                task_type=task_type,
                business_id=0,  # All businesses
                priority=5,
                payload={},
                required_capabilities=["auto_govern"]
            )
        )
        self.jobs[job_id] = job
    
    async def start(self):
        """Start the AutoGovernor scheduler."""
        self.running = True
        while self.running:
            await self._check_scheduled_jobs()
            await asyncio.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
    
    async def _check_scheduled_jobs(self):
        """Check if any jobs need to run."""
        now = datetime.utcnow()
        
        for job in self.jobs.values():
            if not job.enabled:
                continue
            
            # Calculate next run time
            cron = croniter.croniter(job.cron_expression, job.last_run or now)
            next_run = cron.get_next(datetime)
            
            if now >= next_run:
                await self._run_job(job)
    
    async def _run_job(self, job: ScheduledJob):
        """Execute a scheduled job."""
        job.last_run = datetime.utcnow()
        job.run_count += 1
        
        if job.task_template.task_type == "health_check":
            await self._run_health_check()
        elif job.task_template.task_type == "anomaly_scan":
            await self._run_anomaly_scan()
        elif job.task_template.task_type == "opportunity_scan":
            await self._run_opportunity_scan()
    
    async def _run_health_check(self):
        """Check health of all businesses."""
        # Get all businesses
        businesses = set()
        for agent in self.registry.agents.values():
            businesses.add(agent.business_id)
        
        for business_id in businesses:
            health = self.registry.get_business_health(business_id)
            
            if health["status"] == "critical":
                # Queue alert task
                await self.chief.submit_task(Task(
                    task_id=f"alert_health_{business_id}_{datetime.utcnow().timestamp()}",
                    task_type="health_alert",
                    business_id=business_id,
                    priority=10,  # High priority
                    payload={"health": health, "business_id": business_id},
                    required_capabilities=["alert"]
                ))
    
    async def _run_anomaly_scan(self):
        """Scan for anomalies across all businesses."""
        for detector in self.anomaly_detectors:
            try:
                anomalies = await detector()
                for anomaly in anomalies:
                    await self.chief.submit_task(Task(
                        task_id=f"anomaly_{anomaly['id']}",
                        task_type="anomaly_alert",
                        business_id=anomaly.get("business_id", 0),
                        priority=8,
                        payload=anomaly,
                        required_capabilities=["alert"]
                    ))
            except Exception as e:
                print(f"Anomaly detector failed: {e}")
    
    async def _run_opportunity_scan(self):
        """Scan for optimization opportunities."""
        for scanner in self.opportunity_scanners:
            try:
                opportunities = await scanner()
                for opp in opportunities:
                    # Queue for approval, don't auto-execute
                    await self.chief.submit_task(Task(
                        task_id=f"opportunity_{opp['id']}",
                        task_type="opportunity_review",
                        business_id=opp.get("business_id", 0),
                        priority=opp.get("priority", 3),
                        payload=opp,
                        required_capabilities=["review"]
                    ))
            except Exception as e:
                print(f"Opportunity scanner failed: {e}")
    
    def register_anomaly_detector(self, detector: Callable):
        """Register an anomaly detection function."""
        self.anomaly_detectors.append(detector)
    
    def register_opportunity_scanner(self, scanner: Callable):
        """Register an opportunity scanning function."""
        self.opportunity_scanners.append(scanner)
    
    def get_status(self) -> Dict:
        """Get AutoGovernor status."""
        return {
            "running": self.running,
            "jobs": len(self.jobs),
            "anomaly_detectors": len(self.anomaly_detectors),
            "opportunity_scanners": len(self.opportunity_scanners),
            "jobs_detail": [
                {
                    "id": job.job_id,
                    "name": job.name,
                    "enabled": job.enabled,
                    "run_count": job.run_count,
                    "last_run": job.last_run.isoformat() if job.last_run else None
                }
                for job in self.jobs.values()
            ]
        }


# Export
__all__ = [
    'AgentCapability',
    'AgentRegistration',
    'AgentCapabilityRegistry',
    'AgentHealth',
    'Task',
    'ChiefOfStaff',
    'ScheduledJob',
    'AutoGovernor'
]
