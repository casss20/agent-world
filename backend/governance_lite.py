"""
governance_lite.py — Agent World Lite

JSONL audit trail. Drop-in for the parts of governance_v2 that
diagnostic_routes.py actually uses: EventType, GovernanceEvent, and an
event stream with emit()/query().

Every intake, diagnosis, strategy, and approval is appended to one
append-only JSONL file — the "every recommendation is auditable" selling
point survives without the enterprise governance stack.
"""

import asyncio
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EventType(str, Enum):
    DECISION = "decision"
    ACTION = "action"
    APPROVAL = "approval"
    FAILURE = "failure"
    STRATEGY_APPROVED = "strategy_approved"


@dataclass
class GovernanceEvent:
    event_id: str
    timestamp: datetime
    event_type: EventType
    agent_id: str
    action: str
    resource: str
    decision: str
    reasoning: str
    risk_level: str = "safe"
    business_id: Any = 0
    trace_id: Optional[str] = None
    latency_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def generate_id() -> str:
        return f"evt_{uuid.uuid4().hex[:16]}"


class JSONLEventStream:
    """Append-only audit log. Survives restarts; human-readable; grep-able."""

    def __init__(self, path: str = "data/audit.jsonl"):
        self.path = path
        self._lock = asyncio.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    async def emit(self, event: GovernanceEvent) -> None:
        async with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event), default=str) + "\n")

    def query(self, business_id: Any = None, limit: int = 100) -> List[GovernanceEvent]:
        try:
            with open(self.path, encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return []

        events: List[GovernanceEvent] = []
        for line in lines[-limit * 2:]:
            try:
                d = json.loads(line)
                events.append(GovernanceEvent(
                    event_id=d["event_id"],
                    timestamp=datetime.fromisoformat(str(d["timestamp"])),
                    event_type=EventType(d["event_type"]),
                    agent_id=d.get("agent_id", ""),
                    action=d.get("action", ""),
                    resource=d.get("resource", ""),
                    decision=d.get("decision", ""),
                    reasoning=d.get("reasoning", ""),
                    risk_level=d.get("risk_level", "safe"),
                    business_id=d.get("business_id", 0),
                    trace_id=d.get("trace_id"),
                    latency_ms=d.get("latency_ms"),
                    metadata=d.get("metadata") or {},
                ))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        if business_id is not None:
            events = [e for e in events if str(e.business_id) == str(business_id)]
        return events[-limit:]


@dataclass
class LiteGovernance:
    """Minimal stand-in satisfying diagnostic_routes' get_event_stream()/get_tracer()."""
    event_stream: JSONLEventStream
    tracer: Any = None
