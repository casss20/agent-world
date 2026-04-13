"""
Agent World: Observability Middleware
OpenTelemetry-style tracing, metrics, and structured logging
"""

import time
import uuid
import json
import logging
from typing import Optional, Dict, Any, Callable
from contextvars import ContextVar
from functools import wraps

from fastapi import Request, Response, Depends
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from prometheus_client import Counter, Histogram, Gauge, Info

# ============================================================================
# CONTEXT VARIABLES (for async-safe context propagation)
# ============================================================================

# Current trace ID
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')
# Current span ID
span_id_var: ContextVar[str] = ContextVar('span_id', default='')
# Current agent ID
agent_id_var: ContextVar[str] = ContextVar('agent_id', default='')
# Current business ID
business_id_var: ContextVar[str] = ContextVar('business_id', default='')

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Request metrics
REQUEST_COUNT = Counter(
    'agentworld_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'agentworld_request_duration_seconds',
    'Request latency',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Agent metrics
AGENT_STATUS = Gauge(
    'agentworld_agents_by_status',
    'Number of agents by status',
    ['status', 'agent_type']
)

AGENT_TASKS_COMPLETED = Counter(
    'agentworld_agent_tasks_completed_total',
    'Tasks completed by agent',
    ['agent_id', 'agent_type', 'task_type']
)

AGENT_TASKS_FAILED = Counter(
    'agentworld_agent_tasks_failed_total',
    'Tasks failed by agent',
    ['agent_id', 'agent_type', 'failure_reason']
)

# Task metrics
TASK_QUEUE_DEPTH = Gauge(
    'agentworld_task_queue_depth',
    'Current task queue depth',
    ['status', 'task_type']
)

TASK_PROCESSING_TIME = Histogram(
    'agentworld_task_processing_seconds',
    'Time to process a task',
    ['task_type'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
)

# Room metrics
ROOM_MEMBERS = Gauge(
    'agentworld_room_members',
    'Current room members',
    ['room_id', 'room_type']
)

ROOM_MESSAGES = Counter(
    'agentworld_room_messages_total',
    'Messages sent in room',
    ['room_id', 'message_type']
)

# Business metrics
BUSINESS_AGENTS = Gauge(
    'agentworld_business_agents',
    'Agents per business',
    ['business_id']
)

# System metrics
ACTIVE_CONNECTIONS = Gauge(
    'agentworld_websocket_connections',
    'Active WebSocket connections',
    ['connection_type']
)

# Info metric
BUILD_INFO = Info('agentworld_build', 'Build information')

# ============================================================================
# STRUCTURED LOGGER
# ============================================================================

class StructuredLogger:
    """JSON structured logger with correlation IDs"""
    
    def __init__(self, name: str = "agentworld"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Console handler with JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)
    
    def _make_record(self, level: str, message: str, extra: Dict[str, Any]) -> dict:
        """Create structured log record"""
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
            "level": level,
            "message": message,
            "trace_id": trace_id_var.get(),
            "span_id": span_id_var.get(),
            "agent_id": agent_id_var.get(),
            "business_id": business_id_var.get(),
        }
        record.update(extra)
        return record
    
    def info(self, message: str, **extra):
        record = self._make_record("INFO", message, extra)
        self.logger.info(json.dumps(record))
    
    def warning(self, message: str, **extra):
        record = self._make_record("WARNING", message, extra)
        self.logger.warning(json.dumps(record))
    
    def error(self, message: str, **extra):
        record = self._make_record("ERROR", message, extra)
        self.logger.error(json.dumps(record))
    
    def debug(self, message: str, **extra):
        record = self._make_record("DEBUG", message, extra)
        self.logger.debug(json.dumps(record))

class JsonFormatter(logging.Formatter):
    """JSON log formatter"""
    def format(self, record):
        if isinstance(record.msg, str):
            try:
                # Already JSON
                return record.msg
            except:
                pass
        
        log_obj = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if hasattr(record, 'trace_id'):
            log_obj['trace_id'] = record.trace_id
        
        return json.dumps(log_obj)

# Global logger instance
logger = StructuredLogger()

# ============================================================================
# TRACING MIDDLEWARE
# ============================================================================

class TracingMiddleware(BaseHTTPMiddleware):
    """
    Adds distributed tracing to all requests.
    
    Features:
    - Extracts or generates trace ID
    - Creates spans for each request
    - Propagates context to downstream services
    - Logs request/response with correlation IDs
    """
    
    def __init__(self, app: ASGIApp, service_name: str = "agentworld"):
        super().__init__(app)
        self.service_name = service_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate trace ID
        trace_id = request.headers.get('x-trace-id') or str(uuid.uuid4())
        span_id = str(uuid.uuid4())[:16]
        
        # Set context variables
        trace_id_var.set(trace_id)
        span_id_var.set(span_id)
        
        # Extract agent/business from JWT (if available)
        agent_id = self._extract_agent_id(request)
        business_id = self._extract_business_id(request)
        
        if agent_id:
            agent_id_var.set(agent_id)
        if business_id:
            business_id_var.set(business_id)
        
        # Add trace info to request state
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        request.state.start_time = time.time()
        
        # Log request start
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            user_agent=request.headers.get('user-agent'),
            client_ip=request.client.host if request.client else None
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - request.state.start_time
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            # Add trace headers to response
            response.headers['x-trace-id'] = trace_id
            response.headers['x-span-id'] = span_id
            
            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2)
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - request.state.start_time
            
            # Log error
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration * 1000, 2)
            )
            
            raise
    
    def _extract_agent_id(self, request: Request) -> Optional[str]:
        """Extract agent ID from JWT token"""
        # TODO: Implement JWT decoding
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            # Decode JWT and extract agent_id claim
            pass
        return None
    
    def _extract_business_id(self, request: Request) -> Optional[str]:
        """Extract business ID from JWT token"""
        # TODO: Implement JWT decoding
        return None

