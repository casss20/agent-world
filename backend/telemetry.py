"""
Agent World: OpenTelemetry Telemetry Setup
Standard OTLP-based observability for FastAPI
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.context import attach, set_value

# ============================================================================
# TELEMETRY SETUP
# ============================================================================

def setup_telemetry(
    service_name: str = "agent-world-backend",
    service_version: str = "2.0.0",
    environment: str = "dev",
    otlp_endpoint: Optional[str] = None
):
    """
    Initialize OpenTelemetry with OTLP export.
    
    This sets up:
    - Traces (via OTLPSpanExporter)
    - Metrics (via OTLPMetricExporter)
    - Logs (via OTLPLogExporter)
    """
    endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    
    # Create resource with service info
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version or os.getenv("APP_VERSION", "2.0.0"),
        DEPLOYMENT_ENVIRONMENT: environment or os.getenv("ENVIRONMENT", "dev"),
        "service.namespace": "agent-world",
        "host.name": os.getenv("HOSTNAME", "unknown"),
    })
    
    # ============================================================================
    # TRACES
    # ============================================================================
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{endpoint}/v1/traces",
                headers={"Content-Type": "application/x-protobuf"}
            )
        )
    )
    trace.set_tracer_provider(tracer_provider)
    
    # ============================================================================
    # METRICS
    # ============================================================================
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=f"{endpoint}/v1/metrics",
            headers={"Content-Type": "application/x-protobuf"}
        ),
        export_interval_millis=5000  # Export every 5 seconds
    )
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader]
    )
    metrics.set_meter_provider(meter_provider)
    
    # ============================================================================
    # LOGS
    # ============================================================================
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=f"{endpoint}/v1/logs",
                headers={"Content-Type": "application/x-protobuf"}
            )
        )
    )
    
    # Set up logging with OpenTelemetry handler
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    handler.setFormatter(JsonFormatter())
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler, logging.StreamHandler()]
    )
    
    # Get logger for agent-world
    logger = logging.getLogger("agent_world")
    logger.setLevel(logging.INFO)
    
    return tracer_provider, meter_provider, logger_provider


# ============================================================================
# JSON FORMATTER WITH TRACE CORRELATION
# ============================================================================

class JsonFormatter(logging.Formatter):
    """JSON formatter with trace/span ID injection"""
    
    def format(self, record):
        # Get current span context
        span = trace.get_current_span()
        span_ctx = span.get_span_context() if span else None
        
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add trace context if available
        if span_ctx and span_ctx.is_valid:
            log_obj["trace_id"] = format(span_ctx.trace_id, "032x")
            log_obj["span_id"] = format(span_ctx.span_id, "016x")
            log_obj["trace_flags"] = format(span_ctx.trace_flags, "02x")
        
        # Add extra fields from record
        if hasattr(record, "business_id"):
            log_obj["business_id"] = record.business_id
        if hasattr(record, "agent_id"):
            log_obj["agent_id"] = record.agent_id
        if hasattr(record, "room_id"):
            log_obj["room_id"] = record.room_id
        if hasattr(record, "task_id"):
            log_obj["task_id"] = record.task_id
        if hasattr(record, "event_type"):
            log_obj["event_type"] = record.event_type
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "error_code"):
            log_obj["error_code"] = record.error_code
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj, default=str)


# ============================================================================
# TRACER AND METER ACCESS
# ============================================================================

def get_tracer(name: str = "agent-world"):
    """Get OpenTelemetry tracer"""
    return trace.get_tracer(name)

def get_meter(name: str = "agent-world"):
    """Get OpenTelemetry meter"""
    return metrics.get_meter(name)


# ============================================================================
# CUSTOM METRICS
# ============================================================================

class AgentWorldMetrics:
    """Custom metrics for Agent World"""
    
    def __init__(self):
        self.meter = get_meter("agent-world")
        self._init_metrics()
    
    def _init_metrics(self):
        """Initialize all custom metrics"""
        
        # Task metrics
        self.task_claim_counter = self.meter.create_counter(
            "agentworld.task.claim.total",
            description="Number of task claim attempts",
            unit="1"
        )
        
        self.task_claim_success_counter = self.meter.create_counter(
            "agentworld.task.claim.success",
            description="Number of successful task claims",
            unit="1"
        )
        
        self.task_claim_latency = self.meter.create_histogram(
            "agentworld.task.claim.latency",
            description="Latency of task claim operations",
            unit="ms"
        )
        
        self.task_completion_counter = self.meter.create_counter(
            "agentworld.task.complete.total",
            description="Number of completed tasks",
            unit="1"
        )
        
        self.task_failure_counter = self.meter.create_counter(
            "agentworld.task.failure.total",
            description="Number of failed tasks",
            unit="1"
        )
        
        self.task_retry_counter = self.meter.create_counter(
            "agentworld.task.retry.total",
            description="Number of task retries",
            unit="1"
        )
        
        # Agent metrics
        self.active_agents_gauge = self.meter.create_up_down_counter(
            "agentworld.agents.active",
            description="Number of active agents",
            unit="1"
        )
        
        self.agent_heartbeat_age = self.meter.create_histogram(
            "agentworld.agent.heartbeat.age",
            description="Age of last heartbeat in seconds",
            unit="s"
        )
        
        # Room metrics
        self.room_occupancy_gauge = self.meter.create_up_down_counter(
            "agentworld.room.occupancy",
            description="Number of agents in room",
            unit="1"
        )
        
        self.room_join_counter = self.meter.create_counter(
            "agentworld.room.join.total",
            description="Number of room joins",
            unit="1"
        )
        
        self.room_leave_counter = self.meter.create_counter(
            "agentworld.room.leave.total",
            description="Number of room leaves",
            unit="1"
        )
        
        # Blackboard metrics
        self.blackboard_write_counter = self.meter.create_counter(
            "agentworld.blackboard.write.total",
            description="Number of blackboard writes",
            unit="1"
        )
        
        self.blackboard_conflict_counter = self.meter.create_counter(
            "agentworld.blackboard.conflict.total",
            description="Number of optimistic locking conflicts",
            unit="1"
        )
        
        # Governance metrics
        self.ledger_denial_counter = self.meter.create_counter(
            "agentworld.ledger.denial.total",
            description="Number of Ledger permission denials",
            unit="1"
        )
        
        self.ledger_check_latency = self.meter.create_histogram(
            "agentworld.ledger.check.latency",
            description="Latency of Ledger permission checks",
            unit="ms"
        )
        
        # DLQ metrics
        self.dlq_depth_gauge = self.meter.create_observable_gauge(
            "agentworld.dlq.depth",
            description="Current DLQ depth",
            unit="1"
        )
        
        self.dlq_retry_counter = self.meter.create_counter(
            "agentworld.dlq.retry.total",
            description="Number of DLQ task replays",
            unit="1"
        )

# Global metrics instance
_metrics: Optional[AgentWorldMetrics] = None

def get_metrics() -> AgentWorldMetrics:
    """Get or create global metrics instance"""
    global _metrics
    if _metrics is None:
        _metrics = AgentWorldMetrics()
    return _metrics


# ============================================================================
# TRACING DECORATORS
# ============================================================================

def traced(name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator to add tracing to functions.
    
    Usage:
        @traced(name="task.claim", attributes={"priority": "high"})
        async def claim_task(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or func.__name__
            
            with tracer.start_as_current_span(span_name) as span:
                # Set attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Set function info
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or func.__name__
            
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# ============================================================================
# LOGGING HELPERS
# ============================================================================

import asyncio

def get_logger(name: str = "agent_world") -> logging.Logger:
    """Get structured logger with agent-world configuration"""
    return logging.getLogger(name)


def log_agent_event(
    logger: logging.Logger,
    event_type: str,
    agent_id: Optional[str] = None,
    business_id: Optional[str] = None,
    room_id: Optional[str] = None,
    task_id: Optional[str] = None,
    result: Optional[str] = None,
    duration_ms: Optional[float] = None,
    error_code: Optional[str] = None,
    **extra
):
    """
    Log a structured agent event with full context.
    
    Args:
        event_type: Type of event (task_claimed, task_failed, etc.)
        agent_id: Agent ID
        business_id: Business/tenant ID
        room_id: Room ID
        task_id: Task ID
        result: Event result (success, failed, denied, etc.)
        duration_ms: Duration in milliseconds
        error_code: Error classification
        **extra: Additional fields
    """
    extra_fields = {
        "event_type": event_type,
        **extra
    }
    
    if agent_id:
        extra_fields["agent_id"] = agent_id
    if business_id:
        extra_fields["business_id"] = business_id
    if room_id:
        extra_fields["room_id"] = room_id
    if task_id:
        extra_fields["task_id"] = task_id
    if result:
        extra_fields["result"] = result
    if duration_ms:
        extra_fields["duration_ms"] = duration_ms
    if error_code:
        extra_fields["error_code"] = error_code
    
    # Create log record with extra fields
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "(unknown file)",
        0,
        f"Agent event: {event_type}",
        (),
        None
    )
    
    for key, value in extra_fields.items():
        setattr(record, key, value)
    
    logger.handle(record)


# ============================================================================
# CONTEXT PROPAGATION
# ============================================================================

def set_agent_context(
    agent_id: Optional[str] = None,
    business_id: Optional[str] = None,
    room_id: Optional[str] = None,
    task_id: Optional[str] = None
):
    """Set agent context in current span"""
    span = trace.get_current_span()
    
    if agent_id:
        span.set_attribute("agent.id", agent_id)
    if business_id:
        span.set_attribute("business.id", business_id)
    if room_id:
        span.set_attribute("room.id", room_id)
    if task_id:
        span.set_attribute("task.id", task_id)


# ============================================================================
# SHUTDOWN
# ============================================================================

def shutdown_telemetry():
    """Gracefully shutdown telemetry providers"""
    trace.get_tracer_provider().shutdown()
    metrics.get_meter_provider().shutdown()
