"""
Audit Log Service
Database operations for audit logging
"""

import os
import json
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextvars import ContextVar
from .audit_models import AuditLogEntry, AuditLogQuery, AuditLogStats, ActorType, ActionType, ResultType

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/agent_world"
)

# Request ID context for correlation
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

class AuditLogService:
    """Service for audit log operations"""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=20,
            command_timeout=10
        )
        await self._create_tables()
    
    async def close(self):
        """Close database pool"""
        if self.pool:
            await self.pool.close()
    
    async def _create_tables(self):
        """Create audit log tables if not exist"""
        from .audit_models import CREATE_TABLE_SQL
        async with self.pool.acquire() as conn:
            await conn.execute(CREATE_TABLE_SQL)
    
    async def log(self, entry: AuditLogEntry) -> str:
        """
        Write audit log entry to database with hash chaining
        
        Returns:
            event_id of the created entry
        """
        # Inject request ID from context if not provided
        if not entry.request_id:
            entry.request_id = request_id_context.get()
        
        # Get previous hash for chain integrity
        prev_hash = await self._get_last_hash()
        entry.prev_hash = prev_hash
        
        # Compute event hash
        entry.event_hash = entry.compute_hash(prev_hash)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO audit_logs (
                    event_id, request_id, actor_type, actor_id, actor_role,
                    action, resource_type, resource_id, business_id,
                    route, method, status_code, decision,
                    ip_address, user_agent, details, prev_hash, event_hash, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                RETURNING id
                """,
                entry.event_id,
                entry.request_id,
                entry.actor_type.value,
                entry.actor_id,
                entry.actor_role,
                entry.action.value,
                entry.resource_type,
                entry.resource_id,
                entry.business_id,
                entry.route,
                entry.method,
                entry.status_code,
                entry.decision.value,
                entry.ip_address,
                entry.user_agent,
                json.dumps(entry.details) if entry.details else '{}',
                entry.prev_hash,
                entry.event_hash,
                entry.created_at
            )
            return entry.event_id
    
    async def _get_last_hash(self) -> Optional[str]:
        """Get the hash of the most recent audit log entry"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT event_hash FROM audit_logs ORDER BY id DESC LIMIT 1"
            )
            return row['event_hash'] if row else None
    
    async def verify_integrity(self, limit: int = 10000) -> Dict[str, Any]:
        """
        Verify the integrity of the audit log chain
        
        Returns:
            Integrity status with verification results
        """
        from .audit_models import IntegrityStatus, DecisionType
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM audit_logs ORDER BY id ASC LIMIT $1",
                limit
            )
        
        if not rows:
            return IntegrityStatus(
                total_events=0,
                verified_events=0,
                failed_events=0,
                chain_intact=True
            ).dict()
        
        verified = 0
        failed = 0
        prev_hash = None
        
        for row in rows:
            entry = self._row_to_entry(row)
            
            # Skip hash verification for first entry (no prev_hash)
            if entry.prev_hash is None or prev_hash is None:
                verified += 1
            elif entry.prev_hash != prev_hash:
                failed += 1
            else:
                # Verify event hash
                computed = entry.compute_hash(prev_hash)
                if computed == entry.event_hash:
                    verified += 1
                else:
                    failed += 1
            
            prev_hash = entry.event_hash
        
        return IntegrityStatus(
            total_events=len(rows),
            verified_events=verified,
            failed_events=failed,
            chain_intact=failed == 0,
            first_event_id=rows[0]['event_id'],
            last_event_id=rows[-1]['event_id'],
            last_hash=prev_hash
        ).dict()
    
    async def query(self, query: AuditLogQuery) -> List[AuditLogEntry]:
        """Query audit logs with filters"""
        from .audit_models import DecisionType
        
        # Build dynamic query
        conditions = []
        params = []
        param_idx = 1
        
        if query.start_date:
            conditions.append(f"created_at >= ${param_idx}")
            params.append(query.start_date)
            param_idx += 1
        
        if query.end_date:
            conditions.append(f"created_at <= ${param_idx}")
            params.append(query.end_date)
            param_idx += 1
        
        if query.actor_type:
            conditions.append(f"actor_type = ${param_idx}")
            params.append(query.actor_type.value)
            param_idx += 1
        
        if query.actor_id:
            conditions.append(f"actor_id = ${param_idx}")
            params.append(query.actor_id)
            param_idx += 1
        
        if query.actor_role:
            conditions.append(f"actor_role = ${param_idx}")
            params.append(query.actor_role)
            param_idx += 1
        
        if query.action:
            conditions.append(f"action = ${param_idx}")
            params.append(query.action.value)
            param_idx += 1
        
        if query.resource_type:
            conditions.append(f"resource_type = ${param_idx}")
            params.append(query.resource_type)
            param_idx += 1
        
        if query.resource_id:
            conditions.append(f"resource_id = ${param_idx}")
            params.append(query.resource_id)
            param_idx += 1
        
        if query.business_id:
            conditions.append(f"business_id = ${param_idx}")
            params.append(query.business_id)
            param_idx += 1
        
        if query.decision:
            conditions.append(f"decision = ${param_idx}")
            params.append(query.decision.value)
            param_idx += 1
        
        if query.request_id:
            conditions.append(f"request_id = ${param_idx}")
            params.append(query.request_id)
            param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        sql = f"""
            SELECT * FROM audit_logs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([query.limit, query.offset])
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [self._row_to_entry(row) for row in rows]
    
    async def get_stats(self, days: int = 30) -> AuditLogStats:
        """Get audit log statistics"""
        from .audit_models import DecisionType
        
        async with self.pool.acquire() as conn:
            # Total entries
            total_row = await conn.fetchrow(
                "SELECT COUNT(*) as count FROM audit_logs WHERE created_at >= $1",
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Date range
            range_row = await conn.fetchrow(
                """
                SELECT MIN(created_at) as min_date, MAX(created_at) as max_date
                FROM audit_logs WHERE created_at >= $1
                """,
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Action breakdown
            action_rows = await conn.fetch(
                """
                SELECT action, COUNT(*) as count
                FROM audit_logs
                WHERE created_at >= $1
                GROUP BY action
                """,
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Decision breakdown
            decision_rows = await conn.fetch(
                """
                SELECT decision, COUNT(*) as count
                FROM audit_logs
                WHERE created_at >= $1
                GROUP BY decision
                """,
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Actor breakdown
            actor_rows = await conn.fetch(
                """
                SELECT actor_type, COUNT(*) as count
                FROM audit_logs
                WHERE created_at >= $1
                GROUP BY actor_type
                """,
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Hourly activity (last 24 hours)
            hourly_rows = await conn.fetch(
                """
                SELECT EXTRACT(HOUR FROM created_at) as hour, COUNT(*) as count
                FROM audit_logs
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY EXTRACT(HOUR FROM created_at)
                ORDER BY hour
                """
            )
            
            return AuditLogStats(
                total_entries=total_row['count'],
                date_range={
                    'start': range_row['min_date'] or datetime.utcnow(),
                    'end': range_row['max_date'] or datetime.utcnow()
                },
                action_breakdown={row['action']: row['count'] for row in action_rows},
                decision_breakdown={row['decision']: row['count'] for row in decision_rows},
                actor_breakdown={row['actor_type']: row['count'] for row in actor_rows},
                hourly_activity={f"{int(row['hour']):02d}:00": row['count'] for row in hourly_rows}
            )
    
    async def export_to_json(self, query: AuditLogQuery, filepath: str):
        """Export audit logs to JSON file"""
        entries = await self.query(query)
        
        with open(filepath, 'w') as f:
            json.dump([entry.dict() for entry in entries], f, indent=2, default=str)
    
    async def export_to_csv(self, query: AuditLogQuery, filepath: str):
        """Export audit logs to CSV file"""
        import csv
        
        entries = await self.query(query)
        
        with open(filepath, 'w', newline='') as f:
            if entries:
                writer = csv.DictWriter(f, fieldnames=entries[0].dict().keys())
                writer.writeheader()
                for entry in entries:
                    writer.writerow(entry.dict())
    
    def _row_to_entry(self, row: asyncpg.Record) -> AuditLogEntry:
        """Convert database row to AuditLogEntry"""
        from .audit_models import DecisionType
        return AuditLogEntry(
            id=row['id'],
            event_id=str(row['event_id']),
            created_at=row['created_at'],
            request_id=row['request_id'],
            actor_type=ActorType(row['actor_type']),
            actor_id=row['actor_id'],
            actor_role=row['actor_role'],
            action=ActionType(row['action']),
            resource_type=row['resource_type'],
            resource_id=row['resource_id'],
            business_id=row['business_id'],
            route=row['route'],
            method=row['method'],
            status_code=row['status_code'],
            decision=DecisionType(row['decision']),
            ip_address=row['ip_address'],
            user_agent=row['user_agent'],
            details=json.loads(row['details']) if row['details'] else {},
            prev_hash=row['prev_hash'],
            event_hash=row['event_hash']
        )

# Global service instance
_audit_service: Optional[AuditLogService] = None

async def get_audit_service() -> AuditLogService:
    """Get or create audit service singleton"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditLogService()
        await _audit_service.initialize()
    return _audit_service

def set_request_id(request_id: str):
    """Set request ID in context for correlation"""
    request_id_context.set(request_id)

def get_request_id() -> Optional[str]:
    """Get current request ID from context"""
    return request_id_context.get()
