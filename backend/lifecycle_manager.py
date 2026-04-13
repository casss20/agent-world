"""
Agent World: Graceful Lifecycle Manager
Manages agent startup, shutdown, pause/resume, and stuck-task recovery
"""

import asyncio
import signal
import sys
from typing import Dict, Set, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum as PyEnum

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from models import Agent, AgentSession, TaskQueue, AgentStatus, TaskStatus
from observability import logger

# ============================================================================
# LIFECYCLE STATES
# ============================================================================

class LifecycleState(PyEnum):
    """Agent lifecycle states"""
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

# ============================================================================
# LIFECYCLE CONFIGURATION
# ============================================================================

@dataclass
class LifecycleConfig:
    """Configuration for agent lifecycle management"""
    # Heartbeat settings
    heartbeat_interval_seconds: float = 30.0
    heartbeat_timeout_seconds: float = 120.0
    
    # Task settings
    task_claim_timeout_seconds: float = 300.0  # 5 minutes
    task_stuck_threshold_seconds: float = 600.0  # 10 minutes
    
    # Shutdown settings
    graceful_shutdown_timeout_seconds: float = 60.0
    force_kill_after_seconds: float = 90.0
    
    # Recovery settings
    stuck_task_check_interval_seconds: float = 60.0
    zombie_agent_check_interval_seconds: float = 300.0  # 5 minutes

# ============================================================================
# LIFECYCLE MANAGER
# ============================================================================

