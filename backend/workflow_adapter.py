"""
Workflow Adapter Service
Bridges AgentVerse Room Runtime ↔ ChatDev Money Execution Engine
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
import redis.asyncio as redis
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Float, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workflow_adapter")

Base = declarative_base()

class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ExecutionContext:
    """Input from AgentVerse Room Runtime"""
    tenant_id: str
    project_id: str
    room_id: str
    workflow_id: str
    initiated_by_user_id: str
    credential_refs: List[str]
    input_payload: Dict[str, Any]
    execution_limits: Dict[str, Any]
    correlation_id: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class WorkflowRunHandle:
    """Return value to AgentVerse"""
    run_id: str
    legacy_run_id: Optional[str]
    engine: str
    status: WorkflowStatus
    created_at: datetime

@dataclass
class CanonicalEvent:
    """Standardized event for AgentVerse Event Bus"""
    event_name: str
    event_id: str
    tenant_id: str
    project_id: str
    room_id: str
    workflow_run_id: str
    timestamp: datetime
    payload: Dict[str, Any]

class WorkflowRun(Base):
    """Canonical workflow run record (AgentVerse schema)"""
    __tablename__ = "workflow_runs"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    room_id = Column(String(36), nullable=False, index=True)
    workflow_id = Column(String(100), nullable=False)
    
    # Status tracking
    status = Column(String(20), default="pending")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Inputs/Outputs
    inputs = Column(JSON)
    outputs = Column(JSON)
    
    # ChatDev bridge
    legacy_run_id = Column(String(100))
    legacy_engine = Column(String(50), default="chatdev-money")
    
    # Revenue tracking
    estimated_revenue = Column(Float, default=0.0)
    actual_revenue = Column(Float, default=0.0)
    platform = Column(String(50))
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LegacyRunMapping(Base):
    """Maps canonical run IDs to ChatDev legacy IDs"""
    __tablename__ = "legacy_run_mappings"
    
    canonical_run_id = Column(String(36), primary_key=True)
    legacy_run_id = Column(String(100), unique=True, nullable=False)
    engine = Column(String(50), default="chatdev-money")
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatDevMoneyAdapter:
    """
    Adapter for ChatDev Money workflow engine.
    Implements the WorkflowAdapter protocol.
    """
    
    def __init__(self, 
                 chatdev_api_url: str = "http://localhost:8000",
                 redis_url: str = "redis://localhost:6379",
                 db_url: str = None):
        self.chatdev_api_url = chatdev_api_url
        self.redis_client = redis.from_url(redis_url)
        self.http_client = httpx.AsyncClient(timeout=60.0)
        
        # Database setup
        db_url = db_url or os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/agentverse")
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        logger.info("ChatDevMoneyAdapter initialized")
    
    async def start_run(self, ctx: ExecutionContext) -> WorkflowRunHandle:
        """
        Start a ChatDev Money workflow from AgentVerse context.
        
        1. Create canonical WorkflowRun record
        2. Transform context to ChatDev format
        3. Call ChatDev API to start workflow
        4. Store mapping between IDs
        5. Publish started event
        """
        session = self.Session()
        
        try:
            # 1. Create canonical record
            run_id = str(uuid.uuid4())
            run = WorkflowRun(
                id=run_id,
                tenant_id=ctx.tenant_id,
                project_id=ctx.project_id,
                room_id=ctx.room_id,
                workflow_id=ctx.workflow_id,
                status=WorkflowStatus.PENDING.value,
                inputs=ctx.input_payload,
                started_at=datetime.utcnow()
            )
            session.add(run)
            
            # 2. Transform to ChatDev format
            chatdev_payload = self._to_chatdev_payload(ctx, run_id)
            
            # 3. Call ChatDev API
            logger.info(f"Starting ChatDev workflow for run {run_id}")
            response = await self.http_client.post(
                f"{self.chatdev_api_url}/workflows/execute",
                json=chatdev_payload
            )
            response.raise_for_status()
            chatdev_result = response.json()
            
            legacy_run_id = chatdev_result.get("run_id") or chatdev_result.get("session_id")
            
            # 4. Store mapping
            mapping = LegacyRunMapping(
                canonical_run_id=run_id,
                legacy_run_id=legacy_run_id,
                engine="chatdev-money"
            )
            session.add(mapping)
            
            # Update run with legacy ID
            run.legacy_run_id = legacy_run_id
            run.status = WorkflowStatus.RUNNING.value
            
            session.commit()
            
            # 5. Publish started event
            await self._publish_event(CanonicalEvent(
                event_name="workflow.run.started",
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                tenant_id=ctx.tenant_id,
                project_id=ctx.project_id,
                room_id=ctx.room_id,
                workflow_run_id=run_id,
                timestamp=datetime.utcnow(),
                payload={
                    "workflow_id": ctx.workflow_id,
                    "legacy_run_id": legacy_run_id,
                    "initiated_by": ctx.initiated_by_user_id
                }
            ))
            
            logger.info(f"Workflow started: {run_id} -> ChatDev {legacy_run_id}")
            
            return WorkflowRunHandle(
                run_id=run_id,
                legacy_run_id=legacy_run_id,
                engine="chatdev-money",
                status=WorkflowStatus.RUNNING,
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to start workflow: {e}")
            raise
        finally:
            session.close()
    
    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a running workflow"""
        session = self.Session()
        
        try:
            # Get legacy mapping
            mapping = session.query(LegacyRunMapping).filter_by(
                canonical_run_id=run_id
            ).first()
            
            if not mapping:
                logger.warning(f"No mapping found for run {run_id}")
                return False
            
            # Call ChatDev cancel API
            response = await self.http_client.post(
                f"{self.chatdev_api_url}/workflows/{mapping.legacy_run_id}/cancel"
            )
            
            # Update status
            run = session.query(WorkflowRun).filter_by(id=run_id).first()
            if run:
                run.status = WorkflowStatus.CANCELLED.value
                run.completed_at = datetime.utcnow()
                session.commit()
            
            await self._publish_event(CanonicalEvent(
                event_name="workflow.run.cancelled",
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                tenant_id=run.tenant_id if run else "unknown",
                project_id=run.project_id if run else "unknown",
                room_id=run.room_id if run else "unknown",
                workflow_run_id=run_id,
                timestamp=datetime.utcnow(),
                payload={"reason": "user_requested"}
            ))
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to cancel workflow {run_id}: {e}")
            return False
        finally:
            session.close()
    
    async def get_status(self, run_id: str) -> Dict[str, Any]:
        """Get current status of a workflow run"""
        session = self.Session()
        
        try:
            run = session.query(WorkflowRun).filter_by(id=run_id).first()
            if not run:
                return {"error": "Run not found"}
            
            # If running, poll ChatDev for latest
            if run.status == WorkflowStatus.RUNNING.value and run.legacy_run_id:
                try:
                    response = await self.http_client.get(
                        f"{self.chatdev_api_url}/workflows/{run.legacy_run_id}/status"
                    )
                    if response.status_code == 200:
                        chatdev_status = response.json()
                        # Merge with canonical status
                        return {
                            "run_id": run_id,
                            "status": run.status,
                            "legacy_status": chatdev_status.get("status"),
                            "progress": chatdev_status.get("progress", 0),
                            "started_at": run.started_at.isoformat() if run.started_at else None,
                            "workflow_id": run.workflow_id,
                            "room_id": run.room_id
                        }
                except Exception as e:
                    logger.warning(f"Failed to poll ChatDev status: {e}")
            
            # Return cached status
            return {
                "run_id": run_id,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "workflow_id": run.workflow_id,
                "room_id": run.room_id,
                "outputs": run.outputs
            }
            
        finally:
            session.close()
    
    async def map_legacy_event(self, raw_event: Dict[str, Any]) -> List[CanonicalEvent]:
        """
        Transform ChatDev events to canonical AgentVerse events.
        
        ChatDev events:
        - workflow.started
        - node.started (Scout/Maker/Merchant)
        - node.completed
        - workflow.completed
        - workflow.failed
        """
        events = []
        
        event_type = raw_event.get("type")
        legacy_run_id = raw_event.get("workflow_id") or raw_event.get("run_id")
        
        # Find canonical mapping
        session = self.Session()
        try:
            mapping = session.query(LegacyRunMapping).filter_by(
                legacy_run_id=legacy_run_id
            ).first()
            
            if not mapping:
                logger.warning(f"No mapping for legacy run {legacy_run_id}")
                return []
            
            run = session.query(WorkflowRun).filter_by(id=mapping.canonical_run_id).first()
            if not run:
                return []
            
            # Map event types
            if event_type == "node.started":
                events.append(CanonicalEvent(
                    event_name="agent.step.started",
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    tenant_id=run.tenant_id,
                    project_id=run.project_id,
                    room_id=run.room_id,
                    workflow_run_id=run.id,
                    timestamp=datetime.utcnow(),
                    payload={
                        "agent_role": raw_event.get("node_id"),  # Scout/Maker/Merchant
                        "step_type": raw_event.get("task_type", "unknown")
                    }
                ))
                
            elif event_type == "node.completed":
                events.append(CanonicalEvent(
                    event_name="agent.step.completed",
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    tenant_id=run.tenant_id,
                    project_id=run.project_id,
                    room_id=run.room_id,
                    workflow_run_id=run.id,
                    timestamp=datetime.utcnow(),
                    payload={
                        "agent_role": raw_event.get("node_id"),
                        "output_preview": str(raw_event.get("output", ""))[:200]
                    }
                ))
                
            elif event_type == "workflow.completed":
                # Update run record
                run.status = WorkflowStatus.COMPLETED.value
                run.completed_at = datetime.utcnow()
                run.outputs = raw_event.get("outputs", {})
                
                # Extract revenue if available
                outputs = run.outputs
                if "estimated_revenue" in outputs:
                    run.estimated_revenue = float(outputs["estimated_revenue"])
                if "actual_revenue" in outputs:
                    run.actual_revenue = float(outputs["actual_revenue"])
                if "platform" in outputs:
                    run.platform = outputs["platform"]
                
                session.commit()
                
                events.append(CanonicalEvent(
                    event_name="workflow.run.completed",
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    tenant_id=run.tenant_id,
                    project_id=run.project_id,
                    room_id=run.room_id,
                    workflow_run_id=run.id,
                    timestamp=datetime.utcnow(),
                    payload={
                        "duration_seconds": (run.completed_at - run.started_at).total_seconds() if run.completed_at and run.started_at else 0,
                        "estimated_revenue": run.estimated_revenue,
                        "platform": run.platform
                    }
                ))
                
            elif event_type == "workflow.failed":
                run.status = WorkflowStatus.FAILED.value
                run.completed_at = datetime.utcnow()
                session.commit()
                
                events.append(CanonicalEvent(
                    event_name="workflow.run.failed",
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    tenant_id=run.tenant_id,
                    project_id=run.project_id,
                    room_id=run.room_id,
                    workflow_run_id=run.id,
                    timestamp=datetime.utcnow(),
                    payload={
                        "error": raw_event.get("error", "Unknown error"),
                        "failed_at": raw_event.get("node_id", "unknown")
                    }
                ))
            
            return events
            
        finally:
            session.close()
    
    async def map_output(self, run_id: str) -> Dict[str, Any]:
        """Get final output from a completed workflow"""
        session = self.Session()
        
        try:
            run = session.query(WorkflowRun).filter_by(id=run_id).first()
            if not run:
                return {"error": "Run not found"}
            
            return {
                "run_id": run_id,
                "status": run.status,
                "outputs": run.outputs,
                "estimated_revenue": run.estimated_revenue,
                "actual_revenue": run.actual_revenue,
                "platform": run.platform,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None
            }
            
        finally:
            session.close()
    
    def _to_chatdev_payload(self, ctx: ExecutionContext, canonical_run_id: str) -> Dict[str, Any]:
        """Transform AgentVerse context to ChatDev format"""
        
        # Extract workflow type from workflow_id
        workflow_type = ctx.workflow_id.replace("chatdev-", "").replace("_v1", "")
        
        # Map to ChatDev YAML workflow
        yaml_file = f"{workflow_type}_v1.yaml"
        
        # Build task prompt from room context
        task_prompt = ctx.input_payload.get("brief", "Execute workflow")
        
        # Extract variables for ChatDev
        variables = {
            "subreddit": ctx.input_payload.get("subreddit", "sidehustle"),
            "min_upvotes": ctx.input_payload.get("min_upvotes", 100),
            "content_focus": ctx.input_payload.get("content_focus", "passive income"),
            "canonical_run_id": canonical_run_id,  # For event correlation
            "tenant_id": ctx.tenant_id,
            "room_id": ctx.room_id
        }
        
        return {
            "yaml_file": yaml_file,
            "task_prompt": task_prompt,
            "variables": variables,
            "session_name": f"room_{ctx.room_id}_{canonical_run_id[:8]}",
            "log_level": "INFO"
        }
    
    async def _publish_event(self, event: CanonicalEvent):
        """Publish event to Redis for AgentVerse consumers"""
        channel = f"room:{event.room_id}:events"
        
        message = {
            "event_name": event.event_name,
            "event_id": event.event_id,
            "tenant_id": event.tenant_id,
            "project_id": event.project_id,
            "room_id": event.room_id,
            "workflow_run_id": event.workflow_run_id,
            "timestamp": event.timestamp.isoformat(),
            "payload": event.payload
        }
        
        await self.redis_client.publish(channel, json.dumps(message))
        
        # Also publish to tenant-wide channel for dashboard
        tenant_channel = f"tenant:{event.tenant_id}:events"
        await self.redis_client.publish(tenant_channel, json.dumps(message))
        
        logger.debug(f"Published {event.event_name} to {channel}")
    
    async def handle_webhook(self, legacy_event: Dict[str, Any]):
        """
        Webhook handler for ChatDev events.
        Called by ChatDev when workflow state changes.
        """
        logger.info(f"Received legacy event: {legacy_event.get('type')}")
        
        # Transform to canonical events
        canonical_events = await self.map_legacy_event(legacy_event)
        
        # Publish each event
        for event in canonical_events:
            await self._publish_event(event)
        
        return {"processed": len(canonical_events)}
    
    async def close(self):
        """Cleanup resources"""
        await self.http_client.aclose()
        await self.redis_client.close()


