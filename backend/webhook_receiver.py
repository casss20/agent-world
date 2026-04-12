"""
Webhook Receiver for AgentVerse
Receives events from ChatDev Money and routes to rooms

Ticket 1: Phase 2 Production Readiness
"""

import os
import hmac
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Literal
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger("webhook_receiver")

# Router
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Configuration
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-secret-change-in-production")
WEBHOOK_TIMEOUT_MS = int(os.getenv("WEBHOOK_TIMEOUT_MS", "200"))


class WorkflowEvent(BaseModel):
    """
    Event payload from ChatDev Money
    
    All events include signature for verification
    """
    event_type: Literal[
        "workflow.started",
        "step.started", 
        "step.completed",
        "workflow.completed",
        "workflow.failed",
        "workflow.cancelled"
    ] = Field(..., description="Type of workflow event")
    
    run_id: str = Field(..., description="Unique workflow run ID")
    room_id: str = Field(..., description="AgentVerse room ID")
    
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data"
    )
    
    # Signature for HMAC verification
    signature: str = Field(..., description="HMAC-SHA256 signature")
    
    # Idempotency key for duplicate detection
    event_id: str = Field(..., description="Unique event ID for idempotency")
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure valid ISO timestamp"""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Invalid ISO 8601 timestamp")


class WebhookResponse(BaseModel):
    """Standard webhook response"""
    status: str
    event_id: str
    processed_at: str


class EventProcessor:
    """
    Process incoming webhook events
    
    Responsibilities:
    1. Verify signatures
    2. Deduplicate events
    3. Route to room WebSockets
    4. Track metrics
    """
    
    def __init__(self):
        # In-memory dedup cache (use Redis in production)
        self._processed_events: set = set()
        self._max_cache_size = 10000
        
        # Event handlers by type
        self._handlers: Dict[str, callable] = {
            "workflow.started": self._handle_workflow_started,
            "step.started": self._handle_step_started,
            "step.completed": self._handle_step_completed,
            "workflow.completed": self._handle_workflow_completed,
            "workflow.failed": self._handle_workflow_failed,
            "workflow.cancelled": self._handle_workflow_cancelled,
        }
    
    async def verify_signature(self, event: WorkflowEvent) -> bool:
        """
        Verify HMAC-SHA256 signature from ChatDev Money
        
        Signature format: HMAC-SHA256(event_id:timestamp:run_id)
        """
        try:
            message = f"{event.event_id}:{event.timestamp}:{event.run_id}"
            expected = hmac.new(
                WEBHOOK_SECRET.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(event.signature, expected)
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    def is_duplicate(self, event_id: str) -> bool:
        """Check if event was already processed"""
        if event_id in self._processed_events:
            return True
        
        # Add to cache
        self._processed_events.add(event_id)
        
        # Simple LRU: if too big, clear half
        if len(self._processed_events) > self._max_cache_size:
            self._processed_events = set(list(self._processed_events)[self._max_cache_size//2:])
        
        return False
    
    async def process_event(self, event: WorkflowEvent) -> WebhookResponse:
        """
        Main event processing pipeline
        
        Target: <200ms P99 processing time
        """
        start_time = datetime.now(timezone.utc)
        
        # 1. Verify signature
        if not await self.verify_signature(event):
            logger.warning(f"Invalid signature for event {event.event_id}")
            raise HTTPException(401, "Invalid signature")
        
        # 2. Deduplicate
        if self.is_duplicate(event.event_id):
            logger.info(f"Duplicate event {event.event_id}, skipping")
            return WebhookResponse(
                status="duplicate",
                event_id=event.event_id,
                processed_at=start_time.isoformat()
            )
        
        # 3. Route to handler
        handler = self._handlers.get(event.event_type)
        if handler:
            await handler(event)
        else:
            logger.warning(f"No handler for event type {event.event_type}")
        
        # 4. Record metrics
        processing_time_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        logger.info(
            f"Event {event.event_id} processed in {processing_time_ms:.1f}ms",
            extra={"event_type": event.event_type, "processing_ms": processing_time_ms}
        )
        
        return WebhookResponse(
            status="received",
            event_id=event.event_id,
            processed_at=start_time.isoformat()
        )
    
    # Event handlers
    async def _handle_workflow_started(self, event: WorkflowEvent):
        """Workflow execution started"""
        logger.info(f"Workflow {event.run_id} started in room {event.room_id}")
        # TODO: Broadcast to room WebSocket
        await self._broadcast_to_room(event.room_id, {
            "type": "workflow.started",
            "run_id": event.run_id,
            "timestamp": event.timestamp,
            "payload": event.payload
        })
    
    async def _handle_step_started(self, event: WorkflowEvent):
        """Workflow step started"""
        logger.info(f"Step started for {event.run_id}: {event.payload.get('step_name')}")
        await self._broadcast_to_room(event.room_id, {
            "type": "step.started",
            "run_id": event.run_id,
            "step": event.payload.get("step_name"),
            "agent": event.payload.get("agent_id"),
            "timestamp": event.timestamp
        })
    
    async def _handle_step_completed(self, event: WorkflowEvent):
        """Workflow step completed"""
        logger.info(f"Step completed for {event.run_id}: {event.payload.get('step_name')}")
        await self._broadcast_to_room(event.room_id, {
            "type": "step.completed",
            "run_id": event.run_id,
            "step": event.payload.get("step_name"),
            "agent": event.payload.get("agent_id"),
            "timestamp": event.timestamp,
            "outputs": event.payload.get("outputs", {})
        })
    
    async def _handle_workflow_completed(self, event: WorkflowEvent):
        """Workflow execution completed"""
        logger.info(f"Workflow {event.run_id} completed successfully")
        await self._broadcast_to_room(event.room_id, {
            "type": "workflow.completed",
            "run_id": event.run_id,
            "timestamp": event.timestamp,
            "outputs": event.payload.get("outputs", {}),
            "revenue": event.payload.get("revenue"),
            "platform": event.payload.get("platform")
        })
    
    async def _handle_workflow_failed(self, event: WorkflowEvent):
        """Workflow execution failed"""
        logger.error(f"Workflow {event.run_id} failed: {event.payload.get('error')}")
        await self._broadcast_to_room(event.room_id, {
            "type": "workflow.failed",
            "run_id": event.run_id,
            "timestamp": event.timestamp,
            "error": event.payload.get("error", "Unknown error")
        })
    
    async def _handle_workflow_cancelled(self, event: WorkflowEvent):
        """Workflow execution cancelled"""
        logger.info(f"Workflow {event.run_id} cancelled")
        await self._broadcast_to_room(event.room_id, {
            "type": "workflow.cancelled",
            "run_id": event.run_id,
            "timestamp": event.timestamp
        })
    
    async def _broadcast_to_room(self, room_id: str, message: Dict):
        """
        Broadcast event to room WebSocket connections
        
        TODO: Implement actual WebSocket broadcast
        For now, just log (WebSocket integration in separate ticket)
        """
        logger.info(f"Broadcast to room {room_id}: {message['type']}")
        # Placeholder: integrate with room WebSocket manager


# Global processor instance
_processor = EventProcessor()


@router.post("/chatdev/events", response_model=WebhookResponse)
async def receive_chatdev_event(event: WorkflowEvent):
    """
    Receive workflow events from ChatDev Money
    
    ## Event Types
    - `workflow.started` - Workflow execution began
    - `step.started` - Agent step started
    - `step.completed` - Agent step finished
    - `workflow.completed` - Workflow finished successfully
    - `workflow.failed` - Workflow failed
    - `workflow.cancelled` - Workflow was cancelled
    
    ## Security
    All events must include valid HMAC-SHA256 signature
    """
    return await _processor.process_event(event)


@router.get("/health")
async def webhook_health():
    """Health check for webhook receiver"""
    return {
        "status": "healthy",
        "processor": "active",
        "cache_size": len(_processor._processed_events),
        "secret_configured": WEBHOOK_SECRET != "dev-secret-change-in-production"
    }
