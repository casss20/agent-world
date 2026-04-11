"""
Room Engine Bindings - Ticket 5 Implementation
Connects AgentVerse Rooms to Workflow Engines via Adapter
"""

import os
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import httpx
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

# Database base
Base = declarative_base()

# ============== EXTENDED MODELS ==============

class WorkflowEngineBinding(Base):
    """
    Maps rooms to their workflow engines.
    This is the core seam for strangler-pattern migration.
    """
    __tablename__ = 'room_engine_bindings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Engine configuration
    engine_type = Column(String(50), default='chatdev-money')  # 'chatdev-money' | 'native' | 'mock'
    workflow_id = Column(String(100), nullable=False)  # e.g., 'content_arbitrage_v1'
    
    # Feature flag for safe fallback
    use_mock_fallback = Column(Boolean, default=False)
    
    # Engine-specific config
    engine_config = Column(JSONB, default={})
    
    # Credentials reference
    credential_refs = Column(JSONB, default=[])
    
    # Status
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True))
    total_runs = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RoomWorkflowRun(Base):
    """
    Links a Room to its WorkflowRun history.
    Tracks execution history within a room.
    """
    __tablename__ = 'room_workflow_runs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    workflow_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Display info
    run_name = Column(String(255))  # e.g., "Run #5 - March 12"
    description = Column(Text)
    
    # Quick access fields (denormalized for dashboard)
    status = Column(String(20), default='pending')
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    estimated_revenue = Column(Float, default=0.0)
    platform = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        # Index for room history queries
        {'postgresql_using': 'btree'},
    )


class RoomAgentBinding(Base):
    """
    Maps virtual agents (Scout, Maker, Merchant) to rooms.
    Maintains agent presence even when backed by ChatDev workflow.
    """
    __tablename__ = 'room_agent_bindings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    
    # Agent identity
    agent_role = Column(String(50), nullable=False)  # 'scout' | 'maker' | 'merchant'
    display_name = Column(String(255))
    avatar_url = Column(Text)
    color = Column(String(7), default='#00f3ff')
    
    # Runtime state
    status = Column(String(50), default='idle')  # 'idle' | 'working' | 'completed' | 'error'
    current_task = Column(Text)
    last_output_preview = Column(Text)
    
    # Workflow mapping
    workflow_node_id = Column(String(100))  # Maps to ChatDev node_id
    
    entered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now())


# ============== SERVICE LAYER ==============

@dataclass
class LaunchWorkflowRequest:
    """Request to launch a workflow in a room"""
    room_id: str
    workflow_id: str
    user_id: str
    inputs: Dict[str, Any]
    use_mock: bool = False  # Override for testing


@dataclass
class LaunchWorkflowResponse:
    """Response from launching a workflow"""
    run_id: str
    status: str
    engine: str
    message: str
    estimated_duration_seconds: int = 30


