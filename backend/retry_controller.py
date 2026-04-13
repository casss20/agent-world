"""
Agent World: Retry Controller with Dead-Letter Queue
Implements retry policies, exponential backoff, and DLQ for failed tasks
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from enum import Enum as PyEnum
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func

from models import TaskQueue, TaskStatus, Agent
from observability import logger, AgentTracer

# ============================================================================
# RETRY CONFIGURATION
# ============================================================================

class RetryPolicy(PyEnum):
    """Retry policy types"""
    FIXED = "fixed"           # Fixed delay between retries
    EXPONENTIAL = "exponential"  # Exponential backoff
    LINEAR = "linear"         # Linear increasing delay

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    policy: RetryPolicy = RetryPolicy.EXPONENTIAL
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 300.0  # 5 minutes
    jitter: bool = True  # Add randomness to prevent thundering herd
    
    # Dead letter queue settings
    dlq_enabled: bool = True
    dlq_after_retries: int = 3  # Move to DLQ after this many failures

# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig()

# Task-type specific configurations
TASK_RETRY_CONFIGS: Dict[str, RetryConfig] = {
    "scrape": RetryConfig(
        max_retries=5,
        policy=RetryPolicy.EXPONENTIAL,
        base_delay_seconds=5.0,
        max_delay_seconds=600.0  # 10 minutes for scraping
    ),
    "publish": RetryConfig(
        max_retries=3,
        policy=RetryPolicy.EXPONENTIAL,
        base_delay_seconds=10.0
    ),
    "analyze": RetryConfig(
        max_retries=2,
        policy=RetryPolicy.LINEAR,
        base_delay_seconds=30.0
    ),
    "default": DEFAULT_RETRY_CONFIG
}

# ============================================================================
# RETRY CALCULATOR
# ============================================================================

def calculate_retry_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """
    Calculate delay before next retry attempt.
    
    Args:
        attempt: Current retry attempt number (0-indexed)
        config: Retry configuration
    
    Returns:
        Delay in seconds
    """
    import random
    
    if config.policy == RetryPolicy.FIXED:
        delay = config.base_delay_seconds
    
    elif config.policy == RetryPolicy.EXPONENTIAL:
        # Exponential: base * 2^attempt
        delay = config.base_delay_seconds * (2 ** attempt)
    
    elif config.policy == RetryPolicy.LINEAR:
        # Linear: base * (attempt + 1)
        delay = config.base_delay_seconds * (attempt + 1)
    
    else:
        delay = config.base_delay_seconds
    
    # Cap at max delay
    delay = min(delay, config.max_delay_seconds)
    
    # Add jitter (±25%) to prevent thundering herd
    if config.jitter:
        jitter_factor = 0.75 + (random.random() * 0.5)  # 0.75 to 1.25
        delay *= jitter_factor
    
    return delay

# ============================================================================
# DEAD LETTER QUEUE
# ============================================================================

class DeadLetterQueue:
    """
    Manages failed tasks that have exhausted retries.
    
    Features:
    - Store failed tasks with error details
    - Support for manual replay
    - Error classification and alerting
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def move_to_dlq(
        self,
        task_id: str,
        error_message: str,
        error_type: str,
        retry_history: List[Dict[str, Any]]
    ) -> None:
        """
        Move a task to the dead letter queue.
        
        Args:
            task_id: ID of the failed task
            error_message: Human-readable error description
            error_type: Classification of the error
            retry_history: List of retry attempts with timestamps
        """
        task = self.db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
        
        if not task:
            logger.error(f"Task {task_id} not found for DLQ move")
            return
        
        # Update task status
        task.status = TaskStatus.FAILED
        task.error_message = error_message
        
        # Store DLQ metadata
        dlq_metadata = {
            "moved_to_dlq_at": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "retry_history": retry_history,
            "total_attempts": len(retry_history),
        }
        
        # Merge with existing metadata
        existing_metadata = task.result or {}
        existing_metadata["dlq"] = dlq_metadata
        task.result = existing_metadata
        
        self.db.commit()
        
        logger.error(
            "Task moved to dead letter queue",
            task_id=str(task_id),
            task_type=task.task_type,
            error_type=error_type,
            error_message=error_message,
            total_attempts=len(retry_history)
        )
    
    def get_dlq_tasks(
        self,
        business_id: Optional[str] = None,
        task_type: Optional[str] = None,
        error_type: Optional[str] = None,
        limit: int = 50
    ) -> List[TaskQueue]:
        """
        Get tasks from the dead letter queue.
        
        Args:
            business_id: Filter by business
            task_type: Filter by task type
            error_type: Filter by error classification
            limit: Maximum number of tasks to return
        """
        query = self.db.query(TaskQueue).filter(
            TaskQueue.status == TaskStatus.FAILED
        )
        
        if business_id:
            query = query.filter(TaskQueue.business_id == business_id)
        
        if task_type:
            query = query.filter(TaskQueue.task_type == task_type)
        
        # Order by most recent failures first
        query = query.order_by(TaskQueue.completed_at.desc())
        
        return query.limit(limit).all()
    
    def replay_task(self, task_id: str) -> bool:
        """
        Replay a task from the dead letter queue.
        
        Args:
            task_id: ID of the task to replay
        
        Returns:
            True if replay initiated successfully
        """
        task = self.db.query(TaskQueue).filter(
            and_(
                TaskQueue.id == task_id,
                TaskQueue.status == TaskStatus.FAILED
            )
        ).first()
        
        if not task:
            return False
        
        # Reset task state
        task.status = TaskStatus.PENDING
        task.agent_id = None
        task.claimed_at = None
        task.lease_expires = None
        task.retry_count = 0
        task.error_message = None
        
        # Update metadata
        if task.result and isinstance(task.result, dict):
            task.result.pop("dlq", None)
            task.result["replayed_at"] = datetime.utcnow().isoformat()
        
        self.db.commit()
        
        logger.info(
            "Task replayed from DLQ",
            task_id=str(task_id),
            task_type=task.task_type
        )
        
        return True
    
    def classify_error(self, error: Exception) -> str:
        """
        Classify an error for DLQ organization.
        
        Returns:
            Error classification string
        """
        error_type = type(error).__name__
        error_str = str(error).lower()
        
        # Network/transient errors
        if any(x in error_str for x in ['timeout', 'connection', 'network', 'dns']):
            return "transient_network"
        
        # Rate limiting
        if any(x in error_str for x in ['rate limit', 'too many requests', '429']):
            return "rate_limited"
        
        # Authentication
        if any(x in error_str for x in ['unauthorized', 'forbidden', 'auth', '401', '403']):
            return "authentication"
        
        # Resource not found
        if any(x in error_str for x in ['not found', '404', 'does not exist']):
            return "not_found"
        
        # Validation errors
        if any(x in error_str for x in ['invalid', 'validation', 'bad request', '400']):
            return "validation"
        
        # External service errors
        if any(x in error_str for x in ['500', '502', '503', '504', 'service unavailable']):
            return "external_service"
        
        # Default
        return "unknown"

