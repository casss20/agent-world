"""
Metrics Collection for AgentVerse
Tracks 8 critical metrics for scalability monitoring
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timezone


@dataclass
class MetricSnapshot:
    """Single metric reading"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricCollector:
    """
    Collects and aggregates metrics for monitoring
    
    Tracks:
    1. Adapter P99 latency
    2. Redis memory usage
    3. PostgreSQL connections
    4. Event loop lag
    5. Fallback activation rate
    6. Workflow error rate
    7. Cost per run
    8. Manual intervention rate
    """
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        
        # Metric storage
        self._metrics: Dict[str, deque] = {
            "adapter_latency_ms": deque(maxlen=max_history),
            "redis_memory_percent": deque(maxlen=100),
            "pg_connections_used": deque(maxlen=100),
            "event_loop_lag_ms": deque(maxlen=max_history),
            "fallback_activations": deque(maxlen=1000),
            "workflow_errors": deque(maxlen=1000),
            "workflow_success": deque(maxlen=1000),
            "cost_per_run": deque(maxlen=1000),
            "manual_interventions": deque(maxlen=100),
        }
        
        # Counters (don't reset)
        self._counters: Dict[str, float] = {
            "total_workflows": 0,
            "total_fallbacks": 0,
            "total_errors": 0,
            "total_cost": 0.0,
        }
        
        # Start time
        self._start_time = time.time()
    
    # ============== Recording Methods ==============
    
    def record_latency(self, duration_ms: float, operation: str = "unknown"):
        """Record adapter operation latency"""
        self._metrics["adapter_latency_ms"].append(MetricSnapshot(
            timestamp=time.time(),
            value=duration_ms,
            labels={"operation": operation}
        ))
    
    def record_redis_memory(self, percent: float):
        """Record Redis memory usage percentage"""
        self._metrics["redis_memory_percent"].append(MetricSnapshot(
            timestamp=time.time(),
            value=percent
        ))
    
    def record_pg_connections(self, used: int, max_conn: int):
        """Record PostgreSQL connection usage"""
        percent = (used / max_conn * 100) if max_conn > 0 else 0
        self._metrics["pg_connections_used"].append(MetricSnapshot(
            timestamp=time.time(),
            value=percent,
            labels={"used": str(used), "max": str(max_conn)}
        ))
    
    def record_event_loop_lag(self, lag_ms: float):
        """Record event loop lag"""
        self._metrics["event_loop_lag_ms"].append(MetricSnapshot(
            timestamp=time.time(),
            value=lag_ms
        ))
    
    def record_fallback_activation(self, reason: str):
        """Record a fallback to mock mode"""
        self._counters["total_fallbacks"] += 1
        self._metrics["fallback_activations"].append(MetricSnapshot(
            timestamp=time.time(),
            value=1.0,
            labels={"reason": reason}
        ))
    
    def record_workflow_completion(self, success: bool, error_type: str = None):
        """Record workflow completion"""
        self._counters["total_workflows"] += 1
        
        if success:
            self._metrics["workflow_success"].append(MetricSnapshot(
                timestamp=time.time(),
                value=1.0
            ))
        else:
            self._counters["total_errors"] += 1
            self._metrics["workflow_errors"].append(MetricSnapshot(
                timestamp=time.time(),
                value=1.0,
                labels={"error_type": error_type or "unknown"}
            ))
    
    def record_cost(self, cost_usd: float):
        """Record cost for a workflow run"""
        self._counters["total_cost"] += cost_usd
        self._metrics["cost_per_run"].append(MetricSnapshot(
            timestamp=time.time(),
            value=cost_usd
        ))
    
    def record_manual_intervention(self, intervention_type: str):
        """Record manual human intervention"""
        self._metrics["manual_interventions"].append(MetricSnapshot(
            timestamp=time.time(),
            value=1.0,
            labels={"type": intervention_type}
        ))
    
    # ============== Aggregation Methods ==============
    
    def get_p99_latency(self, window_seconds: int = 60) -> float:
        """Get P99 latency over the specified window"""
        return self._get_percentile("adapter_latency_ms", 99, window_seconds)
    
    def get_error_rate(self, window_seconds: int = 300) -> float:
        """Get error rate as percentage"""
        cutoff = time.time() - window_seconds
        
        errors = sum(1 for m in self._metrics["workflow_errors"] if m.timestamp > cutoff)
        success = sum(1 for m in self._metrics["workflow_success"] if m.timestamp > cutoff)
        total = errors + success
        
        return (errors / total * 100) if total > 0 else 0.0
    
    def get_fallback_rate(self, window_seconds: int = 300) -> float:
        """Get fallback activation rate as percentage"""
        cutoff = time.time() - window_seconds
        
        fallbacks = sum(1 for m in self._metrics["fallback_activations"] if m.timestamp > cutoff)
        total_workflows = sum(1 for m in self._metrics["workflow_success"] if m.timestamp > cutoff)
        total_workflows += sum(1 for m in self._metrics["workflow_errors"] if m.timestamp > cutoff)
        
        return (fallbacks / total_workflows * 100) if total_workflows > 0 else 0.0
    
    def get_average_cost(self, window_seconds: int = 3600) -> float:
        """Get average cost per run"""
        cutoff = time.time() - window_seconds
        costs = [m.value for m in self._metrics["cost_per_run"] if m.timestamp > cutoff]
        
        return sum(costs) / len(costs) if costs else 0.0
    
    def _get_percentile(self, metric_name: str, percentile: int, window_seconds: int) -> float:
        """Calculate percentile for a metric"""
        cutoff = time.time() - window_seconds
        values = [m.value for m in self._metrics[metric_name] if m.timestamp > cutoff]
        
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    # ============== Alert Thresholds ==============
    
    def check_alerts(self) -> list:
        """Check all metrics against alert thresholds"""
        alerts = []
        now = time.time()
        
        # 1. Adapter P99 latency > 500ms warning, >2s critical
        p99 = self.get_p99_latency(60)
        if p99 > 2000:
            alerts.append({"severity": "critical", "metric": "adapter_p99_latency", "value": p99, "threshold": 2000})
        elif p99 > 500:
            alerts.append({"severity": "warning", "metric": "adapter_p99_latency", "value": p99, "threshold": 500})
        
        # 2. Redis memory > 70% warning, >85% critical
        if self._metrics["redis_memory_percent"]:
            redis_mem = self._metrics["redis_memory_percent"][-1].value
            if redis_mem > 85:
                alerts.append({"severity": "critical", "metric": "redis_memory", "value": redis_mem, "threshold": 85})
            elif redis_mem > 70:
                alerts.append({"severity": "warning", "metric": "redis_memory", "value": redis_mem, "threshold": 70})
        
        # 3. PG connections > 80% pool warning
        if self._metrics["pg_connections_used"]:
            pg_conn = self._metrics["pg_connections_used"][-1].value
            if pg_conn > 80:
                alerts.append({"severity": "warning", "metric": "pg_connections", "value": pg_conn, "threshold": 80})
        
        # 4. Event loop lag > 100ms warning, >500ms critical
        if self._metrics["event_loop_lag_ms"]:
            lag = self._metrics["event_loop_lag_ms"][-1].value
            if lag > 500:
                alerts.append({"severity": "critical", "metric": "event_loop_lag", "value": lag, "threshold": 500})
            elif lag > 100:
                alerts.append({"severity": "warning", "metric": "event_loop_lag", "value": lag, "threshold": 100})
        
        # 5. Fallback rate > 5% warning, >20% critical
        fallback_rate = self.get_fallback_rate(300)
        if fallback_rate > 20:
            alerts.append({"severity": "critical", "metric": "fallback_rate", "value": fallback_rate, "threshold": 20})
        elif fallback_rate > 5:
            alerts.append({"severity": "warning", "metric": "fallback_rate", "value": fallback_rate, "threshold": 5})
        
        # 6. Error rate > 2% warning, >10% critical
        error_rate = self.get_error_rate(300)
        if error_rate > 10:
            alerts.append({"severity": "critical", "metric": "error_rate", "value": error_rate, "threshold": 10})
        elif error_rate > 2:
            alerts.append({"severity": "warning", "metric": "error_rate", "value": error_rate, "threshold": 2})
        
        # 7. Cost per run > $0.50 warning, >$1.00 critical
        avg_cost = self.get_average_cost(3600)
        if avg_cost > 1.0:
            alerts.append({"severity": "critical", "metric": "cost_per_run", "value": avg_cost, "threshold": 1.0})
        elif avg_cost > 0.5:
            alerts.append({"severity": "warning", "metric": "cost_per_run", "value": avg_cost, "threshold": 0.5})
        
        return alerts
    
    # ============== Export Methods ==============
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary for health endpoint"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": time.time() - self._start_time,
            "adapter": {
                "p99_latency_ms": self.get_p99_latency(60),
                "p95_latency_ms": self._get_percentile("adapter_latency_ms", 95, 60),
                "p50_latency_ms": self._get_percentile("adapter_latency_ms", 50, 60),
            },
            "workflows": {
                "total": self._counters["total_workflows"],
                "error_rate_5m": self.get_error_rate(300),
                "fallback_rate_5m": self.get_fallback_rate(300),
            },
            "resources": {
                "redis_memory_percent": self._metrics["redis_memory_percent"][-1].value if self._metrics["redis_memory_percent"] else 0,
                "pg_connections_percent": self._metrics["pg_connections_used"][-1].value if self._metrics["pg_connections_used"] else 0,
                "event_loop_lag_ms": self._metrics["event_loop_lag_ms"][-1].value if self._metrics["event_loop_lag_ms"] else 0,
            },
            "cost": {
                "average_per_run_1h": self.get_average_cost(3600),
                "total_1h": sum(m.value for m in self._metrics["cost_per_run"] if m.timestamp > time.time() - 3600),
            },
            "alerts": self.check_alerts(),
        }


# Global instance
_metrics: Optional[MetricCollector] = None


def get_metrics() -> MetricCollector:
    """Get or create global metrics collector"""
    global _metrics
    
    if _metrics is None:
        _metrics = MetricCollector()
    
    return _metrics


# Decorator for automatic latency tracking
def track_latency(operation: str):
    """Decorator to track function latency"""
    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = (time.time() - start) * 1000
                get_metrics().record_latency(duration_ms, operation)
        
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = (time.time() - start) * 1000
                get_metrics().record_latency(duration_ms, operation)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