# ============================================================================
# AGENT ACTIVITY TRACER
# ============================================================================

class AgentTracer:
    """Tracer for agent activities"""
    
    @staticmethod
    def trace_task(agent_id: str, task_id: str, task_type: str):
        """Decorator to trace task execution"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                # Set context
                agent_id_var.set(agent_id)
                trace_id = str(uuid.uuid4())
                trace_id_var.set(trace_id)
                
                logger.info(
                    "Task started",
                    agent_id=agent_id,
                    task_id=task_id,
                    task_type=task_type
                )
                
                try:
                    result = await func(*args, **kwargs)
                    
                    duration = time.time() - start_time
                    
                    # Record metrics
                    AGENT_TASKS_COMPLETED.labels(
                        agent_id=agent_id,
                        agent_type="unknown",  # TODO: Get from agent
                        task_type=task_type
                    ).inc()
                    
                    TASK_PROCESSING_TIME.labels(
                        task_type=task_type
                    ).observe(duration)
                    
                    logger.info(
                        "Task completed",
                        agent_id=agent_id,
                        task_id=task_id,
                        task_type=task_type,
                        duration_ms=round(duration * 1000, 2)
                    )
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    # Record failure metric
                    AGENT_TASKS_FAILED.labels(
                        agent_id=agent_id,
                        agent_type="unknown",
                        failure_reason=type(e).__name__
                    ).inc()
                    
                    logger.error(
                        "Task failed",
                        agent_id=agent_id,
                        task_id=task_id,
                        task_type=task_type,
                        error=str(e),
                        error_type=type(e).__name__,
                        duration_ms=round(duration * 1000, 2)
                    )
                    
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def trace_tool_call(agent_id: str, tool_name: str):
        """Decorator to trace tool calls"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                logger.info(
                    "Tool call started",
                    agent_id=agent_id,
                    tool_name=tool_name,
                    args=str(args),
                    kwargs=str(kwargs)
                )
                
                try:
                    result = await func(*args, **kwargs)
                    
                    duration = time.time() - start_time
                    
                    logger.info(
                        "Tool call completed",
                        agent_id=agent_id,
                        tool_name=tool_name,
                        duration_ms=round(duration * 1000, 2)
                    )
                    
                    return result
                    
                except Exception as e:
                    logger.error(
                        "Tool call failed",
                        agent_id=agent_id,
                        tool_name=tool_name,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    
                    raise
            
            return wrapper
        return decorator

# ============================================================================
# METRICS ENDPOINTS
# ============================================================================

from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

metrics_router = APIRouter()

@metrics_router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from fastapi.responses import Response
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@metrics_router.get("/health/ready")
async def health_ready():
    """Readiness probe"""
    return {
        "status": "ready",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

@metrics_router.get("/health/live")
async def health_live():
    """Liveness probe"""
    return {
        "status": "alive",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_trace_id() -> str:
    """Get current trace ID"""
    return trace_id_var.get()

def get_logger() -> StructuredLogger:
    """Get structured logger with current context"""
    return logger

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
# Add middleware to FastAPI app:
from observability import TracingMiddleware

app.add_middleware(TracingMiddleware)

# Use tracer decorator:
from observability import AgentTracer

@AgentTracer.trace_task(agent_id="agent-123", task_id="task-456", task_type="scrape")
async def scrape_task(url: str):
    # Task implementation
    pass

# Log with context:
from observability import logger

logger.info("Processing message", message_id="msg-123", room_id="room-456")

# Access trace ID:
from observability import get_trace_id

trace_id = get_trace_id()
"""
