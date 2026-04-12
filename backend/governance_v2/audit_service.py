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
    
    async def log(self, entry: AuditLogEntry) -> int:
        """
        Write audit log entry to database
        
        Returns:
            ID of the created entry
        """
        # Inject request ID from context if not provided
        if not entry.request_id:
            entry.request_id = request_id_context.get()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO audit_logs (
                    timestamp, actor_type, actor_id, actor_role,
                    action, action_description, resource_type, resource_id,
                    business_id, result, result_details, request_id,
                    session_id, ip_address, user_agent, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING id
                """,
                entry.timestamp,
                entry.actor_type.value,
                entry.actor_id,
                entry.actor_role,
                entry.action.value,
                entry.action_description,
                entry.resource_type,
                entry.resource_id,
                entry.business_id,
                entry.result.value,
                json.dumps(entry.result_details) if entry.result_details else None,
                entry.request_id,
                entry.session_id,
                entry.ip_address,
                entry.user_agent,
                json.dumps(entry.metadata) if entry.metadata else None
            )
            return row['id']
    
    async def query(self, query: AuditLogQuery) -> List[AuditLogEntry]:
        """Query audit logs with filters"""
        
        # Build dynamic query
        conditions = []
        params = []
        param_idx = 1
        
        if query.start_date:
            conditions.append(f"timestamp >= ${param_idx}")
            params.append(query.start_date)
            param_idx += 1
        
        if query.end_date:
            conditions.append(f"timestamp <= ${param_idx}")
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
        
        if query.result:
            conditions.append(f"result = ${param_idx}")
            params.append(query.result.value)
            param_idx += 1
        
        if query.request_id:
            conditions.append(f"request_id = ${param_idx}")
            params.append(query.request_id)
            param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        sql = f"""
            SELECT * FROM audit_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([query.limit, query.offset])
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [self._row_to_entry(row) for row in rows]
    
    async def get_stats(self, days: int = 30) -> AuditLogStats:
        """Get audit log statistics"""
        
        async with self.pool.acquire() as conn:
            # Total entries
            total_row = await conn.fetchrow(
                "SELECT COUNT(*) as count FROM audit_logs WHERE timestamp >= $1",
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Date range
            range_row = await conn.fetchrow(
                """
                SELECT MIN(timestamp) as min_date, MAX(timestamp) as max_date
                FROM audit_logs WHERE timestamp >= $1
                """,
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Action breakdown
            action_rows = await conn.fetch(
                """
                SELECT action, COUNT(*) as count
                FROM audit_logs
                WHERE timestamp >= $1
                GROUP BY action
                """,
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Result breakdown
            result_rows = await conn.fetch(
                """
                SELECT result, COUNT(*) as count
                FROM audit_logs
                WHERE timestamp >= $1
                GROUP BY result
                """,
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Actor breakdown
            actor_rows = await conn.fetch(
                """
                SELECT actor_type, COUNT(*) as count
                FROM audit_logs
                WHERE timestamp >= $1
                GROUP BY actor_type
                """,
                datetime.utcnow() - timedelta(days=days)
            )
            
            # Hourly activity (last 24 hours)
            hourly_rows = await conn.fetch(
                """
                SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count
                FROM audit_logs
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY EXTRACT(HOUR FROM timestamp)
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
                result_breakdown={row['result']: row['count'] for row in result_rows},
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
        return AuditLogEntry(
            id=row['id'],
            timestamp=row['timestamp'],
            actor_type=ActorType(row['actor_type']),
            actor_id=row['actor_id'],
            actor_role=row['actor_role'],
            action=ActionType(row['action']),
            action_description=row['action_description'],
            resource_type=row['resource_type'],
            resource_id=row['resource_id'],
            business_id=row['business_id'],
            result=ResultType(row['result']),
            result_details=json.loads(row['result_details']) if row['result_details'] else None,
            request_id=row['request_id'],
            session_id=row['session_id'],
            ip_address=str(row['ip_address']) if row['ip_address'] else None,
            user_agent=row['user_agent'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
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
