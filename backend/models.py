"""
AgentVerse Models
Complete SQLAlchemy 2.0 declarative models for the AgentVerse platform.

Reconstructed from git history (commit 53e75bd) + later additions.
Supports both sync and async session patterns.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    create_engine, Column, String, DateTime, ForeignKey, Text,
    Integer, Float, Boolean, ARRAY, JSON, Index, Enum as SQLEnum,
)

from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

# ── Enums ───────────────────────────────────────────────────────────────────

class RoomType(PyEnum):
    general = "general"
    private = "private"
    project = "project"
    system = "system"
    # Aliases for auto_spawner.py compatibility
    RESEARCH = "project"
    MARKET = "project"
    FORGE = "project"
    STRATEGY = "project"
    DEVELOPMENT = "project"
    COLLABORATION = "general"
    MONITORING = "system"
    ARCHIVE = "system"

class AgentStatus(PyEnum):
    # Standard states used across the platform
    OFFLINE = "offline"
    STARTING = "starting"
    ONLINE = "online"
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"
    # Legacy lowercase aliases for backward compatibility
    idle = "idle"
    working = "busy"
    paused = "paused"
    error = "error"
    offline = "offline"

class BusinessScope(PyEnum):
    local = "local"
    regional = "regional"
    national = "national"
    global_ = "global"

class TaskStatus(PyEnum):
    pending = "pending"
    active = "active"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    handed_off = "handed_off"
    approved = "approved"
    rejected = "rejected"

class BlackboardOperation(PyEnum):
    SET = "set"
    DELETE = "delete"
    APPEND = "append"

# ── Tenant ──────────────────────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = 'tenants'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    plan = Column(String(50), default='free')
    status = Column(String(50), default='active')
    config = Column(JSON, default={})
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    projects = relationship("Project", back_populates="tenant", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="tenant", cascade="all, delete-orphan")

# ── User ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default='user')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ── Business ────────────────────────────────────────────────────────────────

class Business(Base):
    __tablename__ = 'businesses'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    scope = Column(String(50), default='local')
    status = Column(String(50), default='active')
    config = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assets = relationship("Asset", back_populates="business", cascade="all, delete-orphan")

# ── Asset ───────────────────────────────────────────────────────────────────

class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String(36), ForeignKey("businesses.id"), nullable=False)
    business = relationship("Business", back_populates="assets")

    filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    public_url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000), nullable=True)

    type = Column(String(50), nullable=False, default="content")
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    status = Column(String(20), default="pending_review")
    tags = Column(JSON, default=[])
    description = Column(Text, nullable=True)

    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    uploader = relationship("User", foreign_keys=[uploaded_by])
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approver = relationship("User", foreign_keys=[approved_by])
    approved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_asset_business', 'business_id', 'created_at'),
        Index('ix_asset_status', 'status', 'business_id'),
        Index('ix_asset_type', 'type', 'business_id'),
    )

# ── Project ─────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = 'projects'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), default='general')
    status = Column(String(50), default='active')
    config = Column(JSON, default={})
    extra_data = Column(JSON, default={})
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="projects")
    rooms = relationship("Room", back_populates="project", cascade="all, delete-orphan")

# ── Room ────────────────────────────────────────────────────────────────────

class Room(Base):
    __tablename__ = 'rooms'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    room_type = Column(String(50), default='general')
    shared_context = Column(JSON, default={})
    artifact_urls = Column(JSON, default=[])
    guidelines = Column(JSON, default={})
    status = Column(String(50), default='active')
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="rooms")
    room_agents = relationship("AgentRoom", back_populates="room", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="room", cascade="all, delete-orphan")

# ── Agent ───────────────────────────────────────────────────────────────────

class Agent(Base):
    __tablename__ = 'agents'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    agent_type = Column(String(50), default='assistant')
    avatar_url = Column(Text)
    color = Column(String(7), default='#00f3ff')
    model = Column(String(100), default='claude-3-sonnet')
    system_prompt = Column(Text, nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    tools = Column(JSON, default=[])
    capabilities = Column(JSON, default=[])
    allowed_rooms = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default='idle')
    total_tasks_completed = Column(Integer, default=0)
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="agents")
    room_agents = relationship("AgentRoom", back_populates="agent", cascade="all, delete-orphan")
    owned_tasks = relationship("Task", foreign_keys="Task.owner_agent_id", back_populates="owner")
    sent_messages = relationship("Message", foreign_keys="Message.from_agent_id", back_populates="from_agent")

# ── AgentRoom (RoomAgent alias for backward compatibility) ──────────────────

class AgentRoom(Base):
    __tablename__ = 'room_agents'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(36), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    agent_id = Column(String(36), ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(50), default='participant')
    status = Column(String(50), default='idle')
    is_active = Column(Boolean, default=True)
    current_task_id = Column(String(36))
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)
    position_z = Column(Float, default=0)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    entered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True))

    room = relationship("Room", back_populates="room_agents")
    agent = relationship("Agent", back_populates="room_agents")

# Backward compatibility alias
RoomAgent = AgentRoom

# ── Task ────────────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(36), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    owner_agent_id = Column(String(36), ForeignKey('agents.id'), nullable=False)
    contributor_agent_ids = Column(JSON, default=[])
    task_type = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    priority = Column(String(50), default='medium')
    status = Column(String(50), default='pending')
    estimated_impact = Column(Integer, default=0)
    input_payload = Column(JSON, default={})
    output_payload = Column(JSON, default={})
    parent_task_id = Column(String(36), ForeignKey('tasks.id'))
    depends_on = Column(JSON, default=[])
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    room = relationship("Room", back_populates="tasks")
    owner = relationship("Agent", foreign_keys=[owner_agent_id], back_populates="owned_tasks")
    activities = relationship("Activity", back_populates="task")

# ── Message ─────────────────────────────────────────────────────────────────

class Message(Base):
    __tablename__ = 'messages'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(36), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    from_agent_id = Column(String(36), ForeignKey('agents.id'), nullable=False)
    to_agent_id = Column(String(36), ForeignKey('agents.id'))
    message_type = Column(String(50), default='chat')
    content = Column(Text, nullable=False)
    extra_data = Column(JSON, default={})
    reply_to_id = Column(String(36), ForeignKey('messages.id'))
    thread_root_id = Column(String(36), ForeignKey('messages.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room", back_populates="messages")
    from_agent = relationship("Agent", foreign_keys=[from_agent_id], back_populates="sent_messages")

# ── Activity ────────────────────────────────────────────────────────────────

class Activity(Base):
    __tablename__ = 'activities'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(36), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    agent_id = Column(String(36), ForeignKey('agents.id'))
    task_id = Column(String(36), ForeignKey('tasks.id'))
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    details = Column(JSON, default={})
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room", back_populates="activities")
    task = relationship("Task", back_populates="activities")

# ── Audit ───────────────────────────────────────────────────────────────────

class Audit(Base):
    __tablename__ = 'audit'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_type = Column(String(50), nullable=False)
    actor_id = Column(String(36), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(36), nullable=False)
    request_id = Column(String(120), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    route = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    details = Column(JSON, default={})
    prev_hash = Column(String(128), nullable=True)
    event_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_audit_actor', 'actor_type', 'actor_id', 'created_at'),
        Index('ix_audit_action', 'action', 'created_at'),
        Index('ix_audit_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_request', 'request_id'),
        Index('ix_audit_created', 'created_at'),
    )

# ── BlackboardEvent ───────────────────────────────────────────────────────

class BlackboardEvent(Base):
    __tablename__ = 'blackboard_events'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(36), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    agent_id = Column(String(36), ForeignKey('agents.id'), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(JSON, default={})
    operation = Column(SQLEnum(BlackboardOperation), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_bb_room_seq', 'room_id', 'sequence_number'),
        Index('ix_bb_agent', 'agent_id', 'created_at'),
    )

# ── TaskQueue (for async job processing) ────────────────────────────────────

class TaskQueue(Base):
    __tablename__ = 'task_queue'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(String(100), nullable=False)
    payload = Column(JSON, default={})
    status = Column(String(50), default='pending')
    priority = Column(Integer, default=5)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ── Sync Database Helpers ─────────────────────────────────────────────────

def init_db(database_url: str = None):
    """Initialize database tables (sync)."""
    import os
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./agentworld.db")
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


# get_db for backward compatibility (some routes import it from models)
# Note: New code should use database.get_db() for async sessions
def get_db():
    """Get a sync database session (for backward compatibility)."""
    import os
    url = os.getenv("DATABASE_URL", "sqlite:///./agentworld.db")
    engine = create_engine(url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


# ── Helper Functions ────────────────────────────────────────────────────────

def get_current_blackboard_state(db_session, room_id) -> dict:
    """Build current blackboard state from event sourcing."""
    events = db_session.query(BlackboardEvent).filter(
        BlackboardEvent.room_id == room_id
    ).order_by(BlackboardEvent.sequence_number.asc()).all()

    state = {}
    for event in events:
        if event.operation == BlackboardOperation.SET:
            state[event.key] = event.value
        elif event.operation == BlackboardOperation.DELETE:
            state.pop(event.key, None)
        elif event.operation == BlackboardOperation.APPEND:
            if event.key not in state:
                state[event.key] = []
            if isinstance(state[event.key], list):
                state[event.key].append(event.value)

    return state


def get_room_member_count(db_session, room_id) -> int:
    """Get current active member count for a room."""
    return db_session.query(AgentRoom).filter(
        AgentRoom.room_id == room_id,
        AgentRoom.is_active == True
    ).count()


# ── Compatibility aliases ─────────────────────────────────────────────────

# Compatibility aliases for legacy code
ActivityLog = Activity
RoomMessage = Message
RoomInvitation = AgentRoom
AuditLog = Activity  # file_routes.py compatibility

# AgentSession stub
class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    room_id = Column(String(36), ForeignKey("rooms.id"), nullable=True)
    status = Column(String(20), default="active")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    extra_data = Column(JSON, default=dict)

    agent = relationship("Agent", backref="sessions")


class SwarmExecution(Base):
    __tablename__ = 'swarm_executions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    swarm_id = Column(String(50), unique=True, nullable=False)
    task_id = Column(String(36), ForeignKey('tasks.id'))
    framework = Column(String(50), default='native')
    agents_spawned = Column(Integer, default=0)
    agents_completed = Column(Integer, default=0)
    status = Column(String(50), default='pending')
    decomposition = Column(JSON, default=[])
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)


class AgentConversation(Base):
    __tablename__ = 'agent_conversations'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(50), nullable=False)
    user_id = Column(String(36), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    task_assigned = Column(String(50), nullable=True)
    task_status = Column(String(50), default='pending')
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PluginRegistryEntry(Base):
    __tablename__ = 'plugin_registry'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    provider_type = Column(String(100), nullable=False)
    version = Column(String(50), default='1.0.0')
    status = Column(String(50), default='active')
    config = Column(JSON, default={})
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MCPServerConnection(Base):
    __tablename__ = 'mcp_server_connections'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    transport = Column(String(50), default='stdio')
    endpoint = Column(String(500), nullable=True)
    config = Column(JSON, default={})
    status = Column(String(50), default='inactive')
    last_connected_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
