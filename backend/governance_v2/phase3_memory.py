# Phase 3: Memory & Audit Implementation
## Memory Consolidator + Event Streaming + Trace Propagation

import os
import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from enum import Enum


class EventType(Enum):
    DECISION = "decision"
    ACTION = "action"
    APPROVAL = "approval"
    DENIAL = "denial"
    TOKEN_ISSUED = "token_issued"
    TOKEN_REVOKED = "token_revoked"
    AGENT_REGISTERED = "agent_registered"
    TASK_COMPLETED = "task_completed"
    ANOMALY_DETECTED = "anomaly_detected"
    OPPORTUNITY_FOUND = "opportunity_found"


@dataclass
class GovernanceEvent:
    """
    Immutable governance event with full traceability.
    """
    event_id: str
    trace_id: str  # Request chain ID for distributed tracing
    timestamp: datetime
    event_type: EventType
    agent_id: str
    business_id: int
    action: str
    resource: str
    risk_level: str
    decision: str  # approved, denied, escalated
    reasoning: str
    constitution_rules: List[str]  # Which rules were applied
    latency_ms: int
    metadata: Dict = field(default_factory=dict)
    parent_event_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        return data
    
    @classmethod
    def generate_id(cls) -> str:
        """Generate unique event ID."""
        return hashlib.sha256(
            f"{datetime.utcnow().timestamp()}{os.urandom(16)}".encode()
        ).hexdigest()[:32]


