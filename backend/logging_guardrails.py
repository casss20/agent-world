"""
Production Guardrails Module
Structured logging, correlation IDs, timeouts, retries, and audit trails
"""

import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Optional, Dict, Any, Callable
from contextvars import ContextVar
import asyncio
from dataclasses import dataclass, asdict
from enum import Enum

# Context variable for correlation ID across async boundaries
correlation_id_ctx: ContextVar[str] = ContextVar('correlation_id', default='')
request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class StructuredLogEntry:
    """Structured log entry for consistent formatting"""
    timestamp: str
    level: str
    service: str
    correlation_id: str
    request_id: str
    event_type: str
    message: str
    context: Dict[str, Any]
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "service": self.service,
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "event_type": self.event_type,
            "message": self.message,
            "context": self.context,
            "duration_ms": self.duration_ms,
            "error": self.error
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class StructuredLogger:
    """
    Production-grade structured logger with correlation ID tracking
    
    Usage:
        logger = StructuredLogger("workflow_adapter")
        logger.info("workflow_launched", "Workflow started", {"room_id": "r123"})
    """
    
    def __init__(self, service_name: str, level: int = logging.INFO):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(level)
        
        # Clear existing handlers to avoid duplicates
        self.logger.handlers = []
        
        # Console handler with structured output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        self.logger.addHandler(console_handler)
        
        # Also add file handler for persistence
        file_handler = logging.FileHandler(f"/var/log/agentverse/{service_name}.log")
        file_handler.setLevel(level)
        self.logger.addHandler(file_handler)
    
    def _log(self, level: LogLevel, event_type: str, message: str, 
             context: Dict[str, Any] = None, duration_ms: float = None,
             error: Exception = None):
        """Internal log method with structured formatting"""
        
        # Get correlation ID from context
        corr_id = correlation_id_ctx.get() or str(uuid.uuid4())[:8]
        req_id = request_id_ctx.get() or str(uuid.uuid4())[:8]
        
        entry = StructuredLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            service=self.service_name,
            correlation_id=corr_id,
            request_id=req_id,
            event_type=event_type,
            message=message,
            context=context or {},
            duration_ms=duration_ms,
            error=str(error) if error else None
        )
        
        # Log as JSON for machine parsing
        log_fn = {
            LogLevel.DEBUG: self.logger.debug,
            LogLevel.INFO: self.logger.info,
            LogLevel.WARNING: self.logger.warning,
            LogLevel.ERROR: self.logger.error,
            LogLevel.CRITICAL: self.logger.critical
        }.get(level, self.logger.info)
        
        log_fn(entry.to_json())
        
        return entry
    
    def debug(self, event_type: str, message: str, context: Dict[str, Any] = None):
        return self._log(LogLevel.DEBUG, event_type, message, context)
    
    def info(self, event_type: str, message: str, context: Dict[str, Any] = None):
        return self._log(LogLevel.INFO, event_type, message, context)
    
    def warning(self, event_type: str, message: str, context: Dict[str, Any] = None):
        return self._log(LogLevel.WARNING, event_type, message, context)
    
    def error(self, event_type: str, message: str, 
              context: Dict[str, Any] = None, error: Exception = None):
        return self._log(LogLevel.ERROR, event_type, message, context, error=error)
    
    def critical(self, event_type: str, message: str,
                 context: Dict[str, Any] = None, error: Exception = None):
        return self._log(LogLevel.CRITICAL, event_type, message, context, error=error)
    
    def timing(self, event_type: str, message: str, 
               duration_ms: float, context: Dict[str, Any] = None):
        """Log with timing information"""
        return self._log(LogLevel.INFO, event_type, message, context, duration_ms)


def set_correlation_id(corr_id: str):
    """Set correlation ID for current context"""
    correlation_id_ctx.set(corr_id)


def set_request_id(req_id: str):
    """Set request ID for current context"""
    request_id_ctx.set(req_id)


def get_correlation_id() -> str:
    """Get current correlation ID or generate new one"""
    corr_id = correlation_id_ctx.get()
    if not corr_id:
        corr_id = str(uuid.uuid4())[:8]
        set_correlation_id(corr_id)
    return corr_id


def get_request_id() -> str:
    """Get current request ID or generate new one"""
    req_id = request_id_ctx.get()
    if not req_id:
        req_id = str(uuid.uuid4())[:8]
        set_request_id(req_id)
    return req_id


class CorrelationIdMiddleware:
    """FastAPI middleware to extract/set correlation IDs from requests"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract correlation ID from headers or generate
            headers = dict(scope.get("headers", []))
            corr_id = None
            req_id = None
            
            for key, value in headers.items():
                if key.lower() == b'x-correlation-id':
                    corr_id = value.decode('utf-8')
                if key.lower() == b'x-request-id':
                    req_id = value.decode('utf-8')
            
            if not corr_id:
                corr_id = str(uuid.uuid4())[:8]
            if not req_id:
                req_id = str(uuid.uuid4())[:8]
            
            # Set in context
            set_correlation_id(corr_id)
            set_request_id(req_id)
            
            # Add to response headers
            async def send_with_headers(message):
                if message["type"] == "http.response.start":
                    headers = message.get("headers", [])
                    headers.append([b"x-correlation-id", corr_id.encode()])
                    headers.append([b"x-request-id", req_id.encode()])
                    message["headers"] = headers
                await send(message)
            
            await self.app(scope, receive, send_with_headers)
        else:
            await self.app(scope, receive, send)


def timed(logger: StructuredLogger, event_type: str):
    """Decorator to log function execution time"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                logger.timing(f"{event_type}_success", f"{func.__name__} completed",
                             duration_ms, {"function": func.__name__})
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.error(f"{event_type}_failed", f"{func.__name__} failed",
                           {"function": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                           error=e)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                logger.timing(f"{event_type}_success", f"{func.__name__} completed",
                             duration_ms, {"function": func.__name__})
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.error(f"{event_type}_failed", f"{func.__name__} failed",
                           {"function": func.__name__}, error=e)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Convenience: Create loggers for different components
adapter_logger = StructuredLogger("workflow_adapter")
binding_logger = StructuredLogger("room_bindings")
audit_logger = StructuredLogger("audit_trail")
