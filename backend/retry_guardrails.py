"""
Timeout, Retry, and Circuit Breaker Guardrails
Production-grade failure handling for workflow operations
"""

import asyncio
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Any, TypeVar, Generic
from datetime import datetime, timedelta
import functools

from logging_guardrails import adapter_logger, get_correlation_id


T = TypeVar('T')


class RetryStrategy(Enum):
    """Retry strategies"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    retryable_exceptions: tuple = (Exception,)
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if self.strategy == RetryStrategy.FIXED:
            return self.base_delay_seconds
        
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay_seconds * (2 ** attempt)
            return min(delay, self.max_delay_seconds)
        
        elif self.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            # Add jitter to prevent thundering herd
            exp_delay = self.base_delay_seconds * (2 ** attempt)
            jitter = random.uniform(0, exp_delay * 0.1)
            delay = min(exp_delay + jitter, self.max_delay_seconds)
            return delay
        
        return self.base_delay_seconds


class TimeoutError(Exception):
    """Custom timeout error with context"""
    def __init__(self, operation: str, timeout_seconds: float, correlation_id: str = None):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.correlation_id = correlation_id or get_correlation_id()
        super().__init__(f"Operation '{operation}' timed out after {timeout_seconds}s "
                        f"(corr_id: {self.correlation_id})")


class CircuitBreakerOpen(Exception):
    """Circuit breaker is open - service considered unhealthy"""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern for fault tolerance
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold exceeded, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """
    
    class State(Enum):
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)
        self.half_open_max_calls = half_open_max_calls
        
        self.state = self.State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def record_success(self):
        """Record a successful call"""
        if self.state == self.State.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self._close_circuit()
        else:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == self.State.HALF_OPEN:
            self._open_circuit()
        elif self.failure_count >= self.failure_threshold:
            self._open_circuit()
    
    def can_execute(self) -> bool:
        """Check if call should be allowed"""
        if self.state == self.State.CLOSED:
            return True
        
        if self.state == self.State.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = datetime.utcnow() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._half_open_circuit()
                    return True
            return False
        
        if self.state == self.State.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return True
    
    def _open_circuit(self):
        self.state = self.State.OPEN
        adapter_logger.warning("circuit_breaker_opened", 
                              f"Circuit breaker '{self.name}' opened",
                              {"breaker_name": self.name, "failure_count": self.failure_count})
    
    def _close_circuit(self):
        self.state = self.State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        adapter_logger.info("circuit_breaker_closed",
                           f"Circuit breaker '{self.name}' closed",
                           {"breaker_name": self.name})
    
    def _half_open_circuit(self):
        self.state = self.State.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0
        adapter_logger.info("circuit_breaker_half_open",
                           f"Circuit breaker '{self.name}' half-open",
                           {"breaker_name": self.name})