class RoomWorkflowService:
    """
    Service for managing room-to-workflow bindings.
    
    This is the main interface for Ticket 5:
    - Binds rooms to workflow engines
    - Launches workflows from rooms
    - Tracks room execution history
    - Manages virtual agent presence
    """
    
    def __init__(self, db_session, adapter_url: str = None):
        self.db = db_session
        self.adapter_url = adapter_url or os.getenv("ADAPTER_URL", "http://localhost:8002")
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        print(f"🔌 RoomWorkflowService initialized")
        print(f"   Adapter URL: {self.adapter_url}")
    
    # ============== Binding Management ==============
    
    async def bind_room_to_engine(
        self,
        room_id: str,
        workflow_id: str,
        engine_type: str = 'chatdev-money',
        credential_refs: List[str] = None,
        use_mock_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Bind a room to a specific workflow engine.
        
        This is the key strangler-pattern seam:
        - Room stays stable (same ID, same context)
        - Engine underneath can change (chatdev-money → native later)
        """
        # Check if binding exists
        existing = self.db.query(WorkflowEngineBinding).filter_by(room_id=uuid.UUID(room_id)).first()
        
        if existing:
            # Update existing binding
            existing.workflow_id = workflow_id
            existing.engine_type = engine_type
            existing.credential_refs = credential_refs or []
            existing.use_mock_fallback = use_mock_fallback
            existing.updated_at = datetime.now(timezone.utc)
            binding = existing
        else:
            # Create new binding
            binding = WorkflowEngineBinding(
                room_id=uuid.UUID(room_id),
                workflow_id=workflow_id,
                engine_type=engine_type,
                credential_refs=credential_refs or [],
                use_mock_fallback=use_mock_fallback
            )
            self.db.add(binding)
        
        self.db.commit()
        
        # Initialize virtual agents for this workflow
        await self._initialize_virtual_agents(room_id, workflow_id)
        
        return {
            "binding_id": str(binding.id),
            "room_id": room_id,
            "workflow_id": workflow_id,
            "engine_type": engine_type,
            "status": "bound"
        }
    
    async def _initialize_virtual_agents(self, room_id: str, workflow_id: str):
        """Create virtual agent bindings for workflow roles"""
        # For content_arbitrage_v1, create Scout, Maker, Merchant
        if workflow_id == "content_arbitrage_v1":
            agents_config = [
                ("scout", "Trend Scout", "#00f3ff", "Scout"),
                ("maker", "Content Maker", "#ff006e", "Maker"),
                ("merchant", "Merchant", "#39ff14", "Merchant")
            ]
            
            for role, name, color, node_id in agents_config:
                # Check if already exists
                existing = self.db.query(RoomAgentBinding).filter_by(
                    room_id=uuid.UUID(room_id),
                    agent_role=role
                ).first()
                
                if not existing:
                    agent_binding = RoomAgentBinding(
                        room_id=uuid.UUID(room_id),
                        agent_role=role,
                        display_name=name,
                        color=color,
                        workflow_node_id=node_id
                    )
                    self.db.add(agent_binding)
            
            self.db.commit()
    
    def get_room_binding(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get the engine binding for a room"""
        binding = self.db.query(WorkflowEngineBinding).filter_by(room_id=uuid.UUID(room_id)).first()
        
        if not binding:
            return None
        
        return {
            "binding_id": str(binding.id),
            "room_id": room_id,
            "engine_type": binding.engine_type,
            "workflow_id": binding.workflow_id,
            "is_active": binding.is_active,
            "use_mock_fallback": binding.use_mock_fallback,
            "total_runs": binding.total_runs,
            "last_run_at": binding.last_run_at.isoformat() if binding.last_run_at else None
        }
    
    # ============== Workflow Launch ==============
    
    async def launch_workflow(
        self,
        request: LaunchWorkflowRequest
    ) -> LaunchWorkflowResponse:
        """
        Launch a workflow from a room.
        
        This is the main user-facing operation:
        1. Get room's engine binding
        2. Build execution context
        3. Call adapter (mock or real based on flag)
        4. Track in room history
        5. Return handle to caller
        """
        # Get room binding
        binding = self.db.query(WorkflowEngineBinding).filter_by(
            room_id=uuid.UUID(request.room_id)
        ).first()
        
        if not binding:
            raise ValueError(f"Room {request.room_id} has no engine binding. Bind first.")
        
        if not binding.is_active:
            raise ValueError(f"Room {request.room_id} engine binding is disabled")
        
        # Determine which engine to use
        # Priority: request.use_mock > binding.use_mock_fallback > actual engine
        if request.use_mock or binding.use_mock_fallback:
            engine_mode = "mock"
            effective_engine = "mock-chatdev"
        else:
            engine_mode = "real"
            effective_engine = binding.engine_type
        
        # Get room context
        room = self.db.execute(
            "SELECT project_id FROM rooms WHERE id = :id",
            {"id": request.room_id}
        ).fetchone()
        
        project_id = str(room[0]) if room else "unknown"
        
        # Build adapter request
        adapter_request = {
            "tenant_id": "default-tenant",  # TODO: Get from auth context
            "project_id": project_id,
            "room_id": request.room_id,
            "workflow_id": request.workflow_id or binding.workflow_id,
            "initiated_by_user_id": request.user_id,
            "credential_refs": binding.credential_refs,
            "input_payload": request.inputs
        }
        
        # Call adapter
        try:
            # Use appropriate endpoint based on mode
            if engine_mode == "mock":
                endpoint = f"{self.adapter_url}/prototype/start"
                # Simple request for mock mode
                simple_request = {
                    "room_id": request.room_id,
                    "user_id": request.user_id,
                    "workflow_id": request.workflow_id or binding.workflow_id,
                    **request.inputs
                }
                response = await self.http_client.post(endpoint, json=simple_request)
            else:
                endpoint = f"{self.adapter_url}/adapter/workflows/start"
                response = await self.http_client.post(endpoint, json=adapter_request)
            
            response.raise_for_status()
            result = response.json()
            
            # Update binding stats
            binding.total_runs += 1
            binding.last_run_at = datetime.now(timezone.utc)
            self.db.commit()
            
            # Create room workflow run record
            room_run = RoomWorkflowRun(
                room_id=uuid.UUID(request.room_id),
                workflow_run_id=uuid.UUID(result["run_id"]),
                run_name=f"Run #{binding.total_runs} - {datetime.now().strftime('%b %d')}",
                status="running",
                started_at=datetime.now(timezone.utc)
            )
            self.db.add(room_run)
            self.db.commit()
            
            return LaunchWorkflowResponse(
                run_id=result["run_id"],
                status=result["status"],
                engine=effective_engine,
                message=f"Workflow launched via {effective_engine}",
                estimated_duration_seconds=30 if engine_mode == "mock" else 120
            )
            
        except httpx.HTTPStatusError as e:
            # If real mode fails and fallback is enabled, try mock
            if engine_mode == "real" and binding.use_mock_fallback:
                print(f"⚠️  Real engine failed, falling back to mock: {e}")
                request.use_mock = True
                return await self.launch_workflow(request)
            
            raise
    
    # ============== Status & History ==============
    
    async def get_room_run_status(self, room_id: str, run_id: str) -> Dict[str, Any]:
        """Get status of a specific run in a room"""
        # Query adapter
        try:
            response = await self.http_client.get(
                f"{self.adapter_url}/prototype/status/{run_id}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "run_id": run_id}
    
    def get_room_run_history(self, room_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get workflow run history for a room"""
        runs = self.db.query(RoomWorkflowRun).filter_by(
            room_id=uuid.UUID(room_id)
        ).order_by(
            RoomWorkflowRun.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "run_id": str(run.workflow_run_id),
                "run_name": run.run_name,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "estimated_revenue": run.estimated_revenue,
                "platform": run.platform
            }
            for run in runs
        ]
    
    async def get_room_active_agents(self, room_id: str) -> List[Dict[str, Any]]:
        """Get virtual agents currently in the room"""
        agents = self.db.query(RoomAgentBinding).filter_by(
            room_id=uuid.UUID(room_id)
        ).all()
        
        return [
            {
                "agent_role": agent.agent_role,
                "display_name": agent.display_name,
                "color": agent.color,
                "status": agent.status,
                "current_task": agent.current_task,
                "last_output_preview": agent.last_output_preview[:200] if agent.last_output_preview else None,
                "last_active_at": agent.last_active_at.isoformat() if agent.last_active_at else None
            }
            for agent in agents
        ]
    
    async def update_agent_status_from_event(
        self,
        room_id: str,
        event_name: str,
        payload: Dict[str, Any]
    ):
        """Update virtual agent status based on workflow events"""
        agent_role = payload.get("agent")
        
        if not agent_role:
            return
        
        agent = self.db.query(RoomAgentBinding).filter_by(
            room_id=uuid.UUID(room_id),
            agent_role=agent_role.lower()
        ).first()
        
        if not agent:
            return
        
        if event_name == "agent.step.started":
            agent.status = "working"
            agent.current_task = payload.get("step", "executing")
        elif event_name == "agent.step.completed":
            agent.status = "completed"
            output = payload.get("output", {})
            if isinstance(output, dict):
                agent.last_output_preview = json.dumps(output)[:500]
        
        agent.last_active_at = datetime.now(timezone.utc)
        self.db.commit()
    
    async def close(self):
        await self.http_client.aclose()


# ============== FASTAPI ROUTER ==============

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

router = APIRouter(prefix="/rooms", tags=["room-workflows"])

# Request/Response models
class BindEngineRequest(BaseModel):
    workflow_id: str = Field(default="content_arbitrage_v1")
    engine_type: str = Field(default="chatdev-money")
    credential_refs: List[str] = Field(default_factory=list)
    use_mock_fallback: bool = Field(default=False)

class LaunchRequest(BaseModel):
    workflow_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    use_mock: bool = Field(default=False)

class LaunchResponse(BaseModel):
    run_id: str
    status: str
    engine: str
    message: str
    estimated_duration_seconds: int

# Dependency to get service
def get_workflow_service():
    # TODO: Proper dependency injection with DB session
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/agentworld")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    service = RoomWorkflowService(db)
    try:
        yield service
    finally:
        service.close()
        db.close()

@router.post("/{room_id}/engine/bind")
async def bind_room_engine(
    room_id: str,
    request: BindEngineRequest,
    service: RoomWorkflowService = Depends(get_workflow_service)
):
    """Bind a room to a workflow engine"""
    try:
        result = await service.bind_room_to_engine(
            room_id=room_id,
            workflow_id=request.workflow_id,
            engine_type=request.engine_type,
            credential_refs=request.credential_refs,
            use_mock_fallback=request.use_mock_fallback
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{room_id}/engine")
async def get_room_engine(
    room_id: str,
    service: RoomWorkflowService = Depends(get_workflow_service)
):
    """Get room's engine binding"""
    binding = service.get_room_binding(room_id)
    if not binding:
        raise HTTPException(status_code=404, detail="Room has no engine binding")
    return binding

@router.post("/{room_id}/workflows/launch", response_model=LaunchResponse)
async def launch_room_workflow(
    room_id: str,
    request: LaunchRequest,
    user_id: str = "current-user",  # TODO: Get from auth
    service: RoomWorkflowService = Depends(get_workflow_service)
):
    """Launch a workflow in a room"""
    try:
        launch_request = LaunchWorkflowRequest(
            room_id=room_id,
            workflow_id=request.workflow_id,
            user_id=user_id,
            inputs=request.inputs,
            use_mock=request.use_mock
        )
        
        result = await service.launch_workflow(launch_request)
        
        return LaunchResponse(
            run_id=result.run_id,
            status=result.status,
            engine=result.engine,
            message=result.message,
            estimated_duration_seconds=result.estimated_duration_seconds
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{room_id}/workflows/history")
async def get_room_workflow_history(
    room_id: str,
    limit: int = 20,
    service: RoomWorkflowService = Depends(get_workflow_service)
):
    """Get workflow run history for a room"""
    history = service.get_room_run_history(room_id, limit)
    return {"runs": history, "count": len(history)}

@router.get("/{room_id}/workflows/{run_id}/status")
async def get_room_workflow_status(
    room_id: str,
    run_id: str,
    service: RoomWorkflowService = Depends(get_workflow_service)
):
    """Get status of a specific workflow run"""
    status = await service.get_room_run_status(room_id, run_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status

@router.get("/{room_id}/agents")
async def get_room_virtual_agents(
    room_id: str,
    service: RoomWorkflowService = Depends(get_workflow_service)
):
    """Get virtual agents (Scout, Maker, Merchant) in a room"""
    agents = await service.get_room_active_agents(room_id)
    return {"agents": agents, "count": len(agents)}

@router.post("/{room_id}/engine/toggle-mock")
async def toggle_mock_mode(
    room_id: str,
    use_mock: bool,
    service: RoomWorkflowService = Depends(get_workflow_service)
):
    """
    Toggle mock fallback mode for a room.
    This is the rollback safety valve.
    """
    binding = service.db.query(WorkflowEngineBinding).filter_by(
        room_id=uuid.UUID(room_id)
    ).first()
    
    if not binding:
        raise HTTPException(status_code=404, detail="Room has no engine binding")
    
    binding.use_mock_fallback = use_mock
    service.db.commit()
    
    return {
        "room_id": room_id,
        "use_mock_fallback": use_mock,
        "message": f"Mock fallback {'enabled' if use_mock else 'disabled'}"
    }
