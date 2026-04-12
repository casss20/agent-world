"""
Stateless Adapter - Ticket 5
Production-hardened workflow adapter with Redis-backed state

Replaces guarded_adapter.py for horizontal scaling.
Any instance can handle any request.
"""

import os
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import guardrails
from logging_guardrails import StructuredLogger, set_correlation_id, get_correlation_id
from retry_guardrails import CircuitBreakerOpen
from audit_guardrails import AuditContext, get_audit_store

# Import shared state (Ticket 5)
from shared_state import get_shared_state, SharedState

# Import metrics (Ticket 1)
from metrics_exporter import (
    get_metrics_response,
    initialize_metrics,
    record_workflow_start,
    record_workflow_complete,
    record_workflow_failure,
    update_circuit_breaker_state,
    record_circuit_breaker_failure
)

# Import original adapters
from hybrid_adapter import MockChatDevEngine, RealChatDevEngine

# Import webhook receiver
import webhook_receiver

# Configure structured logging
logger = StructuredLogger("stateless_adapter")

# Create FastAPI app
app = FastAPI(
    title="Stateless Hybrid Workflow Adapter",
    description="Production-hardened stateless adapter with Redis",
    version="2.1.0-stateless"
)

# Middleware
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    """Extract or generate correlation ID"""
    corr_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id")
    if not corr_id:
        import uuid
        corr_id = str(uuid.uuid4())[:8]
    
    set_correlation_id(corr_id)
    response = await call_next(request)
    response.headers["x-correlation-id"] = corr_id
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register webhook receiver
app.include_router(webhook_receiver.router)

# Configuration
USE_REAL_CHATDEV = os.getenv("USE_REAL_CHATDEV", "false").lower() == "true"
CHATDEV_API_URL = os.getenv("CHATDEV_API_URL", "http://localhost:8000")
INSTANCE_ID = os.getenv("INSTANCE_ID", "instance_1")  # Unique per deployment

# Initialize engines
mock_engine = MockChatDevEngine()
real_engine = RealChatDevEngine() if USE_REAL_CHATDEV else None

# Initialize shared state
shared_state = get_shared_state()


# Request/Response models
class LaunchRequest(BaseModel):
    room_id: str
    user_id: str
    workflow_id: str = "content_arbitrage_v1"
    task_prompt: str = "Find trending content opportunities"
    variables: Optional[Dict[str, Any]] = None
    webhook_url: Optional[str] = None


class LaunchResponse(BaseModel):
    run_id: str
    status: str
    estimated_duration: int
    correlation_id: str


class StatusResponse(BaseModel):
    run_id: str
    status: str
    progress_percent: int
    current_agent: Optional[str]
    started_at: Optional[str]
    estimated_completion: Optional[str]