class GuardedOperation:
    """
    Wraps operations with timeout, retry, and circuit breaker protection
    """
    
    def __init__(
        self,
        name: str,
        timeout_seconds: float = 30.0,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = circuit_breaker
    
    async def execute(self, operation: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute operation with full guardrails
        
        1. Check circuit breaker
        2. Apply timeout
        3. Apply retries
        """
        corr_id = get_correlation_id()
        
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpen(f"Circuit breaker '{self.circuit_breaker.name}' is open")
        
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                adapter_logger.debug("operation_attempt",
                                    f"Attempting {self.name}",
                                    {"operation": self.name, "attempt": attempt + 1, 
                                     "correlation_id": corr_id})
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    operation(*args, **kwargs),
                    timeout=self.timeout_seconds
                )
                
                # Record success
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                
                if attempt > 0:
                    adapter_logger.info("operation_recovered",
                                       f"{self.name} succeeded after {attempt + 1} attempts",
                                       {"operation": self.name, "attempts": attempt + 1})
                
                return result
                
            except asyncio.TimeoutError:
                last_exception = TimeoutError(self.name, self.timeout_seconds, corr_id)
                adapter_logger.warning("operation_timeout",
                                      f"{self.name} timed out (attempt {attempt + 1})",
                                      {"operation": self.name, "attempt": attempt + 1,
                                       "timeout": self.timeout_seconds})
                
            except self.retry_config.retryable_exceptions as e:
                last_exception = e
                adapter_logger.warning("operation_failed",
                                      f"{self.name} failed (attempt {attempt + 1}): {str(e)}",
                                      {"operation": self.name, "attempt": attempt + 1,
                                       "error": str(e)})
            
            # Record failure for circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            
            # Calculate and apply delay before retry
            if attempt < self.retry_config.max_attempts - 1:
                delay = self.retry_config.calculate_delay(attempt)
                adapter_logger.debug("operation_retry_delay",
                                    f"Retrying {self.name} in {delay:.2f}s",
                                    {"operation": self.name, "delay": delay})
                await asyncio.sleep(delay)
        
        # All retries exhausted
        adapter_logger.error("operation_exhausted",
                            f"{self.name} failed after {self.retry_config.max_attempts} attempts",
                            {"operation": self.name, "attempts": self.retry_config.max_attempts},
                            error=last_exception)
        
        raise last_exception


# Pre-configured guardrails for common operations

# For workflow launches (can take longer)
WORKFLOW_LAUNCH_GUARDS = GuardedOperation(
    name="workflow_launch",
    timeout_seconds=60.0,
    retry_config=RetryConfig(
        max_attempts=3,
        base_delay_seconds=2.0,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions=(Exception,)
    ),
    circuit_breaker=CircuitBreaker(
        name="workflow_launch",
        failure_threshold=5,
        recovery_timeout_seconds=60.0
    )
)

# For status polling (should be fast)
STATUS_POLL_GUARDS = GuardedOperation(
    name="status_poll",
    timeout_seconds=10.0,
    retry_config=RetryConfig(
        max_attempts=2,
        base_delay_seconds=0.5,
        strategy=RetryStrategy.FIXED,
        retryable_exceptions=(Exception,)
    )
)

# For cancel operations (must be responsive)
CANCEL_GUARDS = GuardedOperation(
    name="cancel_workflow",
    timeout_seconds=5.0,
    retry_config=RetryConfig(
        max_attempts=2,
        base_delay_seconds=0.5,
        strategy=RetryStrategy.FIXED,
        retryable_exceptions=(Exception,)
    )
)


# Convenience decorators

def with_timeout(timeout_seconds: float):
    """Decorator to add timeout to async function"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout_seconds
            )
        return wrapper
    return decorator


def with_retry(config: Optional[RetryConfig] = None):
    """Decorator to add retry logic to async function"""
    config = config or RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        delay = config.calculate_delay(attempt)
                        await asyncio.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator


class WorkflowCancellation:
    """Manage workflow cancellation with cleanup"""
    
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.cancelled = False
        self.cancelled_at: Optional[datetime] = None
        self.cancellation_reason: Optional[str] = None
    
    def cancel(self, reason: str = "user_request"):
        """Mark workflow for cancellation"""
        self.cancelled = True
        self.cancelled_at = datetime.utcnow()
        self.cancellation_reason = reason
        
        adapter_logger.info("workflow_cancellation_requested",
                           f"Cancellation requested for {self.run_id}",
                           {"run_id": self.run_id, "reason": reason})
    
    def check_cancelled(self):
        """Check if cancellation was requested - call periodically in long operations"""
        if self.cancelled:
            raise asyncio.CancelledError(
                f"Workflow {self.run_id} cancelled: {self.cancellation_reason}"
            )


# Global cancellation registry
_cancellations: dict[str, WorkflowCancellation] = {}


def register_cancellation(run_id: str) -> WorkflowCancellation:
    """Register a new cancellable workflow"""
    cancel = WorkflowCancellation(run_id)
    _cancellations[run_id] = cancel
    return cancel


def get_cancellation(run_id: str) -> Optional[WorkflowCancellation]:
    """Get cancellation handle for workflow"""
    return _cancellations.get(run_id)


def unregister_cancellation(run_id: str):
    """Remove cancellation handle after workflow completes"""
    if run_id in _cancellations:
        del _cancellations[run_id]