class AgentLifecycleManager:
    """
    Manages the complete lifecycle of agents.
    
    Features:
    - Graceful startup and initialization
    - Graceful shutdown with task completion
    - Pause/resume functionality
    - Stuck task detection and recovery
    - Zombie agent cleanup
    - Signal handling for clean exits
    """
    
    def __init__(self, db_session: Session, redis_client=None):
        self.db = db_session
        self.redis = redis_client
        self.config = LifecycleConfig()
        
        # Track managed agents
        self.managed_agents: Dict[str, 'AgentLifecycle'] = {}
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Register signal handlers
        self._register_signal_handlers()
    
    def _register_signal_handlers(self):
        """Register OS signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(
                "Received shutdown signal",
                signal=signum,
                signal_name=signal.Signals(signum).name
            )
            asyncio.create_task(self._initiate_shutdown())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def start_agent(self, agent_id: str) -> 'AgentLifecycle':
        """
        Start and manage a new agent.
        
        Args:
            agent_id: ID of the agent to start
        
        Returns:
            AgentLifecycle instance for the started agent
        """
        if agent_id in self.managed_agents:
            logger.warning(
                "Agent already managed",
                agent_id=agent_id
            )
            return self.managed_agents[agent_id]
        
        lifecycle = AgentLifecycle(
            agent_id=agent_id,
            db_session=self.db,
            redis_client=self.redis,
            config=self.config
        )
        
        self.managed_agents[agent_id] = lifecycle
        
        # Start the agent
        await lifecycle.start()
        
        logger.info(
            "Agent lifecycle started",
            agent_id=agent_id,
            lifecycle_id=id(lifecycle)
        )
        
        return lifecycle
    
    async def stop_agent(self, agent_id: str, force: bool = False) -> bool:
        """
        Stop a managed agent.
        
        Args:
            agent_id: ID of the agent to stop
            force: If True, force kill without waiting for tasks
        
        Returns:
            True if agent was stopped successfully
        """
        if agent_id not in self.managed_agents:
            logger.warning(
                "Agent not found in managed agents",
                agent_id=agent_id
            )
            return False
        
        lifecycle = self.managed_agents[agent_id]
        
        if force:
            await lifecycle.force_stop()
        else:
            await lifecycle.graceful_stop()
        
        del self.managed_agents[agent_id]
        
        logger.info(
            "Agent stopped",
            agent_id=agent_id,
            force=force
        )
        
        return True
    
    async def pause_agent(self, agent_id: str) -> bool:
        """Pause a running agent"""
        if agent_id not in self.managed_agents:
            return False
        
        lifecycle = self.managed_agents[agent_id]
        await lifecycle.pause()
        
        logger.info("Agent paused", agent_id=agent_id)
        return True
    
    async def resume_agent(self, agent_id: str) -> bool:
        """Resume a paused agent"""
        if agent_id not in self.managed_agents:
            return False
        
        lifecycle = self.managed_agents[agent_id]
        await lifecycle.resume()
        
        logger.info("Agent resumed", agent_id=agent_id)
        return True
    
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Lifecycle monitoring started")
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        self._shutdown_event.set()
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Lifecycle monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background loop for monitoring and recovery"""
        while not self._shutdown_event.is_set():
            try:
                # Check for stuck tasks
                await self._recover_stuck_tasks()
                
                # Check for zombie agents
                await self._cleanup_zombie_agents()
                
                # Wait before next check
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.config.stuck_task_check_interval_seconds
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(
                    "Error in monitoring loop",
                    error=str(e)
                )
                await asyncio.sleep(10)
    
    async def _recover_stuck_tasks(self):
        """Find and recover tasks that appear stuck"""
        stuck_threshold = datetime.utcnow() - timedelta(
            seconds=self.config.task_stuck_threshold_seconds
        )
        
        stuck_tasks = self.db.query(TaskQueue).filter(
            and_(
                TaskQueue.status == TaskStatus.RUNNING,
                TaskQueue.claimed_at < stuck_threshold
            )
        ).all()
        
        for task in stuck_tasks:
            logger.warning(
                "Recovering stuck task",
                task_id=str(task.id),
                agent_id=str(task.agent_id),
                claimed_at=task.claimed_at.isoformat(),
                stuck_duration_seconds=(
                    datetime.utcnow() - task.claimed_at
                ).total_seconds()
            )
            
            # Release task back to pending
            task.status = TaskStatus.PENDING
            task.agent_id = None
            task.claimed_at = None
            task.lease_expires = None
            task.retry_count += 1
            
            # Update agent status if needed
            if task.agent_id:
                agent = self.db.query(Agent).filter(
                    Agent.id == task.agent_id
                ).first()
                if agent:
                    agent.current_load = max(0, agent.current_load - 1)
                    if agent.current_load == 0:
                        agent.status = AgentStatus.IDLE
        
        if stuck_tasks:
            self.db.commit()
            logger.info(
                "Stuck tasks recovered",
                count=len(stuck_tasks)
            )
    
    async def _cleanup_zombie_agents(self):
        """Find and cleanup agents without recent heartbeats"""
        zombie_threshold = datetime.utcnow() - timedelta(
            seconds=self.config.heartbeat_timeout_seconds
        )
        
        zombie_sessions = self.db.query(AgentSession).filter(
            and_(
                AgentSession.status == "active",
                AgentSession.last_heartbeat < zombie_threshold
            )
        ).all()
        
        for session in zombie_sessions:
            logger.warning(
                "Marking zombie agent session",
                session_id=str(session.id),
                agent_id=str(session.agent_id),
                last_heartbeat=session.last_heartbeat.isoformat()
            )
            
            session.status = "dead"
            
            # Release any claimed tasks
            claimed_tasks = self.db.query(TaskQueue).filter(
                and_(
                    TaskQueue.agent_id == session.agent_id,
                    TaskQueue.status.in_([TaskStatus.CLAIMED, TaskStatus.RUNNING])
                )
            ).all()
            
            for task in claimed_tasks:
                task.status = TaskStatus.PENDING
                task.agent_id = None
                task.claimed_at = None
                task.lease_expires = None
            
            # Update agent status
            agent = self.db.query(Agent).filter(
                Agent.id == session.agent_id
            ).first()
            if agent:
                agent.status = AgentStatus.OFFLINE
                agent.current_load = 0
        
        if zombie_sessions:
            self.db.commit()
            logger.info(
                "Zombie sessions cleaned up",
                count=len(zombie_sessions)
            )
    
    async def _initiate_shutdown(self):
        """Initiate graceful shutdown of all agents"""
        logger.info(
            "Initiating graceful shutdown",
            managed_agents=len(self.managed_agents)
        )
        
        # Stop all agents gracefully
        stop_tasks = [
            self.stop_agent(agent_id, force=False)
            for agent_id in list(self.managed_agents.keys())
        ]
        
        # Wait for all to complete with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*stop_tasks),
                timeout=self.config.graceful_shutdown_timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Graceful shutdown timed out, forcing remaining agents"
            )
            # Force stop remaining
            for agent_id in list(self.managed_agents.keys()):
                await self.stop_agent(agent_id, force=True)
        
        # Stop monitoring
        await self.stop_monitoring()
        
        logger.info("Shutdown complete")
        sys.exit(0)


