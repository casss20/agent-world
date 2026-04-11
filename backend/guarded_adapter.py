"""
Guarded Hybrid Adapter
Production-hardened workflow adapter with full guardrails

Integrates:
- Structured logging with correlation IDs
- Timeouts, retries, circuit breakers
- Audit trail persistence
- Mock/Real toggle with fallback
"""

import os
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import guardrails
from logging_guardrails import (
    StructuredLogger, CorrelationIdMiddleware, 
    set_correlation_id, get_correlation_id
)
from retry_guardrails import (
    WORKFLOW_LAUNCH_GUARDS, STATUS_POLL_GUARDS, CANCEL_GUARDS,
    register_cancellation, unregister_cancellation, get_cancellation,
    CircuitBreakerOpen
)
from audit_guardrails import AuditContext, get_audit_store

# Import original adapters
from hybrid_adapter import MockChatDevEngine, RealChatDevEngine, HybridEngine


# Configure structured logging
logger = StructuredLogger("guarded_adapter")

# Create FastAPI app with middleware
app = FastAPI(
    title="Guarded Hybrid Workflow Adapter",
    description="Production-hardened workflow adapter with full observability",
    version="2.0.0-guarded"
)

# Add correlation ID middleware
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    """Extract or generate correlation ID for each request"""
    corr_id = request.headers.get("x-correlation-id")
    if not corr_id:
        corr_id = request.headers.get("x-request-id")
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


# Configuration
USE_REAL_CHATDEV = os.getenv("USE_REAL_CHATDEV", "false").lower() == "true"
CHATDEV_URL = os.getenv("CHATDEV_URL", "http://localhost:8000")

# Initialize engines
mock_engine = MockChatDevEngine()
real_engine = RealChatDevEngine(CHATDEV_URL) if USE_REAL_CHATDEV else None

# Request/Response models
class LaunchRequest(BaseModel):
    room_id: str
    user_id: str
    workflow_id: str = "content_arbitrage_v1"
    subreddit: str = "sidehustle"
    min_upvotes: int = 100
    use_mock: Optional[bool] = None  # Override global setting


class GuardedLaunchResponse(BaseModel):
    run_id: str
    correlation_id: str
    status: str
    engine_mode: str
    estimated_duration_seconds: int
    audit_trail_id: str


class GuardedStatusResponse(BaseModel):
    run_id: str
    correlation_id: str
    status: str
    progress: int
    current_step: Optional[str]
    outputs: Optional[Dict[str, Any]]
    error: Optional[str]
    duration_ms: Optional[int]
    event_count: int


@app.get("/health")
async def health_check():
    """Health check with engine status"""
    return {
        "status": "healthy",
        "engine_mode": "MOCK" if not USE_REAL_CHATDEV else "REAL",
        "real_engine_available": real_engine is not None,
        "correlation_id": get_correlation_id()
    }


