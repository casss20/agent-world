"""
Audit Log Database Models
Immutable append-only audit trail with hash chaining
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import hashlib
import uuid

class ActorType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"

class ActionType(str, Enum):
    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_ISSUED = "auth.token_issued"
    AUTH_TOKEN_REFRESH = "auth.token_refresh"
    
    # Agent Management
    AGENT_REGISTER = "agent.register"
    AGENT_UPDATE = "agent.update"
    AGENT_DELETE = "agent.delete"
    AGENT_HEARTBEAT = "agent.heartbeat"
    
    # Governance
    GOVERNANCE_EXECUTE = "governance.execute"
    GOVERNANCE_CLASSIFY = "governance.classify"
    GOVERNANCE_TOKEN_ISSUE = "governance.token_issue"
    
    # Control
    KILLSWITCH_TRIGGER = "killswitch.trigger"
    KILLSWITCH_RESET = "killswitch.reset"
    DEGRADATION_CHANGE = "degradation.change"
    
    # Task
    TASK_SUBMIT = "task.submit"
    TASK_ASSIGN = "task.assign"
    TASK_COMPLETE = "task.complete"
    
    # Memory
    MEMORY_QUERY = "memory.query"
    MEMORY_CONSOLIDATE = "memory.consolidate"
    
    # Business
    BUSINESS_CREATE = "business.create"
    BUSINESS_UPDATE = "business.update"
    
    # Security
    AUTHZ_DENIED = "authz.denied"
    RATE_LIMIT_HIT = "rate_limit.hit"

class DecisionType(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    ERROR = "error"
    TIMEOUT = "timeout"

class ResultType(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"
    TIMEOUT = "timeout"

class AuditLogEntry(BaseModel):
    """Audit log entry model with integrity hashing"""
    id: Optional[int] = None
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Request correlation
    request_id: Optional[str] = Field(None, max_length=120)
    
    # Actor information
    actor_type: ActorType
    actor_id: str = Field(..., max_length=120)
    actor_role: Optional[str] = Field(None, max_length=80)
    
    # Action details
    action: ActionType
    resource_type: str = Field(..., max_length=80)
    resource_id: Optional[str] = Field(None, max_length=120)
    business_id: Optional[int] = None
    
    # HTTP context
    route: Optional[str] = Field(None, max_length=255)
    method: Optional[str] = Field(None, max_length=10)
    status_code: Optional[int] = None
    
    # Decision
    decision: DecisionType
    
    # Context
    ip_address: Optional[str] = Field(None, max_length=64)
    user_agent: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Integrity - hash chaining for tamper detection
    prev_hash: Optional[str] = Field(None, max_length=128)
    event_hash: Optional[str] = Field(None, max_length=128)
    
    def compute_hash(self, previous_hash: Optional[str] = None) -> str:
        """Compute SHA-256 hash of this event for integrity"""
        data = f"{self.event_id}:{self.created_at.isoformat()}:{self.actor_id}:{self.action}:{self.decision}:{previous_hash or ''}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_integrity(self, previous_hash: Optional[str] = None) -> bool:
        """Verify this event's hash matches computed value"""
        if not self.event_hash:
            return False
        computed = self.compute_hash(previous_hash)
        return computed == self.event_hash
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "actor_type": "user",
                "actor_id": "admin@agent-world.com",
                "actor_role": "admin",
                "action": "killswitch.trigger",
                "resource_type": "killswitch",
                "resource_id": "emergency_stop",
                "decision": "allowed",
                "ip_address": "192.168.1.100",
                "request_id": "req_abc123"
            }
        }

class AuditLogQuery(BaseModel):
    """Query parameters for audit log retrieval"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    actor_type: Optional[ActorType] = None
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    action: Optional[ActionType] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    business_id: Optional[int] = None
    decision: Optional[DecisionType] = None
    request_id: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)

class AuditLogStats(BaseModel):
    """Audit log statistics"""
    total_entries: int
    date_range: Dict[str, datetime]
    action_breakdown: Dict[str, int]
    decision_breakdown: Dict[str, int]
    actor_breakdown: Dict[str, int]
    hourly_activity: Dict[str, int]

class IntegrityStatus(BaseModel):
    """Audit log integrity verification status"""
    total_events: int
    verified_events: int
    failed_events: int
    chain_intact: bool
    first_event_id: Optional[str] = None
    last_event_id: Optional[str] = None
    last_hash: Optional[str] = None
    verification_time: datetime = Field(default_factory=datetime.utcnow)

# SQL Schema for PostgreSQL with security roles
CREATE_TABLE_SQL = """
-- Audit logs table - append only, immutable
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    request_id VARCHAR(120),
    
    -- Actor information
    actor_type VARCHAR(20) NOT NULL,
    actor_id VARCHAR(120) NOT NULL,
    actor_role VARCHAR(80),
    
    -- Action details
    action VARCHAR(120) NOT NULL,
    resource_type VARCHAR(80) NOT NULL,
    resource_id VARCHAR(120),
    business_id BIGINT,
    
    -- HTTP context
    route VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    
    -- Decision
    decision VARCHAR(40) NOT NULL,
    
    -- Context
    ip_address VARCHAR(64),
    user_agent TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Integrity - hash chaining
    prev_hash VARCHAR(128),
    event_hash VARCHAR(128) NOT NULL,
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_actor_type CHECK (actor_type IN ('user', 'agent', 'system')),
    CONSTRAINT valid_decision CHECK (decision IN ('allowed', 'denied', 'error', 'timeout'))
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_type, actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_business ON audit_logs(business_id);
CREATE INDEX IF NOT EXISTS idx_audit_request ON audit_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_decision ON audit_logs(decision);

-- Composite indexes for common filters
CREATE INDEX IF NOT EXISTS idx_audit_created_actor ON audit_logs(created_at, actor_type, actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_business_created ON audit_logs(business_id, created_at);

-- Create read-only and write-only roles for security
-- DO NOT run these if roles already exist
DO $$
BEGIN
    -- Role for application to insert audit logs
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'audit_writer') THEN
        CREATE ROLE audit_writer NOLOGIN;
        GRANT INSERT ON audit_logs TO audit_writer;
        GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO audit_writer;
    END IF;
    
    -- Role for readers (admin UI, analysts)
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'audit_reader') THEN
        CREATE ROLE audit_reader NOLOGIN;
        GRANT SELECT ON audit_logs TO audit_reader;
    END IF;
END
$$;

-- Materialized view for dashboard stats
CREATE MATERIALIZED VIEW IF NOT EXISTS audit_stats_daily AS
SELECT 
    DATE(created_at) as date,
    action,
    decision,
    COUNT(*) as count
FROM audit_logs
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), action, decision;

CREATE INDEX IF NOT EXISTS idx_audit_stats_date ON audit_stats_daily(date);

-- Function to refresh stats (call periodically)
CREATE OR REPLACE FUNCTION refresh_audit_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY audit_stats_daily;
END;
$$ LANGUAGE plpgsql;

-- Partitioning setup for high-volume (optional, enable if needed)
-- CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
--     FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Retention policy: automated export and cleanup of old logs
-- CREATE OR REPLACE FUNCTION archive_old_audit_logs()
-- RETURNS void AS $$
-- BEGIN
--     -- Export to cold storage before deletion
--     -- DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '90 days';
-- END;
-- $$ LANGUAGE plpgsql;
"""
