"""
Agent World: SQLAlchemy Models
Database models for Living Agents system with tenant isolation
"""

from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Enum, 
    Integer, JSON, Boolean, Text, UniqueConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import expression

Base = declarative_base()

# ============================================================================
# ENUMS
# ============================================================================

class BusinessScope(str, PyEnum):
    BUSINESS = "business"
    SYSTEM = "system"
    GLOBAL = "global"

class AgentStatus(str, PyEnum):
    OFFLINE = "offline"
    STARTING = "starting"
    ONLINE = "online"
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class TaskStatus(str, PyEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RoomType(str, PyEnum):
    FORGE = "forge"
    RESEARCH = "research"
    MARKET = "market"
    SYSTEM = "system"

class MessageType(str, PyEnum):
    CHAT = "chat"
    TASK = "task"
    SYSTEM = "system"
    DIRECT = "direct"

class BlackboardOperation(str, PyEnum):
    SET = "set"
    DELETE = "delete"
    APPEND = "append"

# ============================================================================
# CORE TABLES
# ============================================================================

class Business(Base):
    """Tenant/organization entity"""
    __tablename__ = "businesses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    config = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    
    # Relationships
    agents = relationship("Agent", back_populates="business", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="business", cascade="all, delete-orphan")
    tasks = relationship("TaskQueue", back_populates="business", cascade="all, delete-orphan")

class Agent(Base):
    """Agent entity with lifecycle and capabilities"""
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True)
    scope = Column(Enum(BusinessScope), default=BusinessScope.BUSINESS)
    
    # Identity
    name = Column(String(255), nullable=False)
    agent_type = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Lifecycle
    status = Column(Enum(AgentStatus), default=AgentStatus.OFFLINE)
    desired_status = Column(Enum(AgentStatus), default=AgentStatus.ONLINE)
    version = Column(Integer, default=0)  # Optimistic locking
    
    # Capabilities & Load
    capabilities = Column(ARRAY(String), default=[])
    max_load = Column(Integer, default=5)
    current_load = Column(Integer, default=0)
    config = Column(JSONB, default={})
    
    # Heartbeat
    last_heartbeat = Column(DateTime, nullable=True)
    error_reason = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="agents")
    sessions = relationship("AgentSession", back_populates="agent", cascade="all, delete-orphan")
    room_memberships = relationship("AgentRoom", back_populates="agent", cascade="all, delete-orphan")
    memories = relationship("AgentMemory", back_populates="agent", cascade="all, delete-orphan")
    claimed_tasks = relationship("TaskQueue", back_populates="agent", foreign_keys="TaskQueue.agent_id")
    
    __table_args__ = (
        Index('ix_agent_business_status', 'business_id', 'status'),
        Index('ix_agent_type', 'agent_type'),
        Index('ix_agent_scope', 'scope'),
        UniqueConstraint('business_id', 'name', name='uq_agent_name_per_business'),
    )

class Room(Base):
    """Room/space where agents collaborate"""
    __tablename__ = "rooms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True)
    scope = Column(Enum(BusinessScope), default=BusinessScope.BUSINESS)
    
    # Configuration
    name = Column(String(255), nullable=False)
    room_type = Column(Enum(RoomType), nullable=False)
    description = Column(Text)
    
    # Capacity
    max_agents = Column(Integer, default=10)
    
    # Policy
    policy_config = Column(JSONB, default=lambda: {
        "join_rule": "governor_approved",
        "blackboard_write": "senior_only",
        "message_broadcast": True,
    })
    
    # Lifecycle
    is_active = Column(Boolean, default=True)
    archived_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="rooms")
    memberships = relationship("AgentRoom", back_populates="room", cascade="all, delete-orphan")
    blackboard_events = relationship("BlackboardEvent", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("RoomMessage", back_populates="room", cascade="all, delete-orphan")
    tasks = relationship("TaskQueue", back_populates="room", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_room_business_type', 'business_id', 'room_type'),
        Index('ix_room_active', 'is_active', 'archived_at'),
    )

# ============================================================================
# JUNCTION & STATE TABLES
# ============================================================================

class AgentRoom(Base):
    """Many-to-many relationship with membership metadata"""
    __tablename__ = "agent_rooms"
    
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), primary_key=True)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), primary_key=True)
    
    # Membership metadata
    role = Column(String(50), default="member")  # member, moderator, owner
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="room_memberships")
    room = relationship("Room", back_populates="memberships")
    
    __table_args__ = (
        Index('ix_agent_room_active', 'agent_id', 'is_active'),
        Index('ix_room_members', 'room_id', 'is_active'),
    )

class AgentSession(Base):
    """Tracks running agent processes with heartbeats"""
    __tablename__ = "agent_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    # Process info
    process_id = Column(String(100))
    host = Column(String(255))
    version = Column(String(50))
    
    # Heartbeat tracking
    started_at = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum("active", "stale", "dead"), default="active")
    
    # Relationships
    agent = relationship("Agent", back_populates="sessions")
    
    __table_args__ = (
        Index('ix_session_agent', 'agent_id', 'status'),
        Index('ix_session_heartbeat', 'last_heartbeat'),
    )

