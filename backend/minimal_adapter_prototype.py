"""
Minimal Adapter Prototype
Quick proof-of-concept for AgentVerse ↔ ChatDev Money bridge
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any

class MinimalAdapter:
    """
    Bare-bones adapter to prove the integration works.
    Hardcoded for content_arbitrage_v1 workflow.
    """
    
    def __init__(self):
        self.runs = {}  # In-memory store for prototype
        print("✅ MinimalAdapter initialized")
    
    async def start_run(self, room_id: str, user_id: str, inputs: Dict) -> str:
        """
        Start a workflow run.
        Returns canonical run_id immediately.
        """
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Create run record
        self.runs[run_id] = {
            "id": run_id,
            "room_id": room_id,
            "user_id": user_id,
            "status": "running",
            "workflow": "content_arbitrage_v1",
            "started_at": datetime.utcnow().isoformat(),
            "inputs": inputs,
            "outputs": {},
            "events": []
        }
        
        print(f"🚀 Started workflow {run_id} for room {room_id}")
        print(f"   Inputs: {inputs}")
        
        # Simulate async execution
        asyncio.create_task(self._simulate_execution(run_id))
        
        return run_id
    
    async def _simulate_execution(self, run_id: str):
        """
        Simulate ChatDev workflow execution.
        In real version, this would call ChatDev API.
        """
        run = self.runs[run_id]
        
        # Step 1: Scout
        await asyncio.sleep(1)
        run["events"].append({
            "event": "agent.step.started",
            "agent": "Scout",
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"🔍 [{run_id}] Scout started")
        
        await asyncio.sleep(2)
        trend = {
            "title": "10 Passive Income Ideas for 2026",
            "subreddit": "sidehustle",
            "upvotes": 1247,
            "opportunity_score": 8.5
        }
        run["events"].append({
            "event": "agent.step.completed",
            "agent": "Scout",
            "output": trend,
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"✅ [{run_id}] Scout found: {trend['title']}")
        
        # Step 2: Maker
        await asyncio.sleep(1)
        run["events"].append({
            "event": "agent.step.started",
            "agent": "Maker",
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"✍️  [{run_id}] Maker started writing")
        
        await asyncio.sleep(3)
        article = {
            "title": trend["title"],
            "word_count": 650,
            "seo_score": 92,
            "excerpt": "Discover 10 proven passive income streams..."
        }
        run["outputs"]["article"] = article
        run["events"].append({
            "event": "agent.step.completed",
            "agent": "Maker",
            "output": article,
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"✅ [{run_id}] Maker completed article")
        
        # Step 3: Merchant
        await asyncio.sleep(1)
        run["events"].append({
            "event": "agent.step.started",
            "agent": "Merchant",
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"🏪 [{run_id}] Merchant publishing")
        
        await asyncio.sleep(2)
        publish_result = {
            "platform": "ghost",
            "url": f"https://blog.example.com/{run_id}",
            "published_at": datetime.utcnow().isoformat()
        }
        run["outputs"]["publish"] = publish_result
        run["outputs"]["estimated_revenue"] = 45.50
        run["outputs"]["platform"] = "ghost"
        
        run["events"].append({
            "event": "agent.step.completed",
            "agent": "Merchant",
            "output": publish_result,
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"✅ [{run_id}] Merchant published to {publish_result['platform']}")
        
        # Complete
        run["status"] = "completed"
        run["completed_at"] = datetime.utcnow().isoformat()
        run["events"].append({
            "event": "workflow.run.completed",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"🎉 [{run_id}] Workflow completed!")
        print(f"   Revenue: ${run['outputs']['estimated_revenue']}")
        print(f"   URL: {publish_result['url']}")
    
    def get_status(self, run_id: str) -> Dict:
        """Get current status of a run"""
        if run_id not in self.runs:
            return {"error": "Run not found"}
        
        run = self.runs[run_id]
        return {
            "id": run_id,
            "status": run["status"],
            "workflow": run["workflow"],
            "started_at": run["started_at"],
            "completed_at": run.get("completed_at"),
            "progress": self._calculate_progress(run),
            "latest_event": run["events"][-1] if run["events"] else None
        }
    
    def _calculate_progress(self, run: Dict) -> int:
        """Calculate completion percentage"""
        if run["status"] == "completed":
            return 100
        
        events = run["events"]
        if not events:
            return 0
        
        # Simple progress based on events
        steps = ["Scout", "Maker", "Merchant"]
        completed = sum(1 for e in events if e["event"] == "agent.step.completed")
        return int((completed / len(steps)) * 100)
    
    def get_events(self, run_id: str) -> list:
        """Get all events for a run"""
        if run_id not in self.runs:
            return []
        return self.runs[run_id]["events"]
    
    def cancel_run(self, run_id: str) -> bool:
        """Cancel a running workflow"""
        if run_id not in self.runs:
            return False
        
        run = self.runs[run_id]
        if run["status"] == "running":
            run["status"] = "cancelled"
            run["events"].append({
                "event": "workflow.run.cancelled",
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"🛑 [{run_id}] Workflow cancelled")
            return True
        
        return False


# FastAPI app for prototype
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Minimal Adapter Prototype")
adapter = MinimalAdapter()

class StartRequest(BaseModel):
    room_id: str
    user_id: str
    subreddit: str = "sidehustle"
    min_upvotes: int = 100

@app.post("/prototype/start")
async def start_workflow(request: StartRequest):
    """Start a workflow from a room"""
    inputs = {
        "subreddit": request.subreddit,
        "min_upvotes": request.min_upvotes
    }
    
    run_id = await adapter.start_run(
        room_id=request.room_id,
        user_id=request.user_id,
        inputs=inputs
    )
    
    return {
        "run_id": run_id,
        "status": "running",
        "message": "Workflow started. Poll /status for updates."
    }

@app.get("/prototype/status/{run_id}")
async def get_status(run_id: str):
    """Get workflow status"""
    return adapter.get_status(run_id)

@app.get("/prototype/events/{run_id}")
async def get_events(run_id: str):
    """Get workflow events"""
    return {"events": adapter.get_events(run_id)}

@app.post("/prototype/cancel/{run_id}")
async def cancel_workflow(run_id: str):
    """Cancel a workflow"""
    success = adapter.cancel_run(run_id)
    return {"cancelled": success}

@app.get("/prototype/demo")
async def demo():
    """Run a complete demo workflow"""
    print("\n" + "="*60)
    print("🎬 DEMO: Starting workflow from AgentVerse Room")
    print("="*60)
    
    # Simulate room context
    room_id = "room_demo_123"
    user_id = "user_admin_456"
    
    # Start workflow
    run_id = await adapter.start_run(
        room_id=room_id,
        user_id=user_id,
        inputs={"subreddit": "sidehustle", "min_upvotes": 100}
    )
    
    # Poll status
    print("\n⏳ Polling status...")
    for i in range(10):
        await asyncio.sleep(1)
        status = adapter.get_status(run_id)
        print(f"   Progress: {status['progress']}% - {status['latest_event']['event'] if status['latest_event'] else 'starting'}")
        
        if status["status"] == "completed":
            break
    
    # Final result
    print("\n" + "="*60)
    print("📊 FINAL RESULT")
    print("="*60)
    
    run = adapter.runs[run_id]
    print(f"Run ID: {run_id}")
    print(f"Status: {run['status']}")
    print(f"Duration: ~8 seconds (simulated)")
    print(f"\nOutputs:")
    print(f"  Article: {run['outputs']['article']['title']}")
    print(f"  Platform: {run['outputs']['publish']['platform']}")
    print(f"  URL: {run['outputs']['publish']['url']}")
    print(f"  💰 Estimated Revenue: ${run['outputs']['estimated_revenue']}")
    
    return {
        "demo": "complete",
        "run_id": run_id,
        "summary": {
            "status": run["status"],
            "revenue": run["outputs"]["estimated_revenue"],
            "url": run["outputs"]["publish"]["url"]
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "minimal-adapter-prototype"}


if __name__ == "__main__":
    import uvicorn
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║     Minimal Adapter Prototype - AgentVerse + ChatDev      ║
╚═══════════════════════════════════════════════════════════╝

This prototype demonstrates:
  ✅ Room context → Workflow execution
  ✅ Scout → Maker → Merchant pipeline
  ✅ Real-time event stream
  ✅ Revenue tracking
  
Endpoints:
  POST /prototype/start      - Start workflow
  GET  /prototype/status/{id} - Check status
  GET  /prototype/demo        - Run full demo
  
Try it:
  curl http://localhost:8002/prototype/demo
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)