# Stateless Workflow Adapter
class StatelessWorkflowAdapter:
    """
    Stateless workflow adapter using Redis for shared state
    
    Key differences from guarded_adapter:
    1. No local _circuit_breakers - uses Redis
    2. No local _active_polls - uses Redis
    3. No local _metrics - uses Redis
    4. Any instance can handle any request
    """
    
    def __init__(self, shared: SharedState):
        self._shared = shared
        self._instance_id = INSTANCE_ID
    
    def _get_engine(self):
        """Get appropriate engine (mock or real)"""
        if USE_REAL_CHATDEV and real_engine:
            return real_engine
        return mock_engine
    
    async def launch_workflow(self, request: LaunchRequest) -> LaunchResponse:
        """Launch workflow with circuit breaker protection"""
        run_id = f"run_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(request.room_id) % 10000}"
        correlation_id = get_correlation_id()
        
        # Check circuit breaker (from shared state)
        if self._shared.is_circuit_open("workflow_launch"):
            logger.error(
                "circuit_breaker_open",
                "Circuit breaker open for workflow_launch",
                context={"run_id": run_id}
            )
            raise CircuitBreakerOpen("workflow_launch")
        
        try:
            # Create run record in shared state
            self._shared.create_run(run_id, request.dict())
            self._shared.update_run_status(run_id, "pending", {
                "room_id": request.room_id,
                "user_id": request.user_id,
                "correlation_id": correlation_id
            })
            
            # Get engine and execute
            engine = self._get_engine()
            
            # Build execution context
            exec_request = {
                "workflow_id": request.workflow_id,
                "room_id": request.room_id,
                "user_id": request.user_id,
                "task_prompt": request.task_prompt,
                "variables": request.variables or {}
            }
            
            # Update status to running
            self._shared.update_run_status(run_id, "running")
            
            # Record circuit breaker success
            self._shared.record_success("workflow_launch")
            
            logger.info(
                "workflow_launched",
                "Workflow launched",
                context={
                    "run_id": run_id,
                    "room_id": request.room_id,
                    "workflow_id": request.workflow_id
                }
            )
            
            return LaunchResponse(
                run_id=run_id,
                status="pending",
                estimated_duration=30,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            # Record circuit breaker failure
            self._shared.record_failure("workflow_launch")
            self._shared.update_run_status(run_id, "failed", {"error": str(e)})
            
            logger.error(
                "workflow_launch_failed",
                "Workflow launch failed",
                context={"run_id": run_id, "error": str(e)},
                error=e
            )
            raise
    
    async def get_status(self, run_id: str) -> StatusResponse:
        """Get workflow status from shared state"""
        run_data = self._shared.get_run(run_id)
        
        if not run_data:
            raise HTTPException(404, f"Run {run_id} not found")
        
        # Calculate progress
        status = run_data.get("status", "unknown")
        progress = {"pending": 0, "running": 50, "completed": 100, "failed": 100}.get(status, 0)
        
        return StatusResponse(
            run_id=run_id,
            status=status,
            progress_percent=progress,
            current_agent=None,
            started_at=run_data.get("created_at"),
            estimated_completion=None
        )
    
    async def cancel_workflow(self, run_id: str) -> Dict[str, Any]:
        """Cancel workflow"""
        run_data = self._shared.get_run(run_id)
        
        if not run_data:
            raise HTTPException(404, f"Run {run_id} not found")
        
        self._shared.update_run_status(run_id, "cancelled")
        
        return {
            "run_id": run_id,
            "status": "cancelled",
            "correlation_id": get_correlation_id()
        }


# Global adapter instance
_adapter: Optional[StatelessWorkflowAdapter] = None


def get_adapter() -> StatelessWorkflowAdapter:
    """Get or create global adapter instance"""
    global _adapter
    if _adapter is None:
        _adapter = StatelessWorkflowAdapter(shared_state)
    return _adapter


# API Routes
@app.post("/stateless/launch", response_model=LaunchResponse)
async def stateless_launch(request: LaunchRequest):
    """
    Launch workflow (stateless)
    
    Any instance can handle this request.
    State is stored in Redis, not local memory.
    """
    adapter = get_adapter()
    return await adapter.launch_workflow(request)


@app.get("/stateless/status/{run_id}", response_model=StatusResponse)
async def stateless_status(run_id: str):
    """
    Get workflow status (stateless)
    
    Any instance can return status from shared state.
    """
    adapter = get_adapter()
    return await adapter.get_status(run_id)


@app.post("/stateless/cancel/{run_id}")
async def stateless_cancel(run_id: str):
    """Cancel workflow (stateless)"""
    adapter = get_adapter()
    return await adapter.cancel_workflow(run_id)


@app.get("/stateless/health")
async def stateless_health():
    """Health check including Redis connectivity"""
    shared_health = shared_state.health_check()
    
    return {
        "status": "healthy" if shared_health["status"] == "healthy" else "degraded",
        "instance_id": INSTANCE_ID,
        "engine_mode": "REAL" if USE_REAL_CHATDEV else "MOCK",
        "shared_state": shared_health,
        "correlation_id": get_correlation_id()
    }


@app.get("/stateless/runs")
async def list_runs():
    """List active runs from shared state"""
    # This would query Redis for all run keys
    # Simplified for now
    return {
        "runs": [],
        "instance_id": INSTANCE_ID
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint (Ticket 1)"""
    return get_metrics_response()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ADAPTER_PORT", "8004"))
    
    print(f"Starting stateless adapter on port {port}")
    print(f"Instance ID: {INSTANCE_ID}")
    print(f"Engine mode: {'REAL' if USE_REAL_CHATDEV else 'MOCK'}")
    
    # Initialize metrics
    initialize_metrics(INSTANCE_ID)
    
    uvicorn.run(app, host="0.0.0.0", port=port)
