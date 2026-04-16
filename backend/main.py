from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import json
import uuid
from datetime import datetime
import random

# Import OpenTelemetry
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from telemetry import setup_telemetry, shutdown_telemetry, get_logger

# Import security middleware
from security_middleware import SecurityMiddleware

# Import additional routers
from chatdev_workflow_routes import router as chatdev_router
from ledger_routes import router as ledger_router
from governance_v2.routes import router as governance_v2_router, set_governance_system
from governance_v2.health import set_governance_system as set_health_governance
from hardened_mutations import router as hardened_router
from realtime_streaming import router as realtime_router
from observability import metrics_router, TracingMiddleware
from retry_controller import router as dlq_router
from lifecycle_manager import lifecycle_router
from spawn_routes import router as spawn_router, on_startup as spawn_on_startup
from channel_routes import router as channel_router
from diagnostic_routes import router as diagnostic_router, set_governance_system as set_diagnostic_governance
from agent_templates import seed_agent_templates
from channel_registry import get_channel_registry
from ledger_router import get_ledger_router
from design_providers import (
    router as design_router,
    initialize_design_service,
    create_design_service_with_all_providers
)

# Import governance system
from governance_v2 import LedgerGovernanceSystem

# Setup OpenTelemetry
tracer_provider, meter_provider, logger_provider = setup_telemetry(
    service_name="agent-world-backend",
    service_version="2.0.0",
    environment="production"
)

# Get structured logger
logger = get_logger("agent_world")

app = FastAPI(title="Agent World", version="2.0.0")

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Add tracing middleware for observability
app.add_middleware(TracingMiddleware)

# Add security middleware FIRST (before CORS)
app.add_middleware(SecurityMiddleware)

# Governance system instance (initialized on startup)
governance_system = None

# Dependency to get governance system
def get_governance_system():
    return governance_system

