from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text, Integer, Float, Boolean, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class Tenant(Base):
    __tablename__ = 'tenants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    plan = Column(String(50), default='free')
    config = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    projects = relationship("Project", back_populates="tenant", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="tenant", cascade="all, delete-orphan")

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
    rooms = relationship("Room", back_populates="project", cascade="all, delete-orphan")

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    project = relationship("Project", back_populates="rooms")
    room_agents = relationship("RoomAgent", back_populates="room", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="room", cascade="all, delete-orphan")

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    tenant = relationship("Tenant", back_populates="agents")
    room_agents = relationship("RoomAgent", back_populates="agent", cascade="all, delete-orphan")
    owned_tasks = relationship("Task", foreign_keys="Task.owner_agent_id", back_populates="owner")
    sent_messages = relationship("Message", foreign_keys="Message.from_agent_id", back_populates="from_agent")

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
    
    room = relationship("Room", back_populates="tasks")
    owner = relationship("Agent", foreign_keys=[owner_agent_id], back_populates="owned_tasks")
    activities = relationship("Activity", back_populates="task")

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
    
    room = relationship("Room", back_populates="messages")
    from_agent = relationship("Agent", foreign_keys=[from_agent_id], back_populates="sent_messages")

class Activity(Base):
    __tablename__ = 'activities'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'))
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id'))
    activity_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    room = relationship("Room", back_populates="activities")
    task = relationship("Task", back_populates="activities")

# Database setup helper
def init_db(database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
