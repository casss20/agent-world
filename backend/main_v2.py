from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import os
from datetime import datetime
from uuid import UUID, uuid4
from contextlib import asynccontextmanager

# Database
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from models import Base, init_db, Tenant, Project, Room, Agent, RoomAgent, Task, Message
from services import RoomService, MessageService, TaskService

# Load environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/agentworld")

# Setup database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables on startup
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models for API
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "general"

class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    room_type: str = "general"
    guidelines: Optional[Dict] = None

class AgentCreate(BaseModel):
    name: str
    role: str
    system_prompt: str
    model: str = "claude-3-sonnet"
    color: Optional[str] = "#00f3ff"
    tools: List[str] = []

class TaskCreate(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    priority: int = 3
    input_payload: Optional[Dict] = None

class MessageCreate(BaseModel):
    content: str
    to_agent_id: Optional[str] = None
    message_type: str = "chat"
    metadata: Optional[Dict] = None

class ContextUpdate(BaseModel):
    updates: Dict[str, Any]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
    
    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    
    async def broadcast_to_room(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.active_connections[room_id].remove(conn)

manager = ConnectionManager()

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure default tenant exists
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            tenant = Tenant(name="Default Tenant", slug="default", plan="pro")
            db.add(tenant)
            db.commit()
            
            # Create sample project
            project = Project(
                tenant_id=tenant.id,
                name="Marketing Campaign Q4",
                description="Holiday marketing initiative",
                type="marketing"
            )
            db.add(project)
            db.commit()
            
            # Create sample room
            room = Room(
                project_id=project.id,
                name="Strategy Room",
                description="High-level planning and research",
                room_type="strategy",
                shared_context={
                    "brief": "Launch holiday campaign targeting 25-34 demographic",
                    "budget": 50000,
                    "timeline": "6 weeks",
                    "trending_keywords": ["holiday gifts", "cozy vibes"]
                }
            )
            db.add(room)
            
            # Create sample agents
            agents_data = [
                ("Researcher Alpha", "researcher", "#00f3ff"),
                ("Designer Beta", "designer", "#ff006e"),
                ("Writer Gamma", "writer", "#39ff14")
            ]
            
            for name, role, color in agents_data:
                agent = Agent(
                    tenant_id=tenant.id,
                    name=name,
                    role=role,
                    color=color,
                    system_prompt=f"You are a {role} specialist. Help the team achieve their goals.",
                    model="claude-3-sonnet",
                    tools=["web_search"] if role == "researcher" else ["image_gen"] if role == "designer" else []
                )
                db.add(agent)
                db.commit()
                
                # Add to room
                room_agent = RoomAgent(
                    room_id=room.id,
                    agent_id=agent.id,
                    status="idle",
                    position_x=__import__('random').uniform(-3, 3),
                    position_y=0,
                    position_z=__import__('random').uniform(-3, 3)
                )
                db.add(room_agent)
            
            db.commit()
    finally:
        db.close()
    
    yield
    # Shutdown

app = FastAPI(
    title="AgentVerse API",
    description="Multi-agent collaboration platform",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ PROJECT ENDPOINTS ============

@app.get("/api/v1/projects")
def list_projects(db: Session = Depends(get_db)):
    """List all projects for default tenant"""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if not tenant:
        return []
    
    projects = db.query(Project).filter(
        Project.tenant_id == tenant.id,
        Project.status == "active"
    ).all()
    
    return [{
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "type": p.type,
        "created_at": p.created_at.isoformat()
    } for p in projects]

@app.post("/api/v1/projects")
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    new_project = Project(
        tenant_id=tenant.id,
        name=project.name,
        description=project.description,
        type=project.type
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return {
        "id": str(new_project.id),
        "name": new_project.name,
        "description": new_project.description,
        "type": new_project.type
    }

# ============ ROOM ENDPOINTS ============

@app.get("/api/v1/projects/{project_id}/rooms")
def list_project_rooms(project_id: str, db: Session = Depends(get_db)):
    """List all rooms in a project"""
    room_service = RoomService(db)
    rooms = room_service.get_project_rooms(UUID(project_id))
    
    return [{
        "id": str(r.id),
        "name": r.name,
        "description": r.description,
        "room_type": r.room_type,
        "agent_count": len(r.room_agents)
    } for r in rooms]

@app.post("/api/v1/projects/{project_id}/rooms")
def create_room(project_id: str, room: RoomCreate, db: Session = Depends(get_db)):
    """Create a new room in a project"""
    room_service = RoomService(db)
    new_room = room_service.create_room(
        project_id=UUID(project_id),
        name=room.name,
        description=room.description,
        room_type=room.room_type,
        guidelines=room.guidelines
    )
    
    return {
        "id": str(new_room.id),
        "name": new_room.name,
        "description": new_room.description,
        "room_type": new_room.room_type
    }

@app.get("/api/v1/rooms/{room_id}")
def get_room(room_id: str, db: Session = Depends(get_db)):
    """Get room details with state"""
    room_service = RoomService(db)
    state = room_service.get_room_state(UUID(room_id))
    
    if not state:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return state

@app.put("/api/v1/rooms/{room_id}/context")
def update_room_context(room_id: str, update: ContextUpdate,
                       agent_id: Optional[str] = None,
                       db: Session = Depends(get_db)):
    """Update shared room context"""
    room_service = RoomService(db)
    
    new_context = room_service.update_context(
        room_id=UUID(room_id),
        agent_id=UUID(agent_id) if agent_id else None,
        updates=update.updates
    )
    
    if not new_context:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Broadcast update to all connected clients
    asyncio.create_task(manager.broadcast_to_room(room_id, {
        "type": "context_updated",
        "updates": update.updates,
        "full_context": new_context
    }))
    
    return {"context": new_context}

# ============ AGENT ENDPOINTS ============

@app.get("/api/v1/agents")
def list_agents(db: Session = Depends(get_db)):
    """List all agents for default tenant"""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if not tenant:
        return []
    
    agents = db.query(Agent).filter(
        Agent.tenant_id == tenant.id,
        Agent.is_active == True
    ).all()
    
    return [{
        "id": str(a.id),
        "name": a.name,
        "role": a.role,
        "color": a.color,
        "model": a.model,
        "tools": a.tools,
        "total_tasks_completed": a.total_tasks_completed
    } for a in agents]

@app.post("/api/v1/agents")
def create_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    """Create a new agent"""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    new_agent = Agent(
        tenant_id=tenant.id,
        name=agent.name,
        role=agent.role,
        system_prompt=agent.system_prompt,
        model=agent.model,
        color=agent.color or "#00f3ff",
        tools=agent.tools
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    return {
        "id": str(new_agent.id),
        "name": new_agent.name,
        "role": new_agent.role,
        "color": new_agent.color
    }

@app.post("/api/v1/rooms/{room_id}/agents/{agent_id}/join")
def agent_join_room(room_id: str, agent_id: str,
                   x: float = 0, y: float = 0, z: float = 0,
                   db: Session = Depends(get_db)):
    """Agent enters a room"""
    room_service = RoomService(db)
    room_agent = room_service.agent_enter_room(
        room_id=UUID(room_id),
        agent_id=UUID(agent_id),
        position=(x, y, z)
    )
    
    # Broadcast to room
    asyncio.create_task(manager.broadcast_to_room(room_id, {
        "type": "agent_joined",
        "agent_id": agent_id,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    return {"status": "joined", "room_agent_id": str(room_agent.id)}

@app.post("/api/v1/rooms/{room_id}/agents/{agent_id}/leave")
def agent_leave_room(room_id: str, agent_id: str, db: Session = Depends(get_db)):
    """Agent leaves a room"""
    room_service = RoomService(db)
    room_service.agent_leave_room(
        room_id=UUID(room_id),
        agent_id=UUID(agent_id)
    )
    
    # Broadcast to room
    asyncio.create_task(manager.broadcast_to_room(room_id, {
        "type": "agent_left",
        "agent_id": agent_id,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    return {"status": "left"}

# ============ TASK ENDPOINTS ============

@app.post("/api/v1/rooms/{room_id}/tasks")
def create_task(room_id: str, task: TaskCreate,
               owner_agent_id: str,
               db: Session = Depends(get_db)):
    """Create a new task in a room"""
    task_service = TaskService(db)
    new_task = task_service.create_task(
        room_id=UUID(room_id),
        owner_agent_id=UUID(owner_agent_id),
        task_type=task.type,
        title=task.title,
        description=task.description,
        priority=task.priority,
        input_payload=task.input_payload
    )
    
    # Broadcast
    asyncio.create_task(manager.broadcast_to_room(room_id, {
        "type": "task_created",
        "task": {
            "id": str(new_task.id),
            "title": new_task.title,
            "type": new_task.type,
            "owner_agent_id": owner_agent_id,
            "status": new_task.status
        }
    }))
    
    return {
        "id": str(new_task.id),
        "title": new_task.title,
        "status": new_task.status
    }

@app.get("/api/v1/rooms/{room_id}/tasks")
def list_room_tasks(room_id: str, status: Optional[str] = None,
                   db: Session = Depends(get_db)):
    """List tasks in a room"""
    query = db.query(Task).filter(Task.room_id == UUID(room_id))
    
    if status:
        query = query.filter(Task.status == status)
    
    tasks = query.order_by(Task.created_at.desc()).all()
    
    return [{
        "id": str(t.id),
        "title": t.title,
        "type": t.type,
        "status": t.status,
        "priority": t.priority,
        "owner_agent_id": str(t.owner_agent_id),
        "created_at": t.created_at.isoformat()
    } for t in tasks]

# ============ MESSAGE ENDPOINTS ============

@app.post("/api/v1/rooms/{room_id}/messages")
def send_message(room_id: str, message: MessageCreate,
                from_agent_id: str,
                db: Session = Depends(get_db)):
    """Send a message (broadcast or DM)"""
    msg_service = MessageService(db)
    
    new_msg = msg_service.send_message(
        room_id=UUID(room_id),
        from_agent_id=UUID(from_agent_id),
        to_agent_id=UUID(message.to_agent_id) if message.to_agent_id else None,
        content=message.content,
        message_type=message.message_type,
        metadata=message.metadata
    )
    
    # Broadcast
    asyncio.create_task(manager.broadcast_to_room(room_id, {
        "type": "new_message",
        "message": {
            "id": str(new_msg.id),
            "from_agent_id": from_agent_id,
            "to_agent_id": message.to_agent_id,
            "content": message.content,
            "message_type": message.message_type,
            "created_at": new_msg.created_at.isoformat()
        }
    }))
    
    return {"id": str(new_msg.id), "status": "sent"}

@app.get("/api/v1/rooms/{room_id}/messages")
def get_room_messages(room_id: str, limit: int = 50,
                     db: Session = Depends(get_db)):
    """Get recent messages in room"""
    msg_service = MessageService(db)
    messages = msg_service.get_room_messages(UUID(room_id), limit)
    
    return [{
        "id": str(m.id),
        "from_agent_id": str(m.from_agent_id),
        "to_agent_id": str(m.to_agent_id) if m.to_agent_id else None,
        "content": m.content,
        "message_type": m.message_type,
        "created_at": m.created_at.isoformat()
    } for m in messages]

# ============ WEBSOCKET ============

@app.websocket("/ws/rooms/{room_id}")
async def room_websocket(websocket: WebSocket, room_id: str,
                        db: Session = Depends(get_db)):
    """Real-time WebSocket connection for a room"""
    await manager.connect(room_id, websocket)
    
    # Send initial room state
    room_service = RoomService(db)
    state = room_service.get_room_state(UUID(room_id))
    
    await websocket.send_json({
        "type": "room_state",
        "data": state
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "heartbeat":
                # Update agent heartbeat
                agent_id = data.get("agent_id")
                if agent_id:
                    room_service.update_agent_status(
                        room_id=UUID(room_id),
                        agent_id=UUID(agent_id),
                        status=data.get("status", "idle"),
                        current_task_id=UUID(data["task_id"]) if data.get("task_id") else None
                    )
            
            elif action == "send_message":
                # Handle message from client
                msg_service = MessageService(db)
                msg = msg_service.send_message(
                    room_id=UUID(room_id),
                    from_agent_id=UUID(data["from_agent_id"]),
                    to_agent_id=UUID(data["to_agent_id"]) if data.get("to_agent_id") else None,
                    content=data["content"],
                    message_type=data.get("message_type", "chat")
                )
                
                await manager.broadcast_to_room(room_id, {
                    "type": "new_message",
                    "message": {
                        "id": str(msg.id),
                        "from_agent_id": data["from_agent_id"],
                        "to_agent_id": data.get("to_agent_id"),
                        "content": data["content"],
                        "message_type": data.get("message_type", "chat"),
                        "created_at": msg.created_at.isoformat()
                    }
                })
    
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