# ============================================================================
# RETRY CONTROLLER
# ============================================================================

class RetryController:
    """
    Manages task execution with retry logic.
    
    Features:
    - Configurable retry policies
    - Exponential backoff with jitter
    - Dead letter queue for exhausted retries
    - Error classification
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.dlq = DeadLetterQueue(db_session)
    
    async def execute_with_retry(
        self,
        task_id: str,
        task_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a task with retry logic.
        
        Args:
            task_id: ID of the task being executed
            task_func: Async function to execute
            *args, **kwargs: Arguments to pass to task_func
        
        Returns:
            Task result
        
        Raises:
            Exception: If all retries are exhausted
        """
        task = self.db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Get retry config for this task type
        config = TASK_RETRY_CONFIGS.get(task.task_type, TASK_RETRY_CONFIGS["default"])
        
        retry_history = []
        last_error = None
        
        # Attempt execution with retries
        for attempt in range(config.max_retries + 1):
            try:
                # Update task status
                task.status = TaskStatus.RUNNING
                task.retry_count = attempt
                self.db.commit()
                
                logger.info(
                    "Task execution attempt",
                    task_id=str(task_id),
                    attempt=attempt + 1,
                    max_retries=config.max_retries
                )
                
                # Execute task
                result = await task_func(*args, **kwargs)
                
                # Success!
                task.status = TaskStatus.COMPLETED
                task.result = {"output": result}
                task.completed_at = datetime.utcnow()
                self.db.commit()
                
                logger.info(
                    "Task completed successfully",
                    task_id=str(task_id),
                    attempts=attempt + 1
                )
                
                return result
                
            except Exception as e:
                last_error = e
                error_type = self.dlq.classify_error(e)
                
                retry_history.append({
                    "attempt": attempt + 1,
                    "timestamp": datetime.utcnow().isoformat(),
                    "error_type": error_type,
                    "error_message": str(e)
                })
                
                logger.warning(
                    "Task execution failed",
                    task_id=str(task_id),
                    attempt=attempt + 1,
                    error_type=error_type,
                    error_message=str(e)
                )
                
                # Check if we should retry
                if attempt < config.max_retries:
                    # Calculate delay before next retry
                    delay = calculate_retry_delay(attempt, config)
                    
                    logger.info(
                        "Retrying task after delay",
                        task_id=str(task_id),
                        delay_seconds=round(delay, 2),
                        next_attempt=attempt + 2
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    # Exhausted retries - move to DLQ
                    break
        
        # All retries exhausted
        error_type = self.dlq.classify_error(last_error)
        
        self.dlq.move_to_dlq(
            task_id=task_id,
            error_message=str(last_error),
            error_type=error_type,
            retry_history=retry_history
        )
        
        raise last_error
    
    async def process_dlq_batch(
        self,
        batch_size: int = 10,
        error_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a batch of DLQ tasks for replay.
        
        Args:
            batch_size: Number of tasks to process
            error_types: Only replay tasks with these error types
        
        Returns:
            Statistics about the batch processing
        """
        tasks = self.dlq.get_dlq_tasks(limit=batch_size * 2)
        
        if error_types:
            tasks = [
                t for t in tasks
                if t.result
                and isinstance(t.result, dict)
                and t.result.get("dlq", {}).get("error_type") in error_types
            ]
        
        tasks = tasks[:batch_size]
        
        replayed = 0
        failed = 0
        
        for task in tasks:
            try:
                if self.dlq.replay_task(str(task.id)):
                    replayed += 1
            except Exception as e:
                logger.error(
                    "Failed to replay task",
                    task_id=str(task.id),
                    error=str(e)
                )
                failed += 1
        
        return {
            "total_processed": len(tasks),
            "replayed": replayed,
            "failed": failed
        }

# ============================================================================
# DLQ API ENDPOINTS
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/dlq", tags=["dead-letter-queue"])

class DLQListResponse(BaseModel):
    tasks: List[Dict[str, Any]]
    total: int

class DLQReplayRequest(BaseModel):
    task_ids: List[str]

class DLQReplayResponse(BaseModel):
    replayed: int
    failed: int
    errors: List[Dict[str, str]]

def get_db():
    raise NotImplementedError("Override with actual dependency")

@router.get("/tasks", response_model=DLQListResponse)
async def list_dlq_tasks(
    business_id: Optional[str] = None,
    task_type: Optional[str] = None,
    error_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List tasks in the dead letter queue"""
    dlq = DeadLetterQueue(db)
    tasks = dlq.get_dlq_tasks(
        business_id=business_id,
        task_type=task_type,
        error_type=error_type,
        limit=limit
    )
    
    return {
        "tasks": [
            {
                "id": str(t.id),
                "task_type": t.task_type,
                "business_id": str(t.business_id),
                "error_message": t.error_message,
                "retry_count": t.retry_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "dlq_metadata": t.result.get("dlq") if t.result else None
            }
            for t in tasks
        ],
        "total": len(tasks)
    }

@router.post("/replay", response_model=DLQReplayResponse)
async def replay_dlq_tasks(
    request: DLQReplayRequest,
    db: Session = Depends(get_db)
):
    """Replay tasks from the dead letter queue"""
    dlq = DeadLetterQueue(db)
    
    replayed = 0
    failed = 0
    errors = []
    
    for task_id in request.task_ids:
        try:
            if dlq.replay_task(task_id):
                replayed += 1
            else:
                failed += 1
                errors.append({
                    "task_id": task_id,
                    "error": "Task not found or not in DLQ"
                })
        except Exception as e:
            failed += 1
            errors.append({
                "task_id": task_id,
                "error": str(e)
            })
    
    return {
        "replayed": replayed,
        "failed": failed,
        "errors": errors
    }

@router.get("/stats")
async def get_dlq_stats(db: Session = Depends(get_db)):
    """Get DLQ statistics"""
    # Count by error type
    error_type_counts = db.query(
        TaskQueue.result["dlq"]["error_type"].label("error_type"),
        func.count(TaskQueue.id).label("count")
    ).filter(
        TaskQueue.status == TaskStatus.FAILED
    ).group_by("error_type").all()
    
    # Count by task type
    task_type_counts = db.query(
        TaskQueue.task_type,
        func.count(TaskQueue.id).label("count")
    ).filter(
        TaskQueue.status == TaskStatus.FAILED
    ).group_by(TaskQueue.task_type).all()
    
    total_failed = db.query(func.count(TaskQueue.id)).filter(
        TaskQueue.status == TaskStatus.FAILED
    ).scalar()
    
    return {
        "total_failed_tasks": total_failed,
        "by_error_type": [
            {"error_type": e.error_type, "count": e.count}
            for e in error_type_counts
        ],
        "by_task_type": [
            {"task_type": t.task_type, "count": t.count}
            for t in task_type_counts
        ]
    }

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
# Execute task with retry:
from retry_controller import RetryController

retry_controller = RetryController(db_session)

result = await retry_controller.execute_with_retry(
    task_id="task-123",
    task_func=my_task_function,
    arg1="value1",
    arg2="value2"
)

# Get DLQ tasks:
dlq = DeadLetterQueue(db_session)
failed_tasks = dlq.get_dlq_tasks(task_type="scrape")

# Replay a task:
dlq.replay_task("task-123")
"""