@app.on_event("startup")
async def startup_event():
    global governance_system

    # ── Ledger 2.0 Governance System ──────────────────────────────────
    governance_system = LedgerGovernanceSystem(ledger_sovereign=None)
    set_governance_system(governance_system)
    set_health_governance(governance_system)
    set_diagnostic_governance(governance_system)  # Wire diagnostics to Ledger
    await governance_system.start()
    print("✅ Ledger 2.0 Governance System initialized")

    # ── Design Providers ─────────────────────────────────────────────
    import os
    design_service = create_design_service_with_all_providers(
        openai_key=os.getenv("OPENAI_API_KEY"),
        nano_banana_key=os.getenv("NANO_BANANA_API_KEY"),
        sd_endpoint=os.getenv("STABLE_DIFFUSION_ENDPOINT"),
        canva_token=os.getenv("CANVA_ACCESS_TOKEN")
    )
    initialize_design_service(design_service)
    providers = design_service.registry.list_available()
    print(f"✅ Design Providers initialized: {len(providers)} providers")
    for p in providers:
        print(f"   • {p['display_name']} ({p['type']}) - ${p['cost_per_image']}/image")

    # ── Spawn executor + broadcast drain ──────────────────────────────
    await spawn_on_startup()
    print("✅ Spawn executor + broadcast drain started")

    # ── Background agent simulation ────────────────────────────────────
    asyncio.create_task(background_simulation())
    print("✅ Background simulation started")

    # ── Channel Registry ───────────────────────────────────────────────
    get_channel_registry()   # warm the singleton (loads channels_config.json)
    get_ledger_router()      # warm the Ledger Router
    print("✅ Channel Registry and Ledger Router ready")

    # ── Seed named agent templates ─────────────────────────────────────
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        import os
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentworld.db")
        engine  = create_engine(DATABASE_URL, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db      = Session()
        created = await seed_agent_templates(db)
        db.close()
        if created:
            print(f"✅ Seeded {created} named agent templates (Nova/Forge/Pixel/Cipher/Ultron)")
        else:
            print("✅ Named agent templates already seeded")
    except Exception as e:
        print(f"⚠️  Agent template seeding skipped: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Agent World")
    if governance_system:
        governance_system.stop()
        logger.info("Ledger 2.0 Governance System stopped")
    # Shutdown OpenTelemetry
    shutdown_telemetry()
    logger.info("Telemetry shutdown complete")

# Include additional routers
app.include_router(spawn_router)          # spawn / agent pipeline
app.include_router(channel_router)        # channels, routing, agent templates
app.include_router(diagnostic_router)     # business diagnostics & strategy
app.include_router(design_router)         # design providers (DALL-E, Nano Banana, etc.)
app.include_router(chatdev_router)
app.include_router(ledger_router)
app.include_router(governance_v2_router)
app.include_router(hardened_router, prefix="/api/v1", tags=["hardened-mutations"])
app.include_router(realtime_router)
app.include_router(metrics_router)
app.include_router(dlq_router)
app.include_router(lifecycle_router)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
class Agent(BaseModel):
    id: str
    name: str
    role: str
    status: str = "idle"  # idle, working, paused, error
    room_id: Optional[str] = None
    current_task: Optional[str] = None
    progress: int = 0
    logs: List[Dict] = []
    avatar_color: str = "#00f3ff"
    
    class Config:
        arbitrary_types_allowed = True

class Room(BaseModel):
    id: str
    name: str
    x: float
    y: float
    color: str = "#1a1c2c"
    agents: List[str] = []

class Task(BaseModel):
    id: str
    type: str
    description: str
    status: str = "pending"  # pending, active, completed, failed
    assigned_to: Optional[str] = None
    progress: int = 0
    created_at: datetime = datetime.now()

# In-memory storage (replace with PostgreSQL later)
agents: Dict[str, Agent] = {}
rooms: Dict[str, Room] = {}
tasks: Dict[str, Task] = {}
active_connections: List[WebSocket] = []

# Initialize with some data
def init_world():
    # Create rooms
    rooms["forge"] = Room(
        id="forge",
        name="The Forge",
        x=-5,
        y=0,
        color="#ff6b35",
        agents=[]
    )
    rooms["library"] = Room(
        id="library", 
        name="The Library",
        x=5,
        y=0,
        color="#4ecdc4",
        agents=[]
    )
    rooms["market"] = Room(
        id="market",
        name="The Market", 
        x=0,
        y=5,
        color="#ffe66d",
        agents=[]
    )
    
    # Create initial agents
    agent_colors = ["#00f3ff", "#ff006e", "#39ff14", "#ffb347", "#bf00ff"]
    
    for i in range(3):
        agent_id = f"agent_{i+1}"
        agents[agent_id] = Agent(
            id=agent_id,
            name=f"Agent {i+1}",
            role=["Researcher", "Designer", "Writer"][i],
            status="idle",
            room_id="forge",
            avatar_color=agent_colors[i]
        )
        rooms["forge"].agents.append(agent_id)

init_world()

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send initial world state
        await self.send_world_state(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass
    
    async def send_world_state(self, websocket: WebSocket):
        await websocket.send_json({
            "type": "world_init",
            "agents": [a.dict() for a in agents.values()],
            "rooms": [r.dict() for r in rooms.values()],
            "tasks": [t.dict() for t in tasks.values()]
        })

manager = ConnectionManager()

# Routes
@app.get("/")
async def root():
    return {"message": "Agent World API", "agents": len(agents), "rooms": len(rooms)}

@app.get("/api/agents")
async def get_agents():
    return list(agents.values())

@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    if agent_id not in agents:
        return {"error": "Agent not found"}
    return agents[agent_id]

@app.post("/api/agents/{agent_id}/move")
async def move_agent(agent_id: str, room_id: str):
    if agent_id not in agents or room_id not in rooms:
        return {"error": "Invalid agent or room"}
    
    agent = agents[agent_id]
    old_room = agent.room_id
    
    # Remove from old room
    if old_room and old_room in rooms:
        rooms[old_room].agents = [a for a in rooms[old_room].agents if a != agent_id]
    
    # Add to new room
    agent.room_id = room_id
    rooms[room_id].agents.append(agent_id)
    
    # Broadcast update
    await manager.broadcast({
        "type": "agent_moved",
        "agent_id": agent_id,
        "from_room": old_room,
        "to_room": room_id
    })
    
    return {"success": True}

@app.post("/api/agents/{agent_id}/task")
async def assign_task(agent_id: str, task_type: str, description: str):
    if agent_id not in agents:
        return {"error": "Agent not found"}
    
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        type=task_type,
        description=description,
        assigned_to=agent_id,
        status="active"
    )
    tasks[task_id] = task
    
    agent = agents[agent_id]
    agent.status = "working"
    agent.current_task = task_id
    agent.progress = 0
    
    # Start task simulation
    asyncio.create_task(simulate_task(agent_id, task_id))
    
    await manager.broadcast({
        "type": "task_assigned",
        "agent_id": agent_id,
        "task": task.dict()
    })
    
    return {"task_id": task_id}

@app.post("/api/agents/{agent_id}/pause")
async def pause_agent(agent_id: str):
    if agent_id not in agents:
        return {"error": "Agent not found"}
    
    agents[agent_id].status = "paused"
    await manager.broadcast({
        "type": "agent_paused",
        "agent_id": agent_id
    })
    return {"success": True}

# WebSocket endpoint
@app.websocket("/ws/world")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "move_agent":
                await move_agent(message["agent_id"], message["room_id"])
            elif message.get("action") == "assign_task":
                await assign_task(
                    message["agent_id"],
                    message["task_type"],
                    message["description"]
                )
            elif message.get("action") == "spawn_agent":
                await spawn_new_agent(message.get("name"), message.get("role"))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Simulate agent work
async def simulate_task(agent_id: str, task_id: str):
    agent = agents[agent_id]
    task = tasks[task_id]
    
    steps = [
        "Analyzing requirements...",
        "Gathering data...",
        "Processing information...",
        "Generating output...",
        "Finalizing..."
    ]
    
    for i, step in enumerate(steps):
        if agent.status == "paused":
            await asyncio.sleep(1)
            continue
            
        agent.progress = (i + 1) * 20
        agent.logs.append({
            "timestamp": datetime.now().isoformat(),
            "message": step,
            "task_id": task_id
        })
        
        await manager.broadcast({
            "type": "agent_progress",
            "agent_id": agent_id,
            "progress": agent.progress,
            "log": step
        })
        
        await asyncio.sleep(random.uniform(1, 3))
    
    task.status = "completed"
    agent.status = "idle"
    agent.current_task = None
    agent.progress = 0
    
    await manager.broadcast({
        "type": "task_completed",
        "agent_id": agent_id,
        "task_id": task_id
    })

async def spawn_new_agent(name: str, role: str):
    agent_id = f"agent_{len(agents) + 1}"
    colors = ["#00f3ff", "#ff006e", "#39ff14", "#ffb347", "#bf00ff"]
    
    agent = Agent(
        id=agent_id,
        name=name or f"Agent {len(agents) + 1}",
        role=role or "Assistant",
        status="idle",
        room_id="forge",
        avatar_color=colors[len(agents) % len(colors)]
    )
    agents[agent_id] = agent
    rooms["forge"].agents.append(agent_id)
    
    await manager.broadcast({
        "type": "agent_spawned",
        "agent": agent.dict()
    })

# Background simulation (agents do random things)
# NOTE: background_simulation() is now started in the single startup_event() above.

async def background_simulation():
    while True:
        await asyncio.sleep(10)
        
        # Random agent activity
        for agent in agents.values():
            if agent.status == "idle" and random.random() < 0.3:
                # Agent does something idle
                await manager.broadcast({
                    "type": "agent_activity",
                    "agent_id": agent.id,
                    "message": f"{agent.name} is observing the {rooms[agent.room_id].name}"
                })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
