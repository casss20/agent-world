"""
Metrics Exporter - Ticket 1: Observability Stack
Prometheus metrics for AgentVerse Money Room
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response, Request
from functools import wraps
import time

# Application info
APP_INFO = Info('agentverse_adapter', 'Adapter application info')

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Workflow metrics
WORKFLOW_COUNT = Counter(
    'workflows_total',
    'Total workflows processed',
    ['status', 'workflow_id']
)

WORKFLOW_DURATION = Histogram(
    'workflow_duration_seconds',
    'Workflow execution duration',
    ['workflow_id'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

ACTIVE_WORKFLOWS = Gauge(
    'active_workflows',
    'Currently active workflows',
    ['status']
)

# Redis metrics
REDIS_CONNECTIONS = Gauge(
    'redis_connections_active',
    'Active Redis connections'
)

REDIS_OPS_TOTAL = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation_type', 'status']
)

REDIS_LATENCY = Histogram(
    'redis_operation_duration_seconds',
    'Redis operation latency',
    ['operation_type'],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 0.5=half_open)',
    ['breaker_name']
)

CIRCUIT_BREAKER_FAILURES = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['breaker_name']
)

# Instance metrics
INSTANCE_INFO = Info('adapter_instance', 'Adapter instance info')


class MetricsMiddleware:
    """FastAPI middleware for request metrics"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        
        # Capture status code
        status_code = 200
        
        async def wrapped_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)
        
        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            duration = time.time() - start_time
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status_code=str(status_code)
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=path
            ).observe(duration)


def record_workflow_start(workflow_id: str):
    """Record workflow start"""
    WORKFLOW_COUNT.labels(
        status='started',
        workflow_id=workflow_id
    ).inc()
    ACTIVE_WORKFLOWS.labels(status='running').inc()


def record_workflow_complete(workflow_id: str, duration_seconds: float):
    """Record workflow completion"""
    WORKFLOW_COUNT.labels(
        status='completed',
        workflow_id=workflow_id
    ).inc()
    WORKFLOW_DURATION.labels(
        workflow_id=workflow_id
    ).observe(duration_seconds)
    ACTIVE_WORKFLOWS.labels(status='running').dec()


def record_workflow_failure(workflow_id: str):
    """Record workflow failure"""
    WORKFLOW_COUNT.labels(
        status='failed',
        workflow_id=workflow_id
    ).inc()
    ACTIVE_WORKFLOWS.labels(status='running').dec()


def record_redis_operation(operation_type: str, duration_seconds: float, success: bool = True):
    """Record Redis operation"""
    status = 'success' if success else 'error'
    REDIS_OPS_TOTAL.labels(
        operation_type=operation_type,
        status=status
    ).inc()
    REDIS_LATENCY.labels(
        operation_type=operation_type
    ).observe(duration_seconds)


def update_circuit_breaker_state(name: str, state: str):
    """Update circuit breaker state gauge"""
    state_value = {'closed': 0, 'half_open': 0.5, 'open': 1}.get(state, 0)
    CIRCUIT_BREAKER_STATE.labels(breaker_name=name).set(state_value)


def record_circuit_breaker_failure(name: str):
    """Record circuit breaker failure"""
    CIRCUIT_BREAKER_FAILURES.labels(breaker_name=name).inc()


def get_metrics_response():
    """Generate Prometheus metrics response"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def initialize_metrics(instance_id: str, version: str = "2.1.0"):
    """Initialize application metrics"""
    APP_INFO.info({'version': version, 'service': 'stateless_adapter'})
    INSTANCE_INFO.info({'instance_id': instance_id})