class EventStream:
    """
    Event streaming infrastructure for governance observability.
    Supports multiple consumers and persistent storage.
    """
    
    def __init__(self, storage_path: str = "./events"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.consumers: List[Callable] = []
        self.event_buffer: List[GovernanceEvent] = []
        self.buffer_size = 100
        self.flush_interval = 5  # seconds
        self.running = False
        
    async def start(self):
        """Start the event stream processor."""
        self.running = True
        while self.running:
            await self._flush_buffer()
            await asyncio.sleep(self.flush_interval)
    
    def stop(self):
        """Stop the event stream."""
        self.running = False
    
    async def emit(self, event: GovernanceEvent):
        """
        Emit an event to the stream.
        
        Flow:
        1. Add to buffer
        2. Notify consumers
        3. Persist to storage
        """
        self.event_buffer.append(event)
        
        # Notify consumers immediately
        for consumer in self.consumers:
            try:
                await consumer(event)
            except Exception as e:
                print(f"Event consumer failed: {e}")
        
        # Flush if buffer is full
        if len(self.event_buffer) >= self.buffer_size:
            await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Flush buffered events to persistent storage."""
        if not self.event_buffer:
            return
        
        events = self.event_buffer[:]
        self.event_buffer = []
        
        # Organize by date
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        daily_file = self.storage_path / f"events_{date_str}.jsonl"
        
        # Append to daily file
        with open(daily_file, "a") as f:
            for event in events:
                f.write(json.dumps(event.to_dict()) + "\n")
    
    def subscribe(self, consumer: Callable):
        """Subscribe to events."""
        self.consumers.append(consumer)
    
    def query(
        self,
        business_id: Optional[int] = None,
        agent_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[GovernanceEvent]:
        """
        Query events with filters.
        """
        results = []
        
        # Read from daily files
        for event_file in sorted(self.storage_path.glob("events_*.jsonl")):
            with open(event_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        
                        # Apply filters
                        if business_id and data.get("business_id") != business_id:
                            continue
                        if agent_id and data.get("agent_id") != agent_id:
                            continue
                        if event_type and data.get("event_type") != event_type.value:
                            continue
                        
                        event_time = datetime.fromisoformat(data["timestamp"])
                        if start_time and event_time < start_time:
                            continue
                        if end_time and event_time > end_time:
                            continue
                        
                        # Convert back to GovernanceEvent
                        data['timestamp'] = event_time
                        data['event_type'] = EventType(data['event_type'])
                        event = GovernanceEvent(**data)
                        results.append(event)
                        
                        if len(results) >= limit:
                            return results
                            
                    except Exception as e:
                        continue
        
        return results


@dataclass
class ConsolidationResult:
    """Result of memory consolidation process."""
    decisions_processed: int
    patterns_extracted: List[str]
    lessons_learned: List[str]
    strategic_insights: List[str]
    memory_updated: bool
    timestamp: datetime


class MemoryConsolidator:
    """
    Daily consolidation of governance events into strategic memory.
    
    Trigger conditions (AND):
    - 24h since last consolidation
    - 5+ decisions since last run
    - Advisory lock acquired
    """
    
    def __init__(
        self,
        event_stream: EventStream,
        memory_path: str = "./memory",
        lock_path: str = "./.consolidation_lock"
    ):
        self.event_stream = event_stream
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(exist_ok=True)
        self.lock_path = Path(lock_path)
        self.state_file = self.memory_path / "consolidation_state.json"
        
        # Gate configuration
        self.min_hours = 24
        self.min_decisions = 5
        self.lock_timeout_hours = 1
        
    def _get_state(self) -> Dict:
        """Get current consolidation state."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {
            "last_consolidated_at": None,
            "decisions_since_consolidation": 0,
            "total_consolidations": 0
        }
    
    def _save_state(self, state: Dict):
        """Save consolidation state."""
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)
    
    def _acquire_lock(self) -> bool:
        """
        Acquire advisory lock for consolidation.
        Uses file mtime as last_consolidated_at pattern.
        """
        try:
            if self.lock_path.exists():
                # Check if lock is stale
                mtime = datetime.fromtimestamp(self.lock_path.stat().st_mtime)
                if datetime.utcnow() - mtime < timedelta(hours=self.lock_timeout_hours):
                    return False  # Lock is held and not stale
            
            # Create lock file with PID
            with open(self.lock_path, "w") as f:
                f.write(str(os.getpid()))
            
            return True
            
        except Exception as e:
            print(f"Lock acquisition failed: {e}")
            return False
    
    def _release_lock(self, rollback: bool = False):
        """
        Release consolidation lock.
        If rollback, restore previous mtime.
        """
        try:
            if rollback and self.lock_path.exists():
                # Get state to restore mtime
                state = self._get_state()
                last_consolidated = state.get("last_consolidated_at")
                
                if last_consolidated:
                    # Restore mtime to previous value
                    timestamp = datetime.fromisoformat(last_consolidated).timestamp()
                    os.utime(self.lock_path, (timestamp, timestamp))
                else:
                    self.lock_path.unlink()
            elif self.lock_path.exists():
                self.lock_path.unlink()
                
        except Exception as e:
            print(f"Lock release failed: {e}")
    
    async def should_consolidate(self) -> bool:
        """
        Check if consolidation should run.
        Triple gate: time + volume + lock
        """
        state = self._get_state()
        
        # Gate 1: Time check (cheapest)
        last_consolidated = state.get("last_consolidated_at")
        if last_consolidated:
            last_time = datetime.fromisoformat(last_consolidated)
            if datetime.utcnow() - last_time < timedelta(hours=self.min_hours):
                return False
        
        # Gate 2: Volume check
        if state.get("decisions_since_consolidation", 0) < self.min_decisions:
            return False
        
        # Gate 3: Lock acquisition (most expensive)
        if not self._acquire_lock():
            return False
        
        return True
    
    async def consolidate(self) -> Optional[ConsolidationResult]:
        """
        Run memory consolidation.
        
        Process:
        1. Query recent decisions
        2. Extract patterns
        3. Update strategic memory
        4. Prune ephemeral details
        5. Log consolidation event
        """
        try:
            state = self._get_state()
            last_consolidated = state.get("last_consolidated_at")
            
            start_time = datetime.fromisoformat(last_consolidated) if last_consolidated else (
                datetime.utcnow() - timedelta(days=7)
            )
            
            # Query decisions since last consolidation
            events = self.event_stream.query(
                event_type=EventType.DECISION,
                start_time=start_time,
                limit=1000
            )
            
            if len(events) < self.min_decisions:
                self._release_lock(rollback=True)
                return None
            
            # Extract patterns
            patterns = self._extract_patterns(events)
            lessons = self._extract_lessons(events)
            insights = self._generate_insights(events)
            
            # Update memory files
            await self._update_memory(patterns, lessons, insights)
            
            # Update state
            state["last_consolidated_at"] = datetime.utcnow().isoformat()
            state["decisions_since_consolidation"] = 0
            state["total_consolidations"] = state.get("total_consolidations", 0) + 1
            self._save_state(state)
            
            # Release lock
            self._release_lock()
            
            return ConsolidationResult(
                decisions_processed=len(events),
                patterns_extracted=patterns,
                lessons_learned=lessons,
                strategic_insights=insights,
                memory_updated=True,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            print(f"Consolidation failed: {e}")
            self._release_lock(rollback=True)
            return None
    
    def _extract_patterns(self, events: List[GovernanceEvent]) -> List[str]:
        """Extract recurring patterns from events."""
        patterns = []
        
        # Pattern 1: Most common blocked actions
        blocked = [e for e in events if e.decision == "denied"]
        if len(blocked) > len(events) * 0.2:
            patterns.append("High denial rate - review constitution rules")
        
        # Pattern 2: Peak activity times
        hours = {}
        for e in events:
            hour = e.timestamp.hour
            hours[hour] = hours.get(hour, 0) + 1
        peak_hour = max(hours.items(), key=lambda x: x[1])[0]
        patterns.append(f"Peak activity at {peak_hour}:00 UTC")
        
        # Pattern 3: Business with most activity
        business_counts = {}
        for e in events:
            business_counts[e.business_id] = business_counts.get(e.business_id, 0) + 1
        top_business = max(business_counts.items(), key=lambda x: x[1])[0]
        patterns.append(f"Business {top_business} has highest governance activity")
        
        return patterns
    
    def _extract_lessons(self, events: List[GovernanceEvent]) -> List[str]:
        """Extract lessons learned from events."""
        lessons = []
        
        # Find escalated decisions
        escalated = [e for e in events if e.decision == "escalated"]
        if escalated:
            lessons.append(f"{len(escalated)} decisions required human escalation")
        
        # Find high-latency decisions
        slow = [e for e in events if e.latency_ms > 1000]
        if slow:
            lessons.append(f"{len(slow)} decisions took >1s - optimization needed")
        
        return lessons
    
    def _generate_insights(self, events: List[GovernanceEvent]) -> List[str]:
        """Generate strategic insights."""
        insights = []
        
        # Approval rate trend
        approved = len([e for e in events if e.decision == "approved"])
        rate = approved / len(events) if events else 0
        
        if rate > 0.9:
            insights.append("High approval rate - consider relaxing safe actions")
        elif rate < 0.5:
            insights.append("Low approval rate - review if too restrictive")
        
        return insights
    
    async def _update_memory(self, patterns: List[str], lessons: List[str], insights: List[str]):
        """Update strategic memory files."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        memory_file = self.memory_path / f"consolidated_{today}.md"
        
        content = f"""# Consolidated Memory - {today}

## Patterns Identified
{chr(10).join(f"- {p}" for p in patterns)}

## Lessons Learned
{chr(10).join(f"- {l}" for l in lessons)}

## Strategic Insights
{chr(10).join(f"- {i}" for i in insights)}

## Statistics
- Consolidated at: {datetime.utcnow().isoformat()}
- Total consolidations: {self._get_state().get('total_consolidations', 0)}
"""
        
        with open(memory_file, "w") as f:
            f.write(content)
    
    def record_decision(self):
        """Call this when a decision is made to increment counter."""
        state = self._get_state()
        state["decisions_since_consolidation"] = state.get("decisions_since_consolidation", 0) + 1
        self._save_state(state)


class TracePropagator:
    """
    Distributed tracing for governance events.
    Propagates trace_id across all components.
    """
    
    def __init__(self):
        self._current_trace: Optional[str] = None
    
    def start_trace(self) -> str:
        """Start a new trace."""
        trace_id = hashlib.sha256(
            f"{datetime.utcnow().timestamp()}{os.urandom(8)}".encode()
        ).hexdigest()[:16]
        self._current_trace = trace_id
        return trace_id
    
    def get_trace(self) -> Optional[str]:
        """Get current trace ID."""
        return self._current_trace
    
    def set_trace(self, trace_id: str):
        """Set trace ID from incoming request."""
        self._current_trace = trace_id
    
    def end_trace(self):
        """End current trace."""
        self._current_trace = None


# Export
__all__ = [
    'EventType',
    'GovernanceEvent',
    'EventStream',
    'ConsolidationResult',
    'MemoryConsolidator',
    'TracePropagator'
]
