"""
Batched Audit Writer
Buffers audit events and flushes in batches to reduce DB pressure
"""

import asyncio
import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass


@dataclass
class AuditEvent:
    """Single audit event waiting to be written"""
    timestamp: str
    run_id: str
    room_id: str
    event_type: str
    severity: str
    message: str
    metadata: Dict[str, Any]


class BatchedAuditWriter:
    """
    Buffers audit events and writes them in batches
    
    Benefits:
    - Reduces SQLite write contention
    - Fewer disk I/O operations
    - Better throughput under load
    """
    
    def __init__(
        self,
        db_path: str = "/var/lib/agentverse/audit.db",
        batch_size: int = 100,
        flush_interval_ms: int = 100,
        max_buffer_size: int = 1000
    ):
        self.db_path = db_path
        self.batch_size = batch_size
        self.flush_interval = flush_interval_ms / 1000.0  # Convert to seconds
        self.max_buffer_size = max_buffer_size
        
        self._buffer: List[AuditEvent] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Ensure database table exists
        self._init_db()
    
    def _init_db(self):
        """Initialize audit database with batch-optimized schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    room_id TEXT,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes for batch operations
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_run_id 
                ON audit_events(run_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_room_id 
                ON audit_events(room_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
                ON audit_events(timestamp)
            """)
            
            conn.commit()
    
    async def start(self):
        """Start the background flush task"""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
    
    async def stop(self):
        """Stop and flush remaining events"""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush_buffer()
    
    async def write_event(
        self,
        run_id: str,
        room_id: str,
        event_type: str,
        severity: str = "INFO",
        message: str = "",
        metadata: Dict[str, Any] = None
    ):
        """Queue an audit event for batch writing"""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=run_id,
            room_id=room_id,
            event_type=event_type,
            severity=severity,
            message=message,
            metadata=metadata or {}
        )
        
        async with self._lock:
            self._buffer.append(event)
            
            # Trigger immediate flush if buffer is full
            if len(self._buffer) >= self.max_buffer_size:
                asyncio.create_task(self._flush_buffer())
    
    async def _flush_loop(self):
        """Background task that periodically flushes the buffer"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Audit flush error: {e}")
    
    async def _flush_buffer(self):
        """Write buffered events to database"""
        async with self._lock:
            if not self._buffer:
                return
            
            # Take current buffer contents
            events_to_write = self._buffer[:self.batch_size]
            self._buffer = self._buffer[self.batch_size:]
        
        # Write outside the lock to allow concurrent queueing
        try:
            await asyncio.to_thread(self._write_batch_sync, events_to_write)
        except Exception as e:
            print(f"Batch write failed: {e}")
            # Re-queue failed events (with limit to prevent unbounded growth)
            async with self._lock:
                if len(self._buffer) < self.max_buffer_size * 2:
                    self._buffer = events_to_write + self._buffer
    
    def _write_batch_sync(self, events: List[AuditEvent]):
        """Synchronous batch write to SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO audit_events 
                (timestamp, run_id, room_id, event_type, severity, message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.timestamp,
                        e.run_id,
                        e.room_id,
                        e.event_type,
                        e.severity,
                        e.message,
                        json.dumps(e.metadata)
                    )
                    for e in events
                ]
            )
            conn.commit()
    
    async def get_events(
        self,
        run_id: Optional[str] = None,
        room_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit events (waits for pending writes)"""
        await self._flush_buffer()  # Ensure all events are written
        
        return await asyncio.to_thread(
            self._query_sync, run_id, room_id, limit
        )
    
    def _query_sync(
        self,
        run_id: Optional[str],
        room_id: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Synchronous query"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []
            
            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)
            
            if room_id:
                query += " AND room_id = ?"
                params.append(room_id)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "run_id": row["run_id"],
                    "room_id": row["room_id"],
                    "event_type": row["event_type"],
                    "severity": row["severity"],
                    "message": row["message"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                }
                for row in rows
            ]
    
    @property
    def pending_count(self) -> int:
        """Number of events waiting to be written"""
        return len(self._buffer)


# Global instance for shared use
_audit_writer: Optional[BatchedAuditWriter] = None


async def get_batched_audit_writer() -> BatchedAuditWriter:
    """Get or create the global batched audit writer"""
    global _audit_writer
    
    if _audit_writer is None:
        _audit_writer = BatchedAuditWriter()
        await _audit_writer.start()
    
    return _audit_writer


async def close_batched_audit_writer():
    """Close the global audit writer"""
    global _audit_writer
    
    if _audit_writer:
        await _audit_writer.stop()
        _audit_writer = None
