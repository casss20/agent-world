"""
Audit Trail Persistence
Immutable log of all workflow runs and events for compliance and debugging
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import threading
from contextlib import contextmanager

from logging_guardrails import audit_logger, get_correlation_id


class AuditEventType(Enum):
    """Types of audit events"""
    WORKFLOW_LAUNCHED = "workflow.launched"
    WORKFLOW_STEP_STARTED = "workflow.step.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step.completed"
    WORKFLOW_STEP_FAILED = "workflow.step.failed"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_CANCELLED = "workflow.cancelled"
    WORKFLOW_FAILED = "workflow.failed"
    AGENT_INVOKED = "agent.invoked"
    AGENT_COMPLETED = "agent.completed"
    TOOL_CALLED = "tool.called"
    TOOL_COMPLETED = "tool.completed"
    REVENUE_RECORDED = "revenue.recorded"


@dataclass
class AuditEvent:
    """Immutable audit event record"""
    event_id: str
    event_type: str
    timestamp: str
    correlation_id: str
    run_id: str
    room_id: str
    user_id: str
    agent_id: Optional[str]
    step_name: Optional[str]
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        event_type: AuditEventType,
        run_id: str,
        room_id: str,
        user_id: str,
        agent_id: Optional[str] = None,
        step_name: Optional[str] = None,
        payload: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> "AuditEvent":
        """Factory method to create a new audit event"""
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=get_correlation_id(),
            run_id=run_id,
            room_id=room_id,
            user_id=user_id,
            agent_id=agent_id,
            step_name=step_name,
            payload=payload or {},
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "run_id": self.run_id,
            "room_id": self.room_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "step_name": self.step_name,
            "payload": self.payload,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


@dataclass
class WorkflowRunRecord:
    """Summary record of a workflow run"""
    run_id: str
    correlation_id: str
    room_id: str
    user_id: str
    workflow_id: str
    engine_type: str
    status: str  # running, completed, failed, cancelled
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    revenue: Optional[float] = None
    platform: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditTrailStore:
    """
    Persistent store for audit events and run records
    
    Uses SQLite for local durability. Can be swapped for PostgreSQL
    or event store in production.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "/var/lib/agentverse/audit.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._db_path = db_path
        return cls._instance
    
    def __init__(self, db_path: str = "/var/lib/agentverse/audit.db"):
        if self._initialized:
            return
        
        self._db_path = db_path
        self._init_database()
        self._initialized = True
        
        audit_logger.info("audit_store_initialized", 
                         "Audit trail store initialized",
                         {"db_path": db_path})
    
    def _init_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    correlation_id TEXT NOT NULL,
                    room_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    engine_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_ms INTEGER,
                    revenue REAL,
                    platform TEXT,
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_room ON workflow_runs(room_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_user ON workflow_runs(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_status ON workflow_runs(status)
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    room_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    agent_id TEXT,
                    step_name TEXT,
                    payload TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_run ON audit_events(run_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type ON audit_events(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_time ON audit_events(timestamp)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup"""
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def record_run_start(self, run: WorkflowRunRecord):
        """Record the start of a workflow run"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO workflow_runs 
                (run_id, correlation_id, room_id, user_id, workflow_id, engine_type,
                 status, created_at, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id, run.correlation_id, run.room_id, run.user_id,
                run.workflow_id, run.engine_type, run.status, run.created_at,
                run.started_at
            ))
            conn.commit()
        
        audit_logger.info("run_recorded",
                         f"Run {run.run_id} recorded",
                         {"run_id": run.run_id, "status": run.status})
    
    def record_run_completion(
        self,
        run_id: str,
        status: str,
        completed_at: str,
        duration_ms: int,
        revenue: Optional[float] = None,
        platform: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Record the completion of a workflow run"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE workflow_runs
                SET status = ?, completed_at = ?, duration_ms = ?,
                    revenue = ?, platform = ?, error_message = ?
                WHERE run_id = ?
            """, (status, completed_at, duration_ms, revenue, platform,
                  error_message, run_id))
            conn.commit()
        
        audit_logger.info("run_completed",
                         f"Run {run_id} completed with status {status}",
                         {"run_id": run_id, "status": status, 
                          "revenue": revenue, "duration_ms": duration_ms})
    
    def record_event(self, event: AuditEvent):
        """Record an audit event"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO audit_events
                (event_id, event_type, timestamp, correlation_id, run_id, room_id,
                 user_id, agent_id, step_name, payload, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.event_type, event.timestamp,
                event.correlation_id, event.run_id, event.room_id,
                event.user_id, event.agent_id, event.step_name,
                json.dumps(event.payload), json.dumps(event.metadata)
            ))
            conn.commit()
        
        # Also log to structured logger
        audit_logger.info("audit_event",
                         f"Event {event.event_type} for run {event.run_id}",
                         {"event_type": event.event_type, "run_id": event.run_id,
                          "step_name": event.step_name, "agent_id": event.agent_id})
    
    def get_run(self, run_id: str) -> Optional[WorkflowRunRecord]:
        """Get a workflow run by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            
            if row:
                return WorkflowRunRecord(
                    run_id=row[0],
                    correlation_id=row[1],
                    room_id=row[2],
                    user_id=row[3],
                    workflow_id=row[4],
                    engine_type=row[5],
                    status=row[6],
                    created_at=row[7],
                    started_at=row[8],
                    completed_at=row[9],
                    duration_ms=row[10],
                    revenue=row[11],
                    platform=row[12],
                    error_message=row[13]
                )
            return None
    
    def get_run_events(self, run_id: str) -> List[AuditEvent]:
        """Get all events for a workflow run"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT event_id, event_type, timestamp, correlation_id, run_id,
                          room_id, user_id, agent_id, step_name, payload, metadata
                   FROM audit_events WHERE run_id = ? ORDER BY timestamp""",
                (run_id,)
            ).fetchall()
            
            return [
                AuditEvent(
                    event_id=row[0],
                    event_type=row[1],
                    timestamp=row[2],
                    correlation_id=row[3],
                    run_id=row[4],
                    room_id=row[5],
                    user_id=row[6],
                    agent_id=row[7],
                    step_name=row[8],
                    payload=json.loads(row[9]),
                    metadata=json.loads(row[10])
                )
                for row in rows
            ]
    
    def get_room_runs(
        self,
        room_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[WorkflowRunRecord]:
        """Get workflow runs for a room"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM workflow_runs 
                   WHERE room_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (room_id, limit, offset)
            ).fetchall()
            
            return [
                WorkflowRunRecord(
                    run_id=row[0],
                    correlation_id=row[1],
                    room_id=row[2],
                    user_id=row[3],
                    workflow_id=row[4],
                    engine_type=row[5],
                    status=row[6],
                    created_at=row[7],
                    started_at=row[8],
                    completed_at=row[9],
                    duration_ms=row[10],
                    revenue=row[11],
                    platform=row[12],
                    error_message=row[13]
                )
                for row in rows
            ]
    
    def export_run_audit(self, run_id: str) -> Dict[str, Any]:
        """Export complete audit trail for a run"""
        run = self.get_run(run_id)
        if not run:
            return None
        
        events = self.get_run_events(run_id)
        
        return {
            "run": run.to_dict(),
            "events": [e.to_dict() for e in events],
            "event_count": len(events),
            "export_timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
_audit_store: Optional[AuditTrailStore] = None


def get_audit_store() -> AuditTrailStore:
    """Get singleton audit store instance"""
    global _audit_store
    if _audit_store is None:
        _audit_store = AuditTrailStore()
    return _audit_store


class AuditContext:
    """
    Context manager for recording audit events during workflow execution
    
    Usage:
        with AuditContext(run_id, room_id, user_id) as audit:
            audit.record_launch(inputs)
            audit.record_step_started("Scout")
            # ... do work ...
            audit.record_step_completed("Scout", outputs)
    """
    
    def __init__(
        self,
        run_id: str,
        room_id: str,
        user_id: str,
        workflow_id: str = "content_arbitrage_v1"
    ):
        self.run_id = run_id
        self.room_id = room_id
        self.user_id = user_id
        self.workflow_id = workflow_id
        self.store = get_audit_store()
        self.started_at: Optional[datetime] = None
    
    def __enter__(self):
        self.started_at = datetime.now(timezone.utc)
        
        # Record run start
        run = WorkflowRunRecord(
            run_id=self.run_id,
            correlation_id=get_correlation_id(),
            room_id=self.room_id,
            user_id=self.user_id,
            workflow_id=self.workflow_id,
            engine_type="hybrid",
            status="running",
            created_at=self.started_at.isoformat(),
            started_at=self.started_at.isoformat()
        )
        self.store.record_run_start(run)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - self.started_at).total_seconds() * 1000)
        
        if exc_type:
            # Record failure
            self.store.record_run_completion(
                run_id=self.run_id,
                status="failed",
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms,
                error_message=str(exc_val)
            )
        # else: completion recorded explicitly by record_completion()
    
    def record_launch(self, inputs: Dict[str, Any]):
        """Record workflow launch event"""
        event = AuditEvent.create(
            event_type=AuditEventType.WORKFLOW_LAUNCHED,
            run_id=self.run_id,
            room_id=self.room_id,
            user_id=self.user_id,
            payload={"inputs": inputs, "workflow_id": self.workflow_id}
        )
        self.store.record_event(event)
    
    def record_step_started(self, step_name: str, agent_id: str):
        """Record step start event"""
        event = AuditEvent.create(
            event_type=AuditEventType.WORKFLOW_STEP_STARTED,
            run_id=self.run_id,
            room_id=self.room_id,
            user_id=self.user_id,
            agent_id=agent_id,
            step_name=step_name,
            payload={"step_name": step_name}
        )
        self.store.record_event(event)
    
    def record_step_completed(
        self,
        step_name: str,
        agent_id: str,
        outputs: Dict[str, Any]
    ):
        """Record step completion event"""
        event = AuditEvent.create(
            event_type=AuditEventType.WORKFLOW_STEP_COMPLETED,
            run_id=self.run_id,
            room_id=self.room_id,
            user_id=self.user_id,
            agent_id=agent_id,
            step_name=step_name,
            payload={"step_name": step_name, "outputs": outputs}
        )
        self.store.record_event(event)
    
    def record_completion(
        self,
        status: str,
        outputs: Dict[str, Any],
        revenue: Optional[float] = None,
        platform: Optional[str] = None
    ):
        """Record workflow completion"""
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - self.started_at).total_seconds() * 1000)
        
        # Record completion event
        event = AuditEvent.create(
            event_type=AuditEventType.WORKFLOW_COMPLETED,
            run_id=self.run_id,
            room_id=self.room_id,
            user_id=self.user_id,
            payload={"outputs": outputs, "revenue": revenue, "platform": platform}
        )
        self.store.record_event(event)
        
        # Update run record
        self.store.record_run_completion(
            run_id=self.run_id,
            status=status,
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms,
            revenue=revenue,
            platform=platform
        )
    
    def record_cancellation(self, reason: str):
        """Record workflow cancellation"""
        event = AuditEvent.create(
            event_type=AuditEventType.WORKFLOW_CANCELLED,
            run_id=self.run_id,
            room_id=self.room_id,
            user_id=self.user_id,
            payload={"reason": reason}
        )
        self.store.record_event(event)
