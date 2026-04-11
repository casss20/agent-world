"""
Hybrid Workflow Adapter
Supports both MOCK (simulation) and REAL (ChatDev Money) execution modes.
Toggle via USE_REAL_CHATDEV environment variable.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

import httpx

# Configuration
USE_REAL_CHATDEV = os.getenv("USE_REAL_CHATDEV", "false").lower() == "true"
CHATDEV_API_URL = os.getenv("CHATDEV_API_URL", "http://localhost:8000")
CHATDEV_API_KEY = os.getenv("CHATDEV_API_KEY", "")
ADAPTER_MODE = "REAL" if USE_REAL_CHATDEV else "MOCK"

print(f"🔧 Hybrid Adapter Mode: {ADAPTER_MODE}")
print(f"   ChatDev URL: {CHATDEV_API_URL}")


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionContext:
    tenant_id: str
    project_id: str
    room_id: str
    workflow_id: str
    initiated_by_user_id: str
    credential_refs: List[str]
    input_payload: Dict[str, Any]
    execution_limits: Dict[str, Any]
    correlation_id: str


@dataclass
class WorkflowRun:
    run_id: str
    legacy_run_id: Optional[str]
    room_id: str
    workflow_id: str
    status: str
    engine: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: int = 0
    current_step: Optional[str] = None
    outputs: Dict[str, Any] = None
    events: List[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "legacy_run_id": self.legacy_run_id,
            "room_id": self.room_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "engine": self.engine,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "current_step": self.current_step,
            "outputs": self.outputs,
            "events": self.events,
            "error": self.error
        }


class ChatDevClient:
    """HTTP client for real ChatDev Money API"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=CHATDEV_API_URL,
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {CHATDEV_API_KEY}" if CHATDEV_API_KEY else "",
                "Content-Type": "application/json"
            }
        )
    
    async def execute_workflow(
        self,
        yaml_file: str,
        task_prompt: str,
        variables: Dict[str, Any],
        session_name: str
    ) -> Dict[str, Any]:
        """Start a workflow in ChatDev Money"""
        payload = {
            "yaml_file": yaml_file,
            "task_prompt": task_prompt,
            "variables": variables,
            "session_name": session_name,
            "log_level": "INFO"
        }
        
        try:
            response = await self.client.post("/workflows/execute", json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"✅ ChatDev workflow started: {result.get('run_id', result.get('session_id'))}")
            return result
        except httpx.HTTPStatusError as e:
            print(f"❌ ChatDev API error: {e.response.status_code}")
            raise
        except Exception as e:
            print(f"❌ ChatDev connection error: {e}")
            raise
    
    async def get_status(self, run_id: str) -> Dict[str, Any]:
        """Get workflow status from ChatDev"""
        try:
            response = await self.client.get(f"/workflows/{run_id}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "unknown"}
    
    async def cancel_workflow(self, run_id: str) -> bool:
        """Cancel a workflow in ChatDev"""
        try:
            response = await self.client.post(f"/workflows/{run_id}/cancel")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Cancel failed: {e}")
            return False
    
    async def close(self):
        await self.client.aclose()


class MockChatDevEngine:
    """
    Simulated ChatDev Money execution.
    Used when USE_REAL_CHATDEV=false or for testing.
    """
    
    def __init__(self):
        self.runs: Dict[str, WorkflowRun] = {}
        self._client = None
    
    async def start_workflow(self, ctx: ExecutionContext) -> WorkflowRun:
        """Start simulated workflow execution"""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        run = WorkflowRun(
            run_id=run_id,
            legacy_run_id=f"mock_{run_id}",
            room_id=ctx.room_id,
            workflow_id=ctx.workflow_id,
            status=WorkflowStatus.RUNNING.value,
            engine="mock-chatdev",
            started_at=datetime.now(timezone.utc),
            events=[],
            outputs={}
        )
        
        self.runs[run_id] = run
        
        # Start async simulation
        asyncio.create_task(self._simulate_execution(run_id, ctx))
        
        return run
    
    async def _simulate_execution(self, run_id: str, ctx: ExecutionContext):
        """Simulate Scout → Maker → Merchant pipeline"""
        run = self.runs[run_id]
        inputs = ctx.input_payload
        subreddit = inputs.get("subreddit", "sidehustle")
        
        # Scout phase
        await self._emit_event(run, "agent.step.started", {"agent": "Scout"})
        await asyncio.sleep(1.5)
        
        trend = {
            "trend_title": f"10 Passive Income Ideas from r/{subreddit}",
            "opportunity_score": 8.5,
            "summary": f"Hot trend in r/{subreddit} about passive income",
            "keywords": ["passive income", "side hustle", "2026"],
            "monetization_angle": "Affiliate marketing"
        }
        run.outputs["trend_data"] = trend
        run.progress = 33
        run.current_step = "Scout"
        await self._emit_event(run, "agent.step.completed", {"agent": "Scout", "output": trend})
        
        # Maker phase
        await self._emit_event(run, "agent.step.started", {"agent": "Maker"})
        await asyncio.sleep(2.0)
        
        article = {
            "title": trend["trend_title"],
            "word_count": 720,
            "seo_score": 94,
            "content_file": f"content_{run_id}.md"
        }
        run.outputs["article"] = article
        run.progress = 66
        run.current_step = "Maker"
        await self._emit_event(run, "agent.step.completed", {"agent": "Maker", "output": article})
        
        # Merchant phase
        await self._emit_event(run, "agent.step.started", {"agent": "Merchant"})
        await asyncio.sleep(1.5)
        
        publish = {
            "platform": "ghost",
            "url": f"https://blog.example.com/{run_id}",
            "status": "published"
        }
        run.outputs["publish"] = publish
        run.outputs["estimated_revenue"] = 52.50
        run.outputs["platform"] = "ghost"
        run.outputs["published_url"] = publish["url"]
        
        run.progress = 100
        run.current_step = "Merchant"
        run.status = WorkflowStatus.COMPLETED.value
        run.completed_at = datetime.now(timezone.utc)
        
        await self._emit_event(run, "agent.step.completed", {"agent": "Merchant", "output": publish})
        await self._emit_event(run, "workflow.run.completed", {
            "revenue": 52.50,
            "platform": "ghost",
            "url": publish["url"]
        })
        
        print(f"🎉 Mock run {run_id} completed - ${run.outputs['estimated_revenue']} revenue")
    
    async def _emit_event(self, run: WorkflowRun, event_name: str, payload: Dict):
        """Emit event to run's event log"""
        event = {
            "event_name": event_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        run.events.append(event)
    
    def get_status(self, run_id: str) -> Optional[WorkflowRun]:
        return self.runs.get(run_id)
    
    def cancel_run(self, run_id: str) -> bool:
        if run_id in self.runs:
            run = self.runs[run_id]
            if run.status == WorkflowStatus.RUNNING.value:
                run.status = WorkflowStatus.CANCELLED.value
                run.completed_at = datetime.now(timezone.utc)
                return True
        return False


class RealChatDevEngine:
    """
    Real ChatDev Money execution via HTTP API.
    Used when USE_REAL_CHATDEV=true.
    """
    
    def __init__(self):
        self.client = ChatDevClient()
        self.runs: Dict[str, WorkflowRun] = {}
        # Poll for status updates
        self._polling_task = None
    
    async def start_workflow(self, ctx: ExecutionContext) -> WorkflowRun:
        """Start real workflow in ChatDev Money"""
        
        # Build ChatDev payload
        yaml_file = f"{ctx.workflow_id}.yaml"
        task_prompt = f"Execute {ctx.workflow_id} workflow"
        
        variables = {
            **ctx.input_payload,
            "tenant_id": ctx.tenant_id,
            "room_id": ctx.room_id,
            "project_id": ctx.project_id
        }
        
        session_name = f"av_room_{ctx.room_id[:8]}_{uuid.uuid4().hex[:6]}"
        
        # Call ChatDev API
        result = await self.client.execute_workflow(
            yaml_file=yaml_file,
            task_prompt=task_prompt,
            variables=variables,
            session_name=session_name
        )
        
        legacy_run_id = result.get("run_id") or result.get("session_id")
        
        # Create canonical run record
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        run = WorkflowRun(
            run_id=run_id,
            legacy_run_id=legacy_run_id,
            room_id=ctx.room_id,
            workflow_id=ctx.workflow_id,
            status=WorkflowStatus.RUNNING.value,
            engine="chatdev-money",
            started_at=datetime.now(timezone.utc),
            events=[{
                "event_name": "workflow.run.started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"legacy_run_id": legacy_run_id}
            }],
            outputs={}
        )
        
        self.runs[run_id] = run
        
        # Start polling for status
        asyncio.create_task(self._poll_status(run_id, legacy_run_id))
        
        return run
    
    async def _poll_status(self, run_id: str, legacy_run_id: str):
        """Poll ChatDev for status updates"""
        import asyncio
        
        max_polls = 120  # 10 minutes at 5-second intervals
        for _ in range(max_polls):
            await asyncio.sleep(5)
            
            run = self.runs.get(run_id)
            if not run or run.status not in [WorkflowStatus.PENDING.value, WorkflowStatus.RUNNING.value]:
                break
            
            try:
                status = await self.client.get_status(legacy_run_id)
                
                # Map ChatDev status to canonical
                chatdev_status = status.get("status", "unknown")
                
                if chatdev_status == "completed":
                    run.status = WorkflowStatus.COMPLETED.value
                    run.completed_at = datetime.now(timezone.utc)
                    run.progress = 100
                    
                    # Extract outputs
                    outputs = status.get("outputs", {})
                    run.outputs = outputs
                    
                    # Emit completion event
                    run.events.append({
                        "event_name": "workflow.run.completed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": {
                            "revenue": outputs.get("estimated_revenue", 0),
                            "platform": outputs.get("platform"),
                            "url": outputs.get("published_url")
                        }
                    })
                    break
                    
                elif chatdev_status == "failed":
                    run.status = WorkflowStatus.FAILED.value
                    run.completed_at = datetime.now(timezone.utc)
                    run.error = status.get("error", "Unknown error")
                    
                    run.events.append({
                        "event_name": "workflow.run.failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": {"error": run.error}
                    })
                    break
                    
                elif chatdev_status == "running":
                    # Update progress if available
                    run.progress = status.get("progress", run.progress)
                    run.current_step = status.get("current_node", run.current_step)
                    
                    # Check for step events
                    # (ChatDev would emit these via webhook ideally)
                    
            except Exception as e:
                print(f"⚠️  Polling error for {run_id}: {e}")
    
    def get_status(self, run_id: str) -> Optional[WorkflowRun]:
        return self.runs.get(run_id)
    
    async def cancel_run(self, run_id: str) -> bool:
        run = self.runs.get(run_id)
        if run and run.legacy_run_id:
            return await self.client.cancel_workflow(run.legacy_run_id)
        return False
    
    async def close(self):
        await self.client.close()


class HybridWorkflowAdapter:
    """
    Unified adapter that routes to MOCK or REAL ChatDev Money
    based on USE_REAL_CHATDEV environment variable.
    """
    
    def __init__(self):
        self.mode = ADAPTER_MODE
        
        if USE_REAL_CHATDEV:
            print("🔌 Using REAL ChatDev Money engine")
            self.engine = RealChatDevEngine()
        else:
            print("🎭 Using MOCK ChatDev engine (simulation)")
            self.engine = MockChatDevEngine()
    
    async def start_run(self, ctx: ExecutionContext) -> Dict[str, Any]:
        """Start a workflow run"""
        run = await self.engine.start_workflow(ctx)
        return run.to_dict()
    
    async def get_status(self, run_id: str) -> Dict[str, Any]:
        """Get run status"""
        run = self.engine.get_status(run_id)
        if run:
            return run.to_dict()
        return {"error": "Run not found"}
    
    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a run"""
        if isinstance(self.engine, RealChatDevEngine):
            return await self.engine.cancel_run(run_id)
        return self.engine.cancel_run(run_id)
    
    async def get_events(self, run_id: str) -> List[Dict]:
        """Get run events"""
        run = self.engine.get_status(run_id)
        if run:
            return run.events
        return []
    
    async def close(self):
        if isinstance(self.engine, RealChatDevEngine):
            await self.engine.close()


# ============== FASTAPI APP ==============

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Hybrid Workflow Adapter",
    version="2.1.0",
    description=f"Mode: {ADAPTER_MODE} - Toggle with USE_REAL_CHATDEV env var"
)
adapter = None

# Request models
class StartRequest(BaseModel):
    room_id: str
    user_id: str
    workflow_id: str = Field(default="content_arbitrage_v1")
    subreddit: str = Field(default="sidehustle")
    min_upvotes: int = Field(default=100)
    content_focus: str = Field(default="passive income")

class RoomContextRequest(BaseModel):
    tenant_id: str
    project_id: str
    room_id: str
    workflow_id: str = Field(default="content_arbitrage_v1")
    initiated_by_user_id: str
    credential_refs: List[str] = Field(default_factory=list)
    input_payload: Dict[str, Any] = Field(default_factory=dict)

@app.on_event("startup")
async def startup():
    global adapter
    adapter = HybridWorkflowAdapter()
    print(f"✅ Hybrid Adapter initialized in {ADAPTER_MODE} mode")

@app.on_event("shutdown")
async def shutdown():
    if adapter:
        await adapter.close()

@app.post("/prototype/start")
async def start_workflow_simple(request: StartRequest):
    """
    Simple start endpoint (prototype compatibility).
    Automatically builds room context from simple inputs.
    """
    ctx = ExecutionContext(
        tenant_id="prototype-tenant",
        project_id="prototype-project",
        room_id=request.room_id,
        workflow_id=request.workflow_id,
        initiated_by_user_id=request.user_id,
        credential_refs=[],
        input_payload={
            "subreddit": request.subreddit,
            "min_upvotes": request.min_upvotes,
            "content_focus": request.content_focus
        },
        execution_limits={},
        correlation_id=str(uuid.uuid4())
    )
    
    result = await adapter.start_run(ctx)
    return {
        "run_id": result["run_id"],
        "legacy_run_id": result["legacy_run_id"],
        "status": result["status"],
        "engine": result["engine"],
        "message": f"Workflow started using {result['engine']} engine"
    }

@app.post("/adapter/workflows/start")
async def start_workflow_full(request: RoomContextRequest):
    """
    Full-featured start endpoint with complete room context.
    Used by AgentVerse for production integrations.
    """
    ctx = ExecutionContext(
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        room_id=request.room_id,
        workflow_id=request.workflow_id,
        initiated_by_user_id=request.initiated_by_user_id,
        credential_refs=request.credential_refs,
        input_payload=request.input_payload,
        execution_limits={},
        correlation_id=str(uuid.uuid4())
    )
    
    result = await adapter.start_run(ctx)
    return result

@app.get("/prototype/status/{run_id}")
async def get_status_simple(run_id: str):
    """Simple status endpoint (prototype compatibility)"""
    status = await adapter.get_status(run_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status

@app.get("/adapter/workflows/{run_id}/status")
async def get_status_full(run_id: str):
    """Full status endpoint"""
    status = await adapter.get_status(run_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status

@app.get("/prototype/events/{run_id}")
async def get_events(run_id: str):
    """Get event stream for a run"""
    events = await adapter.get_events(run_id)
    return {"events": events, "count": len(events)}

@app.post("/prototype/cancel/{run_id}")
async def cancel_workflow(run_id: str):
    """Cancel a running workflow"""
    success = await adapter.cancel_run(run_id)
    return {"cancelled": success, "run_id": run_id}

@app.get("/prototype/demo")
async def run_demo():
    """Run a complete demo workflow"""
    print("\n" + "="*60)
    print(f"🎬 DEMO: Starting workflow ({ADAPTER_MODE} mode)")
    print("="*60)
    
    ctx = ExecutionContext(
        tenant_id="demo-tenant",
        project_id="demo-project",
        room_id="demo-room-001",
        workflow_id="content_arbitrage_v1",
        initiated_by_user_id="demo-user",
        credential_refs=[],
        input_payload={
            "subreddit": "sidehustle",
            "min_upvotes": 100,
            "content_focus": "passive income"
        },
        execution_limits={},
        correlation_id=str(uuid.uuid4())
    )
    
    result = await adapter.start_run(ctx)
    run_id = result["run_id"]
    
    print(f"\n🚀 Started: {run_id}")
    print(f"   Engine: {result['engine']}")
    print(f"   Status: {result['status']}")
    
    # Poll for completion
    print("\n⏳ Polling status...")
    for i in range(30):
        await asyncio.sleep(1)
        status = await adapter.get_status(run_id)
        
        progress = status.get("progress", 0)
        step = status.get("current_step", "starting")
        print(f"   [{i+1:2d}] {progress:3d}% - {step}")
        
        if status["status"] in ["completed", "failed", "cancelled"]:
            break
    
    # Final result
    final = await adapter.get_status(run_id)
    outputs = final.get("outputs", {})
    
    print("\n" + "="*60)
    print("📊 FINAL RESULT")
    print("="*60)
    print(f"Run ID: {run_id}")
    print(f"Status: {final['status']}")
    print(f"Engine: {final['engine']}")
    
    if outputs:
        print(f"\nOutputs:")
        if "trend_data" in outputs:
            print(f"  📈 Trend: {outputs['trend_data'].get('trend_title', 'N/A')}")
        if "article" in outputs:
            print(f"  📝 Article: {outputs['article'].get('word_count', 0)} words")
        if "publish" in outputs:
            print(f"  🌐 Published: {outputs['publish'].get('platform', 'N/A')}")
        if "estimated_revenue" in outputs:
            print(f"  💰 Revenue: ${outputs['estimated_revenue']}")
    
    return {
        "demo": "complete",
        "mode": ADAPTER_MODE,
        "run": final
    }

@app.get("/health")
async def health_check():
    """Health check with mode indicator"""
    return {
        "status": "healthy",
        "service": "hybrid-workflow-adapter",
        "mode": ADAPTER_MODE,
        "version": "2.1.0",
        "features": {
            "mock_execution": not USE_REAL_CHATDEV,
            "real_execution": USE_REAL_CHATDEV,
            "event_streaming": True,
            "revenue_tracking": True
        }
    }

@app.get("/mode")
async def get_mode():
    """Get current adapter mode"""
    return {
        "mode": ADAPTER_MODE,
        "use_real_chatdev": USE_REAL_CHATDEV,
        "chatdev_url": CHATDEV_API_URL if USE_REAL_CHATDEV else None
    }


if __name__ == "__main__":
    import uvicorn
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     Hybrid Workflow Adapter v2.1.0                          ║
║     Mode: {ADAPTER_MODE:20}                                   ║
╚══════════════════════════════════════════════════════════════╝

Environment Variables:
  USE_REAL_CHATDEV={os.getenv("USE_REAL_CHATDEV", "false")}
  CHATDEV_API_URL={CHATDEV_API_URL}

Endpoints:
  POST /prototype/start      - Start workflow (simple)
  POST /adapter/start        - Start workflow (full context)
  GET  /prototype/status/{id} - Check status
  GET  /prototype/events/{id} - Get events
  GET  /prototype/demo        - Run demo
  GET  /health                - Health check
  GET  /mode                  - Show current mode

Toggle modes:
  USE_REAL_CHATDEV=false python hybrid_adapter.py  # Simulation
  USE_REAL_CHATDEV=true  python hybrid_adapter.py  # Real ChatDev
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)