# ============================================================================
# AGENT LIFECYCLE
# ============================================================================

class AgentLifecycle:
    """
    Manages the lifecycle of a single agent.
    
    Handles:
    - Initialization and startup
    - Task claiming and execution
    - Heartbeat maintenance
    - Graceful shutdown
    - Pause/resume
    """
    
    def __init__(
        self,
        agent_id: str,
        db_session: Session,
        redis_client=None,
        config: LifecycleConfig = None
    ):
        self.agent_id = agent_id
        self.db = db_session
        self.redis = redis_client
        self.config = config or LifecycleConfig()
        
        self.state = LifecycleState.INITIALIZING
        self._main_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        self._current_task: Optional[str] = None
        self._session_id: Optional[str] = None
    
    async def start(self):
        """Start the agent lifecycle"""
        self.state = LifecycleState.STARTING
        
        # Create session record
        session = AgentSession(
            agent_id=self.agent_id,
            status="active",
            started_at=datetime.utcnow(),
            last_heartbeat=datetime.utcnow()
        )
        self.db.add(session)
        self.db.commit()
        self._session_id = str(session.id)
        
        # Update agent status
        agent = self.db.query(Agent).filter(Agent.id == self.agent_id).first()
        if agent:
            agent.status = AgentStatus.ONLINE
            agent.last_heartbeat = datetime.utcnow()
            self.db.commit()
        
        # Start main loop and heartbeat
        self._main_task = asyncio.create_task(self._main_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        self.state = LifecycleState.RUNNING
        
        logger.info(
            "Agent lifecycle started",
            agent_id=self.agent_id,
            session_id=self._session_id
        )
    
    async def _main_loop(self):
        """Main agent loop - claim and execute tasks"""
        while not self._shutdown_event.is_set():
            try:
                # Check for pause
                if self.state == LifecycleState.PAUSED:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=1.0
                    )
                    continue
                
                # Claim next task
                task = await self._claim_task()
                
                if task:
                    await self._execute_task(task)
                else:
                    # No task available, wait before retry
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=5.0
                    )
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(
                    "Error in main loop",
                    agent_id=self.agent_id,
                    error=str(e)
                )
                await asyncio.sleep(5)
    
    async def _claim_task(self) -> Optional[TaskQueue]:
        """Claim next available task from queue"""
        # This would integrate with the hardened task claim endpoint
        # For now, simplified implementation
        agent = self.db.query(Agent).filter(Agent.id == self.agent_id).first()
        
        if not agent or agent.current_load >= agent.max_load:
            return None
        
        # Find pending task
        task = self.db.query(TaskQueue).filter(
            and_(
                TaskQueue.status == TaskStatus.PENDING,
                TaskQueue.business_id == agent.business_id
            )
        ).order_by(TaskQueue.priority.desc()).first()
        
        if task:
            # Claim task
            task.status = TaskStatus.CLAIMED
            task.agent_id = self.agent_id
            task.claimed_at = datetime.utcnow()
            task.lease_expires = datetime.utcnow() + timedelta(
                seconds=self.config.task_claim_timeout_seconds
            )
            
            agent.current_load += 1
            agent.status = AgentStatus.BUSY
            
            self.db.commit()
            
            self._current_task = str(task.id)
            
            logger.info(
                "Task claimed",
                agent_id=self.agent_id,
                task_id=str(task.id)
            )
            
            return task
        
        return None
    
    async def _execute_task(self, task: TaskQueue):
        """Execute a claimed task"""
        try:
            task.status = TaskStatus.RUNNING
            self.db.commit()
            
            logger.info(
                "Task execution started",
                agent_id=self.agent_id,
                task_id=str(task.id),
                task_type=task.task_type
            )
            
            # Simulate task execution (replace with actual task execution)
            await asyncio.sleep(1)
            
            # Mark completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = {"status": "success"}
            
            agent = self.db.query(Agent).filter(Agent.id == self.agent_id).first()
            if agent:
                agent.current_load = max(0, agent.current_load - 1)
                if agent.current_load == 0:
                    agent.status = AgentStatus.IDLE
            
            self.db.commit()
            
            logger.info(
                "Task completed",
                agent_id=self.agent_id,
                task_id=str(task.id)
            )
            
        except Exception as e:
            logger.error(
                "Task execution failed",
                agent_id=self.agent_id,
                task_id=str(task.id),
                error=str(e)
            )
            
            task.status = TaskStatus.PENDING
            task.agent_id = None
            task.claimed_at = None
            task.lease_expires = None
            task.retry_count += 1
            
            agent = self.db.query(Agent).filter(Agent.id == self.agent_id).first()
            if agent:
                agent.current_load = max(0, agent.current_load - 1)
                if agent.current_load == 0:
                    agent.status = AgentStatus.IDLE
            
            self.db.commit()
        
        finally:
            self._current_task = None
    
    async def _heartbeat_loop(self):
        """Maintain agent heartbeat"""
        while not self._shutdown_event.is_set():
            try:
                # Update heartbeat in database
                session = self.db.query(AgentSession).filter(
                    AgentSession.id == self._session_id
                ).first()
                
                if session:
                    session.last_heartbeat = datetime.utcnow()
                    
                    # Also update agent
                    agent = self.db.query(Agent).filter(
                        Agent.id == self.agent_id
                    ).first()
                    if agent:
                        agent.last_heartbeat = datetime.utcnow()
                    
                    self.db.commit()
                
                # Update Redis for fast presence checks
                if self.redis:
                    await self.redis.setex(
                        f"agent:{self.agent_id}:heartbeat",
                        int(self.config.heartbeat_timeout_seconds),
                        datetime.utcnow().isoformat()
                    )
                
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.config.heartbeat_interval_seconds
                )
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(
                    "Heartbeat error",
                    agent_id=self.agent_id,
                    error=str(e)
                )
                await asyncio.sleep(5)
    
    async def pause(self):
        """Pause the agent"""
        if self.state != LifecycleState.RUNNING:
            return
        
        self.state = LifecycleState.PAUSING
        
        # Wait for current task to complete
        if self._current_task:
            logger.info(
                "Waiting for current task to complete before pause",
                agent_id=self.agent_id,
                task_id=self._current_task
            )
            
            # Wait up to 60 seconds for task to complete
            for _ in range(60):
                if not self._current_task:
                    break
                await asyncio.sleep(1)
        
        self.state = LifecycleState.PAUSED
        
        # Update agent status
        agent = self.db.query(Agent).filter(Agent.id == self.agent_id).first()
        if agent:
            agent.status = AgentStatus.PAUSED
            self.db.commit()
        
        logger.info("Agent paused", agent_id=self.agent_id)
    
    async def resume(self):
        """Resume the agent"""
        if self.state != LifecycleState.PAUSED:
            return
        
        self.state = LifecycleState.RESUMING
        
        # Update agent status
        agent = self.db.query(Agent).filter(Agent.id == self.agent_id).first()
        if agent:
            if agent.current_load > 0:
                agent.status = AgentStatus.BUSY
            else:
                agent.status = AgentStatus.IDLE
            self.db.commit()
        
        self.state = LifecycleState.RUNNING
        
        logger.info("Agent resumed", agent_id=self.agent_id)
    
    async def graceful_stop(self):
        """Gracefully stop the agent"""
        self.state = LifecycleState.STOPPING
        self._shutdown_event.set()
        
        # Wait for current task
        if self._current_task:
            logger.info(
                "Waiting for current task to complete",
                agent_id=self.agent_id,
                task_id=self._current_task
            )
            
            try:
                await asyncio.wait_for(
                    self._wait_for_task_completion(),
                    timeout=self.config.graceful_shutdown_timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Task did not complete in time, releasing",
                    agent_id=self.agent_id,
                    task_id=self._current_task
                )
                await self._release_current_task()
        
        # Cancel tasks
        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        await self._cleanup()
        self.state = LifecycleState.STOPPED
    
    async def force_stop(self):
        """Force stop the agent immediately"""
        self._shutdown_event.set()
        
        # Cancel tasks immediately
        if self._main_task:
            self._main_task.cancel()
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        # Release current task
        if self._current_task:
            await self._release_current_task()
        
        await self._cleanup()
        self.state = LifecycleState.STOPPED
    
    async def _wait_for_task_completion(self):
        """Wait for current task to complete"""
        while self._current_task:
            await asyncio.sleep(0.5)
    
    async def _release_current_task(self):
        """Release the current task back to queue"""
        if not self._current_task:
            return
        
        task = self.db.query(TaskQueue).filter(
            TaskQueue.id == self._current_task
        ).first()
        
        if task:
            task.status = TaskStatus.PENDING
            task.agent_id = None
            task.claimed_at = None
            task.lease_expires = None
        
        agent = self.db.query(Agent).filter(Agent.id == self.agent_id).first()
        if agent:
            agent.current_load = max(0, agent.current_load - 1)
        
        self.db.commit()
        self._current_task = None
    
    async def _cleanup(self):
        """Cleanup agent session"""
        # Update session
        if self._session_id:
            session = self.db.query(AgentSession).filter(
                AgentSession.id == self._session_id
            ).first()
            
            if session:
                session.status = "dead"
        
        # Update agent
        agent = self.db.query(Agent).filter(Agent.id == self.agent_id).first()
        if agent:
            agent.status = AgentStatus.OFFLINE
            agent.desired_status = AgentStatus.OFFLINE
        
        self.db.commit()
        
        # Clear Redis
        if self.redis:
            await self.redis.delete(f"agent:{self.agent_id}:heartbeat")
        
        logger.info("Agent cleanup complete", agent_id=self.agent_id)


