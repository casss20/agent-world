"""
Extended Models for Workflow Integration
Adds Workflow and WorkflowRun entities to AgentVerse
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, Boolean, ARRAY, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
import uuid
import enum

Base = declarative_base()

class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    OFFLINE = "offline"

# ============== EXISTING MODELS (from models.py) ==============

class Tenant(Base):
    __tablename__ = 'tenants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    plan = Column(String(50), default='free')
    config = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    projects = relationship("Project", back_populates="tenant")
    agents = relationship("Agent", back_populates="tenant")
    workflows = relationship("Workflow", back_populates="tenant")

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), default='general')
    status = Column(String(50), default='active')
    config = Column(JSONB, default={})
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    tenant = relationship("Tenant", back_populates="projects")
    rooms = relationship("Room", back_populates="project")

class Room(Base):
    __tablename__ = 'rooms'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    room_type = Column(String(50), default='general')
    shared_context = Column(JSONB, default={})
    artifact_urls = Column(ARRAY(Text), default=[])
    guidelines = Column(JSONB, default={})
    status = Column(String(50), default='active')
    is_private = Column(Boolean, default=False)
    
    # WORKFLOW INTEGRATION FIELDS
    engine_type = Column(String(50), default='chatdev-money')  # 'chatdev-money' | 'native'
    default_workflow_id = Column(String(100))
    active_run_id = Column(UUID(as_uuid=True), ForeignKey('workflow_runs.id'), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    project = relationship("Project", back_populates="rooms")
    room_agents = relationship("RoomAgent", back_populates="room")
    workflow_runs = relationship("WorkflowRun", back_populates="room")

class Agent(Base):
    __tablename__ = 'agents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    avatar_url = Column(Text)
    color = Column(String(7), default='#00f3ff')
    model = Column(String(100), default='claude-3-sonnet')
    system_prompt = Column(Text, nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    tools = Column(ARRAY(String), default=[])
    allowed_rooms = Column(ARRAY(String), default=[])
    is_active = Column(Boolean, default=True)
    total_tasks_completed = Column(Integer, default=0)
    
    # WORKFLOW INTEGRATION
    workflow_role = Column(String(50))  # 'scout' | 'maker' | 'merchant' | null
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    tenant = relationship("Tenant", back_populates="agents")
    room_agents = relationship("RoomAgent", back_populates="agent")

class RoomAgent(Base):
    __tablename__ = 'room_agents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    status = Column(String(50), default='idle')
    current_task_id = Column(UUID(as_uuid=True))
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)
    position_z = Column(Float, default=0)
    entered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True))
    
    room = relationship("Room", back_populates="room_agents")
    agent = relationship("Agent", back_populates="room_agents")

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    owner_agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False)
    contributor_agent_ids = Column(ARRAY(UUID(as_uuid=True)), default=[])
    type = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    priority = Column(Integer, default=3)
    status = Column(String(50), default='pending')
    input_payload = Column(JSONB, default={})
    output_payload = Column(JSONB, default={})
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id'))
    depends_on = Column(ARRAY(UUID(as_uuid=True)), default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    room = relationship("Room")

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    from_agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False)
    to_agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'))
    message_type = Column(String(50), default='chat')
    content = Column(Text, nullable=False)
    metadata = Column(JSONB, default={})
    reply_to = Column(UUID(as_uuid=True), ForeignKey('messages.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    room = relationship("Room")

# ============== NEW WORKFLOW MODELS ==============

class Workflow(Base):
    """
    Registered workflow templates that can be launched in rooms.
    In Phase 1, most workflows will be 'chatdev-money' engine type.
    """
    __tablename__ = 'workflows'
    
    id = Column(String(100), primary_key=True)  # e.g., 'content_arbitrage_v1'
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    workflow_type = Column(String(50), nullable=False)  # 'content_arbitrage' | 'research' | etc.
    engine = Column(String(50), default='chatdev-money')  # 'chatdev-money' | 'native'
    
    # For ChatDev workflows: path to YAML file
    yaml_file = Column(String(255))
    
    # For native workflows: JSON config
    config = Column(JSONB, default={})
    
    # Expected inputs schema
    input_schema = Column(JSONB, default={})
    
    # Default values
    default_inputs = Column(JSONB, default={})
    
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    tenant = relationship("Tenant", back_populates="workflows")
    runs = relationship("WorkflowRun", back_populates="workflow")

class WorkflowRun(Base):
    """
    Instance of a workflow execution in a room.
    Canonical record that maps to ChatDev's internal run via legacy_run_id.
    """
    __tablename__ = 'workflow_runs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Hierarchy
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    workflow_id = Column(String(100), ForeignKey('workflows.id'), nullable=False)
    
    # Who started it
    initiated_by_user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Status
    status = Column(String(20), default=WorkflowStatus.PENDING.value)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Inputs/Outputs
    inputs = Column(JSONB, default={})
    outputs = Column(JSONB, default={})
    
    # Error info
    error_message = Column(Text)
    error_details = Column(JSONB, default={})
    
    # ChatDev bridge (legacy integration)
    legacy_run_id = Column(String(100))
    legacy_engine = Column(String(50), default='chatdev-money')
    
    # Progress tracking
    progress_percent = Column(Integer, default=0)
    current_step = Column(String(100))
    
    # Revenue tracking (ported from ChatDev)
    estimated_revenue = Column(Float, default=0.0)
    actual_revenue = Column(Float, default=0.0)
    revenue_currency = Column(String(3), default='USD')
    platform = Column(String(50))  # 'ghost', 'etsy', 'gumroad', etc.
    published_url = Column(Text)
    
    # Metrics
    processing_time_seconds = Column(Float)
    token_usage = Column(JSONB, default={})  # {prompt_tokens: N, completion_tokens: M}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    room = relationship("Room", back_populates="workflow_runs")
    workflow = relationship("Workflow", back_populates="runs")

class WorkflowEvent(Base):
    """
    Immutable event log for workflow runs.
    Used for audit trail and replay.
    """
    __tablename__ = 'workflow_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    room_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    workflow_run_id = Column(UUID(as_uuid=True), ForeignKey('workflow_runs.id', ondelete='CASCADE'), nullable=False)
    
    event_name = Column(String(100), nullable=False)  # 'workflow.run.started', 'agent.step.completed', etc.
    event_id = Column(String(50), unique=True, nullable=False)
    
    # Actor
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'))
    agent_role = Column(String(50))  # 'scout', 'maker', 'merchant'
    
    # Payload
    payload = Column(JSONB, default={})
    
    # Causality
    correlation_id = Column(String(50))
    causation_id = Column(String(50))  # Previous event that caused this
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        # Index for querying run history
        {'postgresql_using': 'btree'},
    )

class LegacyRunMapping(Base):
    """
    Bridge table for ChatDev migration.
    Maps canonical UUID to ChatDev's string IDs.
    """
    __tablename__ = 'legacy_run_mappings'
    
    canonical_run_id = Column(UUID(as_uuid=True), ForeignKey('workflow_runs.id'), primary_key=True)
    legacy_run_id = Column(String(100), unique=True, nullable=False, index=True)
    engine = Column(String(50), default='chatdev-money')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RevenueEntry(Base):
    """
    Ported from ChatDev Money.
    Tracks actual and estimated revenue per content piece.
    """
    __tablename__ = 'revenue_entries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    workflow_run_id = Column(UUID(as_uuid=True), ForeignKey('workflow_runs.id'))
    
    # Tracking
    tracking_id = Column(String(100), unique=True, index=True)
    content_title = Column(String(500))
    platform = Column(String(50), nullable=False)
    revenue_model = Column(String(50))  # 'affiliate', 'ad_sense', 'product_sale', etc.
    
    # Revenue
    estimated_revenue = Column(Float, default=0.0)
    actual_revenue = Column(Float, default=0.0)
    revenue_currency = Column(String(3), default='USD')
    
    # Performance metrics
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    views = Column(Integer, default=0)
    engagement_score = Column(Float)
    
    # Links
    source_url = Column(Text)  # Original Reddit post
    published_url = Column(Text)  # Where content was published
    
    # Status
    status = Column(String(50), default='projected')  # 'projected' | 'confirmed' | 'paid'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ============== DATABASE SETUP ==============

def init_workflow_db(database_url: str):
    """Initialize all tables including workflow extensions"""
    from sqlalchemy import create_engine
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
