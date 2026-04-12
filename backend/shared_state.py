"""
Shared State Module for Stateless Adapter
Ticket 5: Phase 2 Production Readiness

Redis-backed state store for horizontal scaling
"""

import json
import redis
import pickle
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger("shared_state")

# Redis configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0


@dataclass
class CircuitBreakerState:
    """Circuit breaker state persisted in Redis"""
    state: str  # "CLOSED", "OPEN", "HALF_OPEN"
    failure_count: int
    last_failure_time: Optional[str]
    success_count: int


class SharedState:
    """
    Redis-backed shared state for stateless adapter
    
    Replaces instance-local state:
    - _circuit_breakers -> Redis hash
    - _active_polls -> Redis set
    - _audit_buffer -> Redis stream
    """
    
    def __init__(self, redis_client=None):
        self._redis = redis_client or redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        
        # Key prefixes for namespacing
        self._prefix = "agentverse:adapter"
        self._cb_prefix = f"{self._prefix}:circuit_breaker"
        self._poll_prefix = f"{self._prefix}:active_poll"
        self._run_prefix = f"{self._prefix}:workflow_run"
        self._event_prefix = f"{self._prefix}:event"
    
    # ============ Circuit Breaker State ============
    
    def get_circuit_breaker(self, name: str) -> CircuitBreakerState:
        """Get circuit breaker state from Redis"""
        key = f"{self._cb_prefix}:{name}"
        data = self._redis.hgetall(key)
        
        if not data:
            # Return default closed state
            return CircuitBreakerState(
                state="CLOSED",
                failure_count=0,
                last_failure_time=None,
                success_count=0
            )
        
        return CircuitBreakerState(
            state=data.get("state", "CLOSED"),
            failure_count=int(data.get("failure_count", 0)),
            last_failure_time=data.get("last_failure_time"),
            success_count=int(data.get("success_count", 0))
        )
    
    def set_circuit_breaker(self, name: str, state: CircuitBreakerState):
        """Update circuit breaker state in Redis"""
        key = f"{self._cb_prefix}:{name}"
        self._redis.hset(key, mapping={
            "state": state.state,
            "failure_count": state.failure_count,
            "last_failure_time": state.last_failure_time or "",
            "success_count": state.success_count
        })
        # TTL for cleanup
        self._redis.expire(key, 86400)  # 24 hours
    
    def is_circuit_open(self, name: str) -> bool:
        """Check if circuit breaker is open"""
        state = self.get_circuit_breaker(name)
        return state.state == "OPEN"
    
    def record_failure(self, name: str):
        """Record failure for circuit breaker"""
        state = self.get_circuit_breaker(name)
        state.failure_count += 1
        state.last_failure_time = datetime.now(timezone.utc).isoformat()
        
        # Check if threshold exceeded
        if state.failure_count >= 5:  # Configurable threshold
            state.state = "OPEN"
        
        self.set_circuit_breaker(name, state)
    
    def record_success(self, name: str):
        """Record success for circuit breaker"""
        state = self.get_circuit_breaker(name)
        state.success_count += 1
        
        if state.state == "HALF_OPEN":
            state.state = "CLOSED"
            state.failure_count = 0
        
        self.set_circuit_breaker(name, state)
    
    # ============ Active Polls ============
    
    def register_poll(self, run_id: str, instance_id: str):
        """Register that an instance is polling for a run"""
        key = f"{self._poll_prefix}:{run_id}"
        self._redis.sadd(key, instance_id)
        self._redis.expire(key, 3600)  # 1 hour TTL
    
    def unregister_poll(self, run_id: str, instance_id: str):
        """Unregister polling"""
        key = f"{self._poll_prefix}:{run_id}"
        self._redis.srem(key, instance_id)
    
    def get_active_pollers(self, run_id: str) -> Set[str]:
        """Get set of instances polling for a run"""
        key = f"{self._poll_prefix}:{run_id}"
        return self._redis.smembers(key)
    
    def is_being_polled(self, run_id: str) -> bool:
        """Check if any instance is polling for this run"""
        key = f"{self._poll_prefix}:{run_id}"
        return self._redis.scard(key) > 0
    
    # ============ Workflow Runs ============
    
    def create_run(self, run_id: str, request_data: Dict[str, Any]):
        """Create workflow run record"""
        key = f"{self._run_prefix}:{run_id}"
        data = {
            "run_id": run_id,
            "status": "pending",
            "request": json.dumps(request_data),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self._redis.hset(key, mapping=data)
        self._redis.expire(key, 86400 * 7)  # 7 days
    
    def update_run_status(self, run_id: str, status: str, metadata: Dict = None):
        """Update workflow run status"""
        key = f"{self._run_prefix}:{run_id}"
        updates = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if metadata:
            updates["metadata"] = json.dumps(metadata)
        self._redis.hset(key, mapping=updates)
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow run data"""
        key = f"{self._run_prefix}:{run_id}"
        data = self._redis.hgetall(key)
        if not data:
            return None
        
        # Parse JSON fields
        if "request" in data:
            try:
                data["request"] = json.loads(data["request"])
            except json.JSONDecodeError:
                pass
        if "metadata" in data:
            try:
                data["metadata"] = json.loads(data["metadata"])
            except json.JSONDecodeError:
                pass
        return data
    
    # ============ Event Publishing ============
    
    def publish_event(self, channel: str, event: Dict[str, Any]):
        """Publish event to Redis Pub/Sub"""
        event_json = json.dumps(event)
        self._redis.publish(f"{self._prefix}:channel:{channel}", event_json)
    
    def subscribe_events(self, channel: str):
        """Subscribe to event channel"""
        pubsub = self._redis.pubsub()
        pubsub.subscribe(f"{self._prefix}:channel:{channel}")
        return pubsub
    
    # ============ Metrics ============
    
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record metric with timestamp"""
        key = f"{self._prefix}:metrics:{metric_name}"
        timestamp = datetime.now(timezone.utc).isoformat()
        data = {
            "timestamp": timestamp,
            "value": value,
            "tags": json.dumps(tags or {})
        }
        # Use Redis sorted set for time-series data
        self._redis.zadd(key, {json.dumps(data): datetime.now(timezone.utc).timestamp()})
        # Trim old data (keep last 24 hours)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).timestamp()
        self._redis.zremrangebyscore(key, 0, cutoff)
    
    # ============ Health ============
    
    def health_check(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            self._redis.ping()
            return {"status": "healthy", "redis": "connected"}
        except redis.ConnectionError as e:
            return {"status": "unhealthy", "redis": str(e)}


# Global instance
_shared_state: Optional[SharedState] = None


def get_shared_state() -> SharedState:
    """Get or create global shared state instance"""
    global _shared_state
    if _shared_state is None:
        _shared_state = SharedState()
    return _shared_state