# ============================================================================
# API ENDPOINTS
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

lifecycle_router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])

def get_db():
    raise NotImplementedError("Override with actual dependency")

class PauseRequest(BaseModel):
    agent_id: str

class ResumeRequest(BaseModel):
    agent_id: str

class StopRequest(BaseModel):
    agent_id: str
    force: bool = False

@lifecycle_router.post("/pause")
async def pause_agent(
    request: PauseRequest,
    db: Session = Depends(get_db)
):
    """Pause an agent"""
    agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # TODO: Get lifecycle manager instance and call pause
    return {"status": "paused", "agent_id": request.agent_id}

@lifecycle_router.post("/resume")
async def resume_agent(
    request: ResumeRequest,
    db: Session = Depends(get_db)
):
    """Resume a paused agent"""
    agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"status": "resumed", "agent_id": request.agent_id}

@lifecycle_router.post("/stop")
async def stop_agent(
    request: StopRequest,
    db: Session = Depends(get_db)
):
    """Stop an agent"""
    agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"status": "stopped", "agent_id": request.agent_id, "force": request.force}

@lifecycle_router.get("/status/{agent_id}")
async def get_agent_lifecycle_status(agent_id: str, db: Session = Depends(get_db)):
    """Get detailed lifecycle status for an agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    session = db.query(AgentSession).filter(
        and_(
            AgentSession.agent_id == agent_id,
            AgentSession.status == "active"
        )
    ).order_by(AgentSession.started_at.desc()).first()
    
    return {
        "agent_id": agent_id,
        "status": agent.status,
        "desired_status": agent.desired_status,
        "current_load": agent.current_load,
        "session": {
            "id": str(session.id) if session else None,
            "status": session.status if session else None,
            "started_at": session.started_at.isoformat() if session else None,
            "last_heartbeat": session.last_heartbeat.isoformat() if session else None,
        } if session else None
    }