@app.post("/guarded/launch", response_model=GuardedLaunchResponse)
async def guarded_launch(
    request: LaunchRequest,
    background_tasks: BackgroundTasks
):
    """
    Launch workflow with full guardrails
    
    - Structured logging with correlation ID
    - Timeout/retry protection
    - Circuit breaker
    - Audit trail
    """
    corr_id = get_correlation_id()
    run_id = f"run_{os.urandom(4).hex()}"
    
    # Determine engine mode
    use_mock = request.use_mock if request.use_mock is not None else not USE_REAL_CHATDEV
    engine_mode = "MOCK" if use_mock else "REAL"
    
    logger.info("launch_requested",
               f"Workflow launch requested for room {request.room_id}",
               {"room_id": request.room_id, "user_id": request.user_id,
                "workflow_id": request.workflow_id, "engine_mode": engine_mode,
                "correlation_id": corr_id})
    
    # Select engine
    if use_mock or not real_engine:
        engine = mock_engine
    else:
        engine = real_engine
    
    try:
        # Execute with guardrails
        async def do_launch():
            with AuditContext(run_id, request.room_id, request.user_id, request.workflow_id) as audit:
                audit.record_launch({
                    "subreddit": request.subreddit,
                    "min_upvotes": request.min_upvotes,
                    "engine_mode": engine_mode
                })
                
                # Register for cancellation
                cancel_handle = register_cancellation(run_id)
                
                try:
                    result = await engine.execute_workflow(
                        workflow_id=request.workflow_id,
                        inputs={
                            "subreddit": request.subreddit,
                            "min_upvotes": request.min_upvotes
                        }
                    )
                    
                    # Update with run_id
                    result["run_id"] = run_id
                    result["correlation_id"] = corr_id
                    
                    # Schedule background completion tracking
                    background_tasks.add_task(
                        track_completion, run_id, request.room_id, request.user_id, engine
                    )
                    
                    return result
                    
                finally:
                    unregister_cancellation(run_id)
        
        result = await WORKFLOW_LAUNCH_GUARDS.execute(do_launch)
        
        logger.info("launch_success",
                   f"Workflow {run_id} launched successfully",
                   {"run_id": run_id, "engine_mode": engine_mode})
        
        return GuardedLaunchResponse(
            run_id=run_id,
            correlation_id=corr_id,
            status="launched",
            engine_mode=engine_mode,
            estimated_duration_seconds=5 if use_mock else 60,
            audit_trail_id=run_id
        )
        
    except CircuitBreakerOpen:
        logger.error("circuit_breaker_open",
                    "Launch rejected - circuit breaker open",
                    {"room_id": request.room_id})
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable - circuit breaker open"
        )
    except Exception as e:
        logger.error("launch_failed",
                    f"Launch failed: {str(e)}",
                    {"room_id": request.room_id}, error=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/guarded/status/{run_id}", response_model=GuardedStatusResponse)
async def guarded_status(run_id: str):
    """Get status with guardrails and audit info"""
    corr_id = get_correlation_id()
    
    logger.debug("status_requested",
                f"Status requested for {run_id}",
                {"run_id": run_id})
    
    try:
        async def do_status():
            # Try mock engine first (in-memory state)
            status = mock_engine.get_status(run_id)
            if status["status"] != "not_found":
                return status
            
            # Try real engine if available
            if real_engine:
                return await real_engine.get_status(run_id)
            
            return status
        
        result = await STATUS_POLL_GUARDS.execute(do_status)
        
        # Get audit info
        audit_store = get_audit_store()
        run = audit_store.get_run(run_id)
        event_count = len(audit_store.get_run_events(run_id)) if run else 0
        
        return GuardedStatusResponse(
            run_id=run_id,
            correlation_id=corr_id,
            status=result.get("status", "unknown"),
            progress=result.get("progress", 0),
            current_step=result.get("current_step"),
            outputs=result.get("outputs"),
            error=result.get("error"),
            duration_ms=result.get("duration_ms"),
            event_count=event_count
        )
        
    except Exception as e:
        logger.error("status_failed",
                    f"Status check failed: {str(e)}",
                    {"run_id": run_id}, error=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/guarded/cancel/{run_id}")
async def guarded_cancel(run_id: str):
    """Cancel workflow with guardrails"""
    corr_id = get_correlation_id()
    
    logger.info("cancel_requested",
               f"Cancellation requested for {run_id}",
               {"run_id": run_id})
    
    try:
        async def do_cancel():
            # Mark for cancellation
            cancel_handle = get_cancellation(run_id)
            if cancel_handle:
                cancel_handle.cancel("user_request")
            
            # Try to cancel in engine
            if real_engine:
                return await real_engine.cancel_workflow(run_id)
            
            return {"cancelled": True}
        
        result = await CANCEL_GUARDS.execute(do_cancel)
        
        # Record in audit
        audit_store = get_audit_store()
        run = audit_store.get_run(run_id)
        if run:
            audit_store.record_run_completion(
                run_id=run_id,
                status="cancelled",
                completed_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=None,
                error_message="Cancelled by user"
            )
        
        return {"status": "cancelled", "run_id": run_id, "correlation_id": corr_id}
        
    except Exception as e:
        logger.error("cancel_failed",
                    f"Cancel failed: {str(e)}",
                    {"run_id": run_id}, error=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/guarded/audit/{run_id}")
async def get_audit_trail(run_id: str):
    """Get full audit trail for a run"""
    audit_store = get_audit_store()
    trail = audit_store.export_run_audit(run_id)
    
    if not trail:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return trail


@app.get("/guarded/runs")
async def list_runs(room_id: Optional[str] = None, limit: int = 100):
    """List workflow runs with filtering"""
    audit_store = get_audit_store()
    
    if room_id:
        runs = audit_store.get_room_runs(room_id, limit=limit)
    else:
        # Get all recent runs (would need pagination in production)
        runs = []
    
    return {
        "runs": [r.to_dict() for r in runs],
        "count": len(runs)
    }


@app.post("/guarded/toggle-engine")
async def toggle_engine_mode(mode: str):
    """
    Admin endpoint to toggle between MOCK and REAL
    
    For emergency fallback - changes runtime mode without restart
    """
    global USE_REAL_CHATDEV, real_engine
    
    if mode not in ["MOCK", "REAL"]:
        raise HTTPException(status_code=400, detail="Mode must be MOCK or REAL")
    
    logger.critical("engine_mode_toggle",
                   f"Engine mode toggled from {'REAL' if USE_REAL_CHATDEV else 'MOCK'} to {mode}",
                   {"previous": "REAL" if USE_REAL_CHATDEV else "MOCK", "new": mode})
    
    if mode == "REAL":
        USE_REAL_CHATDEV = True
        if not real_engine:
            real_engine = RealChatDevEngine(CHATDEV_URL)
    else:
        USE_REAL_CHATDEV = False
    
    return {"mode": mode, "correlation_id": get_correlation_id()}


async def track_completion(
    run_id: str,
    room_id: str,
    user_id: str,
    engine
):
    """
    Background task to track workflow completion and record audit
    """
    try:
        # Poll until complete
        max_attempts = 60  # 5 minutes at 5 second intervals
        for attempt in range(max_attempts):
            await asyncio.sleep(5)
            
            status = engine.get_status(run_id)
            if status["status"] in ["completed", "failed", "cancelled"]:
                # Record completion in audit
                audit_store = get_audit_store()
                run = audit_store.get_run(run_id)
                
                if run and status["status"] == "completed":
                    outputs = status.get("outputs", {})
                    audit_store.record_run_completion(
                        run_id=run_id,
                        status="completed",
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        duration_ms=status.get("duration_ms"),
                        revenue=outputs.get("estimated_revenue"),
                        platform=outputs.get("platform")
                    )
                    
                    logger.info("completion_tracked",
                               f"Run {run_id} completion tracked",
                               {"run_id": run_id, "revenue": outputs.get("estimated_revenue")})
                
                break
        
    except Exception as e:
        logger.error("completion_tracking_failed",
                    f"Failed to track completion for {run_id}",
                    {"run_id": run_id}, error=e)


if __name__ == "__main__":
    import uvicorn
    
    print(f"🛡️ Guarded Hybrid Adapter Starting...")
    print(f"   Engine Mode: {'REAL' if USE_REAL_CHATDEV else 'MOCK'}")
    print(f"   Real Engine Available: {real_engine is not None}")
    print(f"   Health: http://localhost:8003/health")
    print(f"   Launch: POST http://localhost:8003/guarded/launch")
    print(f"   Status: GET  http://localhost:8003/guarded/status/{{run_id}}")
    print(f"   Audit:  GET  http://localhost:8003/guarded/audit/{{run_id}}")
    
    uvicorn.run(app, host="0.0.0.0", port=8003)