class BlackboardEvent(Base):
    """Event sourcing for room blackboard state"""
    __tablename__ = "blackboard_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    
    # Event data
    sequence_number = Column(Integer, nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(JSONB, nullable=True)
    operation = Column(Enum(BlackboardOperation), default=BlackboardOperation.SET)
    
    # Audit
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    room = relationship("Room", back_populates="blackboard_events")
    
    __table_args__ = (
        UniqueConstraint('room_id', 'sequence_number', name='uq_blackboard_sequence'),
        Index('ix_blackboard_room_key', 'room_id', 'key'),
        Index('ix_blackboard_timestamp', 'timestamp'),
    )

class RoomMessage(Base):
    """Messages within a room"""
    __tablename__ = "room_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    
    # Message content
    message_type = Column(Enum(MessageType), default=MessageType.CHAT)
    content = Column(Text, nullable=False)
    metadata = Column(JSONB, default={})
    
    # Ordering & delivery
    sequence_number = Column(Integer, nullable=False)
    delivered_to = Column(ARRAY(UUID), default=[])
    
    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # TTL
    
    # Relationships
    room = relationship("Room", back_populates="messages")
    
    __table_args__ = (
        Index('ix_message_room_seq', 'room_id', 'sequence_number'),
        Index('ix_message_expires', 'expires_at'),
        Index('ix_message_created', 'created_at'),
    )

class AgentMemory(Base):
    """Structured agent memory (not JSON blob)"""
    __tablename__ = "agent_memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    # Memory content
    memory_type = Column(Enum("short_term", "long_term", "episodic"), default="short_term")
    key = Column(String(255), nullable=False)
    value = Column(JSONB)
    importance = Column(Integer, default=0)  # For pruning
    
    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    accessed_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="memories")
    
    __table_args__ = (
        UniqueConstraint('agent_id', 'key', 'memory_type', name='uq_agent_memory_key'),
        Index('ix_memory_agent_type', 'agent_id', 'memory_type'),
        Index('ix_memory_expires', 'expires_at'),
        Index('ix_memory_importance', 'importance'),
    )

class TaskQueue(Base):
    """Distributed task queue with leasing"""
    __tablename__ = "task_queue"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    
    # Task definition
    task_type = Column(String(100), nullable=False)
    priority = Column(Integer, default=0)
    payload = Column(JSONB, default={})
    required_capability = Column(String(100), nullable=True)
    
    # State machine
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    
    # Claim/lease tracking
    claimed_at = Column(DateTime, nullable=True)
    lease_expires = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Results
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    room = relationship("Room", back_populates="tasks")
    business = relationship("Business", back_populates="tasks")
    agent = relationship("Agent", back_populates="claimed_tasks")
    
    __table_args__ = (
        Index('ix_task_status_priority', 'status', 'priority', 'created_at'),
        Index('ix_task_claimed', 'agent_id', 'lease_expires'),
        Index('ix_task_business', 'business_id', 'status'),
        Index('ix_task_room', 'room_id', 'status'),
    )

class RoomInvitation(Base):
    """Invitations for invite-only rooms"""
    __tablename__ = "room_invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    status = Column(Enum("pending", "accepted", "declined", "expired"), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_invitation_room', 'room_id', 'status'),
        Index('ix_invitation_agent', 'agent_id', 'status'),
    )

# ============================================================================
# AUDIT TABLES
# ============================================================================

class AuditLog(Base):
    """Immutable audit trail"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Actor
    actor_type = Column(String(20), nullable=False)  # user, agent, system
    actor_id = Column(String(120), nullable=False)
    actor_role = Column(String(50), nullable=True)
    
    # Action
    action = Column(String(120), nullable=False)
    resource_type = Column(String(80), nullable=False)
    resource_id = Column(String(120), nullable=False)
    
    # Decision
    decision = Column(String(40), nullable=True)  # allowed, denied, error
    
    # Request context
    request_id = Column(String(120), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    # HTTP context
    route = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    
    # Details
    details = Column(JSONB, default={})
    
    # Integrity
    prev_hash = Column(String(128), nullable=True)
    event_hash = Column(String(128), nullable=False)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_audit_actor', 'actor_type', 'actor_id', 'created_at'),
        Index('ix_audit_action', 'action', 'created_at'),
        Index('ix_audit_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_request', 'request_id'),
        Index('ix_audit_created', 'created_at'),
    )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_blackboard_state(db_session, room_id: uuid.UUID) -> Dict:
    """Build current blackboard state from event sourcing"""
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

def get_room_member_count(db_session, room_id: uuid.UUID) -> int:
    """Get current active member count for a room"""
    return db_session.query(AgentRoom).filter(
        AgentRoom.room_id == room_id,
        AgentRoom.is_active == True
    ).count()