# FastAPI app for the adapter service
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Workflow Adapter Service", version="1.0.0")
adapter = None

class StartWorkflowRequest(BaseModel):
    tenant_id: str
    project_id: str
    room_id: str
    workflow_id: str
    initiated_by_user_id: str
    credential_refs: List[str] = []
    input_payload: Dict[str, Any] = {}
    execution_limits: Dict[str, Any] = {}

@app.on_event("startup")
async def startup():
    global adapter
    adapter = ChatDevMoneyAdapter()

@app.on_event("shutdown")
async def shutdown():
    if adapter:
        await adapter.close()

@app.post("/adapter/workflows/start")
async def start_workflow(request: StartWorkflowRequest):
    """Start a workflow from AgentVerse"""
    try:
        ctx = ExecutionContext(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            room_id=request.room_id,
            workflow_id=request.workflow_id,
            initiated_by_user_id=request.initiated_by_user_id,
            credential_refs=request.credential_refs,
            input_payload=request.input_payload,
            execution_limits=request.execution_limits,
            correlation_id=str(uuid.uuid4())
        )
        
        handle = await adapter.start_run(ctx)
        
        return {
            "run_id": handle.run_id,
            "legacy_run_id": handle.legacy_run_id,
            "engine": handle.engine,
            "status": handle.status.value,
            "created_at": handle.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Start workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/adapter/workflows/{run_id}/cancel")
async def cancel_workflow(run_id: str):
    """Cancel a running workflow"""
    success = await adapter.cancel_run(run_id)
    return {"cancelled": success}

@app.get("/adapter/workflows/{run_id}/status")
async def get_workflow_status(run_id: str):
    """Get workflow status"""
    status = await adapter.get_status(run_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status

@app.post("/adapter/webhooks/chatdev")
async def chatdev_webhook(event: Dict[str, Any]):
    """Webhook for ChatDev events"""
    result = await adapter.handle_webhook(event)
    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "workflow-adapter"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
