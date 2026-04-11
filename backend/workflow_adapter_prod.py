"""
Production Workflow Adapter Service
Connects AgentVerse to ChatDev Money execution engine
"""

import asyncio
import json
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# Import our extended models
from models_workflow import (
    Workflow, WorkflowRun, WorkflowEvent, LegacyRunMapping,
    WorkflowStatus, Room, Agent, RevenueEntry,
    init_workflow_db
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("workflow_adapter")

# ============== CONFIGURATION ==============

@dataclass
class AdapterConfig:
    """Configuration for the Workflow Adapter"""
    # ChatDev Money connection
    chatdev_api_url: str = os.getenv("CHATDEV_API_URL", "http://localhost:8000")
    chatdev_api_key: Optional[str] = os.getenv("CHATDEV_API_KEY")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/agentverse")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Timeouts
    chatdev_timeout: float = 30.0
    webhook_secret: Optional[str] = os.getenv("WEBHOOK_SECRET")
    
    # Feature flags
    enable_revenue_tracking: bool = True
    enable_detailed_events: bool = True
    dry_run: bool = False  # For testing without actual ChatDev calls

# ============== DATA CLASSES ==============

@dataclass
class ExecutionContext:
    """Input context from AgentVerse"""
    tenant_id: str
    project_id: str
    room_id: str
    workflow_id: str
    initiated_by_user_id: str
    credential_refs: List[str]
    input_payload: Dict[str, Any]
    execution_limits: Dict[str, Any]
    correlation_id: str
    
    @classmethod
    def from_request(cls, data: Dict) -> "ExecutionContext":
        return cls(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            room_id=data["room_id"],
            workflow_id=data["workflow_id"],
            initiated_by_user_id=data["initiated_by_user_id"],
            credential_refs=data.get("credential_refs", []),
            input_payload=data.get("input_payload", {}),
            execution_limits=data.get("execution_limits", {}),
            correlation_id=data.get("correlation_id", str(uuid.uuid4()))
        )

@dataclass
class WorkflowRunHandle:
    """Return handle for started workflow"""
    run_id: str
    legacy_run_id: Optional[str]
    engine: str
    status: str
    created_at: datetime

@dataclass
class CanonicalEvent:
    """Standardized event for AgentVerse event bus"""
    event_name: str
    event_id: str
    tenant_id: str
    project_id: str
    room_id: str
    workflow_run_id: str
    timestamp: datetime
    payload: Dict[str, Any]
    agent_id: Optional[str] = None
    agent_role: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

# ============== CHATDEV CLIENT ==============

class ChatDevClient:
    """HTTP client for ChatDev Money API"""
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.chatdev_api_url,
            timeout=config.chatdev_timeout,
            headers={
                "Authorization": f"Bearer {config.chatdev_api_key}" if config.chatdev_api_key else "",
                "Content-Type": "application/json"
            }
        )
        logger.info(f"ChatDevClient initialized: {config.chatdev_api_url}")
    
    async def execute_workflow(
        self,
        yaml_file: str,
        task_prompt: str,
        variables: Dict[str, Any],
        session_name: str,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a workflow execution in ChatDev Money.
        
        Returns ChatDev's run/session ID for tracking.
        """
        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would execute: {yaml_file}")
            return {
                "run_id": f"dry_run_{uuid.uuid4().hex[:8]}",
                "status": "running",
                "session_name": session_name
            }
        
        payload = {
            "yaml_file": yaml_file,
            "task_prompt": task_prompt,
            "variables": variables,
            "session_name": session_name,
            "log_level": "INFO"
        }
        
        if callback_url:
            payload["callback_url"] = callback_url
        
        try:
            response = await self.client.post("/workflows/execute", json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"ChatDev workflow started: {result.get('run_id')}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"ChatDev API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"ChatDev connection error: {e}")
            raise
    
    async def get_status(self, run_id: str) -> Dict[str, Any]:
        """Get current status of a workflow run"""
        try:
            response = await self.client.get(f"/workflows/{run_id}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get status for {run_id}: {e}")
            return {"error": str(e)}
    
    async def cancel_workflow(self, run_id: str) -> bool:
        """Cancel a running workflow"""
        try:
            response = await self.client.post(f"/workflows/{run_id}/cancel")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to cancel workflow {run_id}: {e}")
            return False
    
    async def close(self):
        await self.client.aclose()

# ============== WORKFLOW ADAPTER ==============

class WorkflowAdapter:
    """
    Production adapter between AgentVerse and ChatDev Money.
    
    Responsibilities:
    - Transform AgentVerse context to ChatDev format
    - Manage canonical WorkflowRun records
    - Map ChatDev events to canonical events
    - Publish to Redis event bus
    - Handle errors and retries
    """
    
    def __init__(self, config: AdapterConfig = None):
        self.config = config or AdapterConfig()
        
        # Initialize ChatDev client
        self.chatdev = ChatDevClient(self.config)
        
        # Initialize Redis
        self.redis = redis.from_url(self.config.redis_url)
        
        # Initialize database
        self.engine = create_async_engine(self.config.database_url)
        self.async_session = async_sessionmaker(
            self.engine, 
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Event handlers (for testing/debugging)
        self.event_handlers: List[Callable] = []
        
        logger.info("WorkflowAdapter initialized")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session context"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise
    
    async def start_run(self, ctx: ExecutionContext) -> WorkflowRunHandle:
        """
        Start a workflow run from AgentVerse context.
        
        Flow:
        1. Validate workflow exists
        2. Create canonical WorkflowRun record
        3. Transform context to ChatDev format
        4. Call ChatDev to start execution
        5. Store legacy mapping
        6. Update room's active run
        7. Publish started event
        """
        async with self.get_session() as session:
            # 1. Get workflow definition
            workflow = await session.get(Workflow, ctx.workflow_id)
            if not workflow:
                raise ValueError(f"Workflow not found: {ctx.workflow_id}")
            
            if not workflow.is_active:
                raise ValueError(f"Workflow is disabled: {ctx.workflow_id}")
            
            # 2. Create canonical record
            run_id = uuid.uuid4()
            run = WorkflowRun(
                id=run_id,
                tenant_id=uuid.UUID(ctx.tenant_id),
                project_id=uuid.UUID(ctx.project_id),
                room_id=uuid.UUID(ctx.room_id),
                workflow_id=ctx.workflow_id,
                initiated_by_user_id=uuid.UUID(ctx.initiated_by_user_id),
                inputs=ctx.input_payload,
                status=WorkflowStatus.PENDING.value,
                legacy_engine=workflow.engine
            )
            session.add(run)
            await session.flush()  # Get the ID assigned
            
            # 3. Prepare ChatDev payload
            chatdev_payload = self._build_chatdev_payload(ctx, workflow, str(run_id))
            
            # Build callback URL for webhooks (if ChatDev supports it)
            callback_url = None
            # callback_url = f"{AGENTVERSE_URL}/adapter/webhooks/chatdev"
            
            try:
                # 4. Start ChatDev execution
                chatdev_result = await self.chatdev.execute_workflow(
                    yaml_file=chatdev_payload["yaml_file"],
                    task_prompt=chatdev_payload["task_prompt"],
                    variables=chatdev_payload["variables"],
                    session_name=chatdev_payload["session_name"],
                    callback_url=callback_url
                )
                
                legacy_run_id = chatdev_result.get("run_id") or chatdev_result.get("session_id")
                
                # 5. Store mapping
                mapping = LegacyRunMapping(
                    canonical_run_id=run_id,
                    legacy_run_id=legacy_run_id,
                    engine=workflow.engine
                )
                session.add(mapping)
                
                # Update run with legacy info
                run.legacy_run_id = legacy_run_id
                run.status = WorkflowStatus.RUNNING.value
                run.started_at = datetime.now(timezone.utc)
                await session.flush()
                
                # 6. Update room's active run
                room = await session.get(Room, uuid.UUID(ctx.room_id))
                if room:
                    room.active_run_id = run_id
                
                # 7. Publish started event
                await self._publish_event(CanonicalEvent(
                    event_name="workflow.run.started",
                    event_id=f"evt_{uuid.uuid4().hex[:12]}",
                    tenant_id=ctx.tenant_id,
                    project_id=ctx.project_id,
                    room_id=ctx.room_id,
                    workflow_run_id=str(run_id),
                    timestamp=datetime.now(timezone.utc),
                    correlation_id=ctx.correlation_id,
                    payload={
                        "workflow_id": ctx.workflow_id,
                        "workflow_name": workflow.name,
                        "legacy_run_id": legacy_run_id,
                        "engine": workflow.engine,
                        "inputs": ctx.input_payload
                    }
                ))
                
                logger.info(f"Workflow started: {run_id} -> ChatDev {legacy_run_id}")
                
                return WorkflowRunHandle(
                    run_id=str(run_id),
                    legacy_run_id=legacy_run_id,
                    engine=workflow.engine,
                    status=WorkflowStatus.RUNNING.value,
                    created_at=datetime.now(timezone.utc)
                )
                
            except Exception as e:
                # Mark as failed
                run.status = WorkflowStatus.FAILED.value
                run.error_message = str(e)
                await session.flush()
                
                # Publish failure event
                await self._publish_event(CanonicalEvent(
                    event_name="workflow.run.failed",
                    event_id=f"evt_{uuid.uuid4().hex[:12]}",
                    tenant_id=ctx.tenant_id,
                    project_id=ctx.project_id,
                    room_id=ctx.room_id,
                    workflow_run_id=str(run_id),
                    timestamp=datetime.now(timezone.utc),
                    correlation_id=ctx.correlation_id,
                    payload={
                        "error": str(e),
                        "stage": "startup"
                    }
                ))
                
                logger.error(f"Failed to start workflow: {e}")
                raise
    
    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a running workflow"""
        async with self.get_session() as session:
            # Get run details
            run = await session.get(WorkflowRun, uuid.UUID(run_id))
            if not run:
                logger.warning(f"Run not found: {run_id}")
                return False
            
            if run.status not in [WorkflowStatus.PENDING.value, WorkflowStatus.RUNNING.value]:
                logger.info(f"Run {run_id} is already {run.status}")
                return False
            
            # Cancel via ChatDev if we have a legacy ID
            if run.legacy_run_id:
                success = await self.chatdev.cancel_workflow(run.legacy_run_id)
                if not success:
                    logger.warning(f"Failed to cancel ChatDev workflow {run.legacy_run_id}")
            
            # Update status
            run.status = WorkflowStatus.CANCELLED.value
            run.completed_at = datetime.now(timezone.utc)
            
            # Clear room's active run
            room = await session.get(Room, run.room_id)
            if room and room.active_run_id == run.id:
                room.active_run_id = None
            
            # Publish event
            await self._publish_event(CanonicalEvent(
                event_name="workflow.run.cancelled",
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                tenant_id=str(run.tenant_id),
                project_id=str(run.project_id),
                room_id=str(run.room_id),
                workflow_run_id=run_id,
                timestamp=datetime.now(timezone.utc),
                payload={"reason": "user_requested"}
            ))
            
            logger.info(f"Workflow cancelled: {run_id}")
            return True
    
    async def get_status(self, run_id: str) -> Dict[str, Any]:
        """Get current status of a workflow run"""
        async with self.get_session() as session:
            # Load run with workflow info
            result = await session.execute(
                select(WorkflowRun, Workflow)
                .join(Workflow, WorkflowRun.workflow_id == Workflow.id)
                .where(WorkflowRun.id == uuid.UUID(run_id))
            )
            row = result.first()
            
            if not row:
                return {"error": "Run not found", "run_id": run_id}
            
            run, workflow = row
            
            # Build response
            status = {
                "run_id": run_id,
                "status": run.status,
                "workflow_id": run.workflow_id,
                "workflow_name": workflow.name,
                "room_id": str(run.room_id),
                "progress_percent": run.progress_percent,
                "current_step": run.current_step,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "estimated_revenue": run.estimated_revenue,
                "actual_revenue": run.actual_revenue,
                "platform": run.platform,
                "published_url": run.published_url,
            }
            
            # If running, optionally poll ChatDev for fresh status
            if run.status == WorkflowStatus.RUNNING.value and run.legacy_run_id:
                try:
                    chatdev_status = await self.chatdev.get_status(run.legacy_run_id)
                    if "error" not in chatdev_status:
                        status["legacy_status"] = chatdev_status.get("status")
                        status["legacy_progress"] = chatdev_status.get("progress")
                except Exception as e:
                    logger.warning(f"Could not get ChatDev status: {e}")
            
            return status
    
    async def handle_chatdev_webhook(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle webhook callbacks from ChatDev Money.
        
        ChatDev sends events like:
        - node.started / node.completed
        - workflow.completed / workflow.failed
        """
        event_type = event_data.get("type")
        legacy_run_id = event_data.get("workflow_id") or event_data.get("run_id")
        
        if not legacy_run_id:
            logger.warning("Webhook missing run_id")
            return {"error": "missing run_id"}
        
        logger.info(f"Processing ChatDev webhook: {event_type} for {legacy_run_id}")
        
        # Map to canonical events
        canonical_events = await self._map_chatdev_event(event_data, legacy_run_id)
        
        # Publish each event
        for event in canonical_events:
            await self._publish_event(event)
        
        return {"processed": len(canonical_events)}
    
    async def _map_chatdev_event(
        self, 
        raw_event: Dict[str, Any], 
        legacy_run_id: str
    ) -> List[CanonicalEvent]:
        """Transform ChatDev event to canonical AgentVerse events"""
        events = []
        
        async with self.get_session() as session:
            # Find canonical mapping
            result = await session.execute(
                select(LegacyRunMapping, WorkflowRun)
                .join(WorkflowRun, LegacyRunMapping.canonical_run_id == WorkflowRun.id)
                .where(LegacyRunMapping.legacy_run_id == legacy_run_id)
            )
            mapping = result.first()
            
            if not mapping:
                logger.warning(f"No mapping for legacy run: {legacy_run_id}")
                return []
            
            mapping_row, run = mapping
            
            event_type = raw_event.get("type")
            node_id = raw_event.get("node_id", "")
            
            # Map agent roles
            agent_role = None
            if node_id in ["Scout", "scout"]:
                agent_role = "scout"
            elif node_id in ["Maker", "maker"]:
                agent_role = "maker"
            elif node_id in ["Merchant", "merchant"]:
                agent_role = "merchant"
            
            # Handle different event types
            if event_type == "node.started":
                events.append(CanonicalEvent(
                    event_name="agent.step.started",
                    event_id=f"evt_{uuid.uuid4().hex[:12]}",
                    tenant_id=str(run.tenant_id),
                    project_id=str(run.project_id),
                    room_id=str(run.room_id),
                    workflow_run_id=str(run.id),
                    timestamp=datetime.now(timezone.utc),
                    agent_role=agent_role,
                    payload={
                        "step_name": node_id,
                        "agent_role": agent_role,
                        "legacy_node_id": node_id
                    }
                ))
                
                # Update run current step
                run.current_step = node_id
                
            elif event_type == "node.completed":
                output = raw_event.get("output", {})
                
                events.append(CanonicalEvent(
                    event_name="agent.step.completed",
                    event_id=f"evt_{uuid.uuid4().hex[:12]}",
                    tenant_id=str(run.tenant_id),
                    project_id=str(run.project_id),
                    room_id=str(run.room_id),
                    workflow_run_id=str(run.id),
                    timestamp=datetime.now(timezone.utc),
                    agent_role=agent_role,
                    payload={
                        "step_name": node_id,
                        "agent_role": agent_role,
                        "output_preview": str(output)[:500] if output else None
                    }
                ))
                
                # Store Scout output in workflow run
                if agent_role == "scout" and isinstance(output, dict):
                    current_outputs = run.outputs or {}
                    current_outputs["scout"] = output
                    run.outputs = current_outputs
                    
                    # Update progress
                    run.progress_percent = 33
                
                elif agent_role == "maker":
                    run.progress_percent = 66
                
            elif event_type == "workflow.completed":
                outputs = raw_event.get("outputs", {})
                
                # Update run
                run.status = WorkflowStatus.COMPLETED.value
                run.completed_at = datetime.now(timezone.utc)
                run.outputs = outputs
                
                # Extract revenue info
                if "estimated_revenue" in outputs:
                    run.estimated_revenue = float(outputs["estimated_revenue"])
                if "actual_revenue" in outputs:
                    run.actual_revenue = float(outputs["actual_revenue"])
                if "platform" in outputs:
                    run.platform = outputs["platform"]
                if "published_url" in outputs:
                    run.published_url = outputs["published_url"]
                
                run.progress_percent = 100
                
                # Create revenue entry if tracking enabled
                if self.config.enable_revenue_tracking and run.estimated_revenue > 0:
                    revenue_entry = RevenueEntry(
                        tenant_id=run.tenant_id,
                        workflow_run_id=run.id,
                        tracking_id=f"rev_{uuid.uuid4().hex[:8]}",
                        content_title=outputs.get("article_title", "Unknown"),
                        platform=run.platform or "unknown",
                        estimated_revenue=run.estimated_revenue,
                        actual_revenue=run.actual_revenue,
                        published_url=run.published_url,
                        status="projected"
                    )
                    session.add(revenue_entry)
                
                # Clear room's active run
                room = await session.get(Room, run.room_id)
                if room and room.active_run_id == run.id:
                    room.active_run_id = None
                
                events.append(CanonicalEvent(
                    event_name="workflow.run.completed",
                    event_id=f"evt_{uuid.uuid4().hex[:12]}",
                    tenant_id=str(run.tenant_id),
                    project_id=str(run.project_id),
                    room_id=str(run.room_id),
                    workflow_run_id=str(run.id),
                    timestamp=datetime.now(timezone.utc),
                    payload={
                        "duration_seconds": (
                            (run.completed_at - run.started_at).total_seconds()
                            if run.completed_at and run.started_at else 0
                        ),
                        "estimated_revenue": run.estimated_revenue,
                        "platform": run.platform,
                        "published_url": run.published_url
                    }
                ))
                
            elif event_type == "workflow.failed":
                run.status = WorkflowStatus.FAILED.value
                run.completed_at = datetime.now(timezone.utc)
                run.error_message = raw_event.get("error", "Unknown error")
                
                # Clear room's active run
                room = await session.get(Room, run.room_id)
                if room and room.active_run_id == run.id:
                    room.active_run_id = None
                
                events.append(CanonicalEvent(
                    event_name="workflow.run.failed",
                    event_id=f"evt_{uuid.uuid4().hex[:12]}",
                    tenant_id=str(run.tenant_id),
                    project_id=str(run.project_id),
                    room_id=str(run.room_id),
                    workflow_run_id=str(run.id),
                    timestamp=datetime.now(timezone.utc),
                    payload={
                        "error": run.error_message,
                        "failed_at_step": run.current_step
                    }
                ))
            
            await session.flush()
            return events
    
    def _build_chatdev_payload(
        self, 
        ctx: ExecutionContext, 
        workflow: Workflow,
        canonical_run_id: str
    ) -> Dict[str, Any]:
        """Transform AgentVerse context to ChatDev format"""
        
        # Build task prompt from workflow defaults + user inputs
        task_prompt = f"Execute {workflow.name} workflow"
        
        # Merge default inputs with user inputs
        variables = {**workflow.default_inputs, **ctx.input_payload}
        
        # Add metadata for correlation
        variables["canonical_run_id"] = canonical_run_id
        variables["tenant_id"] = ctx.tenant_id
        variables["room_id"] = ctx.room_id
        variables["project_id"] = ctx.project_id
        
        return {
            "yaml_file": workflow.yaml_file or f"{workflow.id}.yaml",
            "task_prompt": task_prompt,
            "variables": variables,
            "session_name": f"av_room_{ctx.room_id[:8]}_{canonical_run_id[:8]}",
            "log_level": "INFO"
        }
    
    async def _publish_event(self, event: CanonicalEvent):
        """Publish event to Redis for AgentVerse consumers"""
        message = {
            "event_name": event.event_name,
            "event_id": event.event_id,
            "tenant_id": event.tenant_id,
            "project_id": event.project_id,
            "room_id": event.room_id,
            "workflow_run_id": event.workflow_run_id,
            "timestamp": event.timestamp.isoformat(),
            "agent_role": event.agent_role,
            "correlation_id": event.correlation_id,
            "payload": event.payload
        }
        
        # Publish to room-specific channel
        room_channel = f"room:{event.room_id}:events"
        await self.redis.publish(room_channel, json.dumps(message))
        
        # Publish to tenant-wide channel
        tenant_channel = f"tenant:{event.tenant_id}:events"
        await self.redis.publish(tenant_channel, json.dumps(message))
        
        # Store in database for audit
        async with self.get_session() as session:
            event_record = WorkflowEvent(
                tenant_id=uuid.UUID(event.tenant_id),
                room_id=uuid.UUID(event.room_id),
                workflow_run_id=uuid.UUID(event.workflow_run_id),
                event_name=event.event_name,
                event_id=event.event_id,
                agent_role=event.agent_role,
                payload=event.payload,
                correlation_id=event.correlation_id
            )
            session.add(event_record)
        
        # Call registered handlers
        for handler in self.event_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
        
        logger.debug(f"Published {event.event_name} to {room_channel}")
    
    def add_event_handler(self, handler: Callable):
        """Register an event handler for testing/debugging"""
        self.event_handlers.append(handler)
    
    async def get_run_history(
        self,
        room_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get workflow run history with filters"""
        async with self.get_session() as session:
            query = select(WorkflowRun, Workflow).join(Workflow)
            
            if room_id:
                query = query.where(WorkflowRun.room_id == uuid.UUID(room_id))
            if tenant_id:
                query = query.where(WorkflowRun.tenant_id == uuid.UUID(tenant_id))
            if status:
                query = query.where(WorkflowRun.status == status)
            
            query = query.order_by(WorkflowRun.created_at.desc()).limit(limit)
            
            result = await session.execute(query)
            
            history = []
            for run, workflow in result:
                history.append({
                    "run_id": str(run.id),
                    "workflow_id": run.workflow_id,
                    "workflow_name": workflow.name,
                    "room_id": str(run.room_id),
                    "status": run.status,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "estimated_revenue": run.estimated_revenue,
                    "platform": run.platform
                })
            
            return history
    
    async def close(self):
        """Cleanup resources"""
        await self.chatdev.close()
        await self.redis.close()
        await self.engine.dispose()

# ============== FASTAPI APP ==============

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="Workflow Adapter Service", version="2.0.0")
adapter: Optional[WorkflowAdapter] = None

# Request/Response models
class StartWorkflowRequest(BaseModel):
    tenant_id: str
    project_id: str
    room_id: str
    workflow_id: str = Field(default="content_arbitrage_v1")
    initiated_by_user_id: str
    credential_refs: List[str] = Field(default_factory=list)
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    execution_limits: Dict[str, Any] = Field(default_factory=dict)

class StartWorkflowResponse(BaseModel):
    run_id: str
    legacy_run_id: Optional[str]
    engine: str
    status: str
    created_at: str

class StatusResponse(BaseModel):
    run_id: str
    status: str
    progress_percent: int
    current_step: Optional[str]
    estimated_revenue: float
    platform: Optional[str]

@app.on_event("startup")
async def startup():
    global adapter
    config = AdapterConfig()
    adapter = WorkflowAdapter(config)
    logger.info("Workflow Adapter Service started")

@app.on_event("shutdown")
async def shutdown():
    if adapter:
        await adapter.close()
    logger.info("Workflow Adapter Service stopped")

@app.post("/adapter/workflows/start", response_model=StartWorkflowResponse)
async def start_workflow(request: StartWorkflowRequest):
    """Start a workflow from AgentVerse"""
    try:
        ctx = ExecutionContext.from_request(request.dict())
        handle = await adapter.start_run(ctx)
        
        return StartWorkflowResponse(
            run_id=handle.run_id,
            legacy_run_id=handle.legacy_run_id,
            engine=handle.engine,
            status=handle.status,
            created_at=handle.created_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Start workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/adapter/workflows/{run_id}/cancel")
async def cancel_workflow(run_id: str):
    """Cancel a running workflow"""
    success = await adapter.cancel_run(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found or already completed")
    return {"cancelled": True, "run_id": run_id}

@app.get("/adapter/workflows/{run_id}/status", response_model=StatusResponse)
async def get_workflow_status(run_id: str):
    """Get workflow status"""
    status = await adapter.get_status(run_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return StatusResponse(
        run_id=status["run_id"],
        status=status["status"],
        progress_percent=status.get("progress_percent", 0),
        current_step=status.get("current_step"),
        estimated_revenue=status.get("estimated_revenue", 0.0),
        platform=status.get("platform")
    )

@app.get("/adapter/workflows/history")
async def get_workflow_history(
    room_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """Get workflow run history"""
    history = await adapter.get_run_history(room_id, tenant_id, status, limit)
    return {"runs": history, "count": len(history)}

@app.post("/adapter/webhooks/chatdev")
async def chatdev_webhook(event_data: Dict[str, Any], background_tasks: BackgroundTasks):
    """Webhook for ChatDev Money events"""
    # Process webhook in background to respond quickly
    result = await adapter.handle_chatdev_webhook(event_data)
    return result

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "workflow-adapter",
        "version": "2.0.0",
        "chatdev_connected": adapter is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
