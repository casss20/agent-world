"""
Audit Log Database Models
PostgreSQL schema for immutable audit trail
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ActorType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"

class ActionType(str, Enum):
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    
    # Agent Management
    AGENT_REGISTER = "agent_register"
    AGENT_UPDATE = "agent_update"
    AGENT_DELETE = "agent_delete"
    AGENT_HEARTBEAT = "agent_heartbeat"
    
    # Governance
    GOVERNANCE_EXECUTE = "governance_execute"
    GOVERNANCE_CLASSIFY = "governance_classify"
    TOKEN_ISSUE = "token_issue"
    
    # Control
    KILLSWITCH_TRIGGER = "killswitch_trigger"
    KILLSWITCH_RESET = "killswitch_reset"
    DEGRADATION_SET = "degradation_set"
    
    # Memory
    MEMORY_QUERY = "memory_query"
    MEMORY_CONSOLIDATE = "memory_consolidate"
    
    # Business
    BUSINESS_CREATE = "business_create"
    BUSINESS_UPDATE = "business_update"

class ResultType(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"
    TIMEOUT = "timeout"

class AuditLogEntry(BaseModel):
    """Audit log entry model"""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Actor information
    actor_type: ActorType
    actor_id: str = Field(..., max_length=120)
    actor_role: Optional[str] = Field(None, max_length=40)
    
    # Action details
    action: ActionType
    action_description: Optional[str] = None
    
    # Resource information
    resource_type: str = Field(..., max_length=80)
    resource_id: str = Field(..., max_length=120)
    business_id: Optional[int] = None
    
    # Result
    result: ResultType
    result_details: Optional[Dict[str, Any]] = None
    
    # Context
    request_id: Optional[str] = Field(None, max_length=120)
    session_id: Optional[str] = Field(None, max_length=120)
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=255)
    
    # Metadata (flexible JSON for additional fields)
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "actor_type": "user",
                "actor_id": "admin@agent-world.com",
                "actor_role": "admin",
                "action": "killswitch_trigger",
                "resource_type": "killswitch",
                "resource_id": "emergency_stop",
                "result": "success",
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
    action: Optional[ActionType] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    business_id: Optional[int] = None
    result: Optional[ResultType] = None
    request_id: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)

class AuditLogStats(BaseModel):
    """Audit log statistics"""
    total_entries: int
    date_range: Dict[str, datetime]
    action_breakdown: Dict[str, int]
    result_breakdown: Dict[str, int]
    actor_breakdown: Dict[str, int]
    hourly_activity: Dict[str, int]

# SQL Schema for PostgreSQL
CREATE_TABLE_SQL = """
-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Actor information
    actor_type VARCHAR(20) NOT NULL,
    actor_id VARCHAR(120) NOT NULL,
    actor_role VARCHAR(40),
    
    -- Action details
    action VARCHAR(40) NOT NULL,
    action_description TEXT,
    
    -- Resource information
    resource_type VARCHAR(80) NOT NULL,
    resource_id VARCHAR(120) NOT NULL,
    business_id INTEGER,
    
    -- Result
    result VARCHAR(20) NOT NULL,
    result_details JSONB,
    
    -- Context
    request_id VARCHAR(120),
    session_id VARCHAR(120),
    ip_address INET,
    user_agent VARCHAR(255),
    
    -- Metadata
    metadata JSONB,
    
    -- Constraints
    CONSTRAINT valid_actor_type CHECK (actor_type IN ('user', 'agent', 'system')),
    CONSTRAINT valid_result CHECK (result IN ('success', 'failure', 'denied', 'error', 'timeout'))
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_type, actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_business ON audit_logs(business_id);
CREATE INDEX IF NOT EXISTS idx_audit_request ON audit_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_result ON audit_logs(result);

-- Composite indexes for common filters
CREATE INDEX IF NOT EXISTS idx_audit_timestamp_actor ON audit_logs(timestamp, actor_type, actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_business_timestamp ON audit_logs(business_id, timestamp);

-- Partitioning by month (for high-volume systems)
-- CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
--     FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Retention policy: automated cleanup of old logs
-- CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
-- RETURNS void AS $$
-- BEGIN
--     DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '90 days';
-- END;
-- $$ LANGUAGE plpgsql;

-- Materialized view for dashboard stats
CREATE MATERIALIZED VIEW IF NOT EXISTS audit_stats_daily AS
SELECT 
    DATE(timestamp) as date,
    action,
    result,
    COUNT(*) as count
FROM audit_logs
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), action, result;

CREATE INDEX IF NOT EXISTS idx_audit_stats_date ON audit_stats_daily(date);
"""
