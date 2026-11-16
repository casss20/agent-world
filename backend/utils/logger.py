"""
Structured Logging
Correlation IDs, JSON formatting, and log levels for production observability.

Adapted from Ruflo pattern: event-driven telemetry and tracing.
"""

import logging
import sys
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ── Correlation ID Context ──────────────────────────────────────────────────
_correlation_id: str = ""


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set or generate a correlation ID for tracing requests."""
    global _correlation_id
    _correlation_id = cid or str(uuid.uuid4())[:8]
    return _correlation_id


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return _correlation_id or "none"


# ── JSON Formatter ──────────────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    """Output structured JSON logs for production parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", get_correlation_id()),
            "source": {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Include exception info
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Include extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "asctime", "correlation_id",
            }:
                log_obj[key] = value

        return json.dumps(log_obj, default=str)


# ── Setup ────────────────────────────────────────────────────────────────────
def setup_logging(
    level: str = "INFO",
    use_json: bool = True,
    correlation_id: Optional[str] = None,
) -> None:
    """
    Configure root logger for production.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        use_json: Use JSON formatting (production) vs human-readable (dev)
        correlation_id: Initial correlation ID
    """
    if correlation_id:
        set_correlation_id(correlation_id)

    handler = logging.StreamHandler(sys.stdout)
    if use_json:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(correlation_id)s | %(levelname)-8s | %(name)s | %(message)s"
            )
        )

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers = []  # Clear existing
    root.addHandler(handler)

    # Suppress noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ── Convenience ─────────────────────────────────────────────────────────────
def get_logger(name: str) -> logging.Logger:
    """Get a logger with correlation ID support."""
    return logging.getLogger(name)


class LogContext:
    """Context manager for correlation ID scoping."""

    def __init__(self, cid: Optional[str] = None):
        self.cid = cid or str(uuid.uuid4())[:8]
        self.previous: str = ""

    def __enter__(self) -> "LogContext":
        self.previous = get_correlation_id()
        set_correlation_id(self.cid)
        return self

    def __exit__(self, *args: Any) -> None:
        set_correlation_id(self.previous)
