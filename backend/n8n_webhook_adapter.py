"""
n8n_webhook_adapter.py — Agent World

Outbound webhook system for n8n integration.
Sends events to n8n workflows for notifications, logging, integrations.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from models import get_db
from ledger_client import require_capability

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/n8n", tags=["n8n"])


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class WebhookEndpoint:
    """Registered n8n webhook endpoint"""
    name: str
    url: str
    events: List[str]  # Which events to send
    secret: Optional[str] = None  # For HMAC signature
    retry_count: int = 3
    timeout_seconds: int = 30
    enabled: bool = True


# In-production, load from database or config service
REGISTERED_ENDPOINTS: Dict[str, WebhookEndpoint] = {}


def register_endpoint(endpoint: WebhookEndpoint):
    """Register an n8n webhook endpoint"""
    REGISTERED_ENDPOINTS[endpoint.name] = endpoint
    logger.info(f"Registered n8n endpoint: {endpoint.name} -> {endpoint.url}")


def get_enabled_endpoints(event_type: str) -> List[WebhookEndpoint]:
    """Get all endpoints that want this event type"""
    return [
        ep for ep in REGISTERED_ENDPOINTS.values()
        if ep.enabled and (event_type in ep.events or "*" in ep.events)
    ]


# ============================================================================
# API Models
# ============================================================================

class RegisterWebhookRequest(BaseModel):
    name: str
    url: HttpUrl
    events: List[str]  # ["sale_made", "campaign_scaled", "*"]
    secret: Optional[str] = None
    retry_count: int = 3


class WebhookEventPayload(BaseModel):
    event_type: str
    timestamp: datetime
    payload: Dict[str, Any]
    source: str = "agent_world"
    version: str = "1.0"


class SendTestEventRequest(BaseModel):
    event_type: str
    payload: Dict[str, Any]


class WebhookDeliveryStatus(BaseModel):
    endpoint: str
    event_type: str
    status: str  # success, failed, retrying
    status_code: Optional[int]
    response_body: Optional[str]
    latency_ms: float
    retry_count: int


# ============================================================================
# Core Webhook Sender
# ============================================================================

class N8NWebhookClient:
    """Client for sending events to n8n workflows"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def send_event(
        self,
        endpoint: WebhookEndpoint,
        event_type: str,
        payload: Dict[str, Any]
    ) -> WebhookDeliveryStatus:
        """Send single event to n8n endpoint"""
        
        event_payload = WebhookEventPayload(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            payload=payload,
            source="agent_world",
            version="1.0"
        )
        
        body = event_payload.dict()
        body_json = json.dumps(body, default=str)
        
        # Build headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentWorld-Webhook/1.0",
            "X-Agent-World-Event": event_type,
            "X-Agent-World-Timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add HMAC signature if secret configured
        if endpoint.secret:
            signature = self._sign_payload(body_json, endpoint.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        
        start_time = datetime.utcnow()
        
        try:
            response = await self.client.post(
                endpoint.url,
                content=body_json,
                headers=headers
            )
            
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return WebhookDeliveryStatus(
                endpoint=endpoint.name,
                event_type=event_type,
                status="success" if response.status_code < 400 else "failed",
                status_code=response.status_code,
                response_body=response.text[:1000] if response.status_code >= 400 else None,
                latency_ms=latency_ms,
                retry_count=0
            )
            
        except httpx.TimeoutException:
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return WebhookDeliveryStatus(
                endpoint=endpoint.name,
                event_type=event_type,
                status="failed",
                status_code=None,
                response_body="Timeout",
                latency_ms=latency_ms,
                retry_count=0
            )
            
        except Exception as e:
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return WebhookDeliveryStatus(
                endpoint=endpoint.name,
                event_type=event_type,
                status="failed",
                status_code=None,
                response_body=str(e)[:500],
                latency_ms=latency_ms,
                retry_count=0
            )
    
    async def send_with_retry(
        self,
        endpoint: WebhookEndpoint,
        event_type: str,
        payload: Dict[str, Any]
    ) -> WebhookDeliveryStatus:
        """Send with exponential backoff retry"""
        
        for attempt in range(endpoint.retry_count):
            result = await self.send_event(endpoint, event_type, payload)
            
            if result.status == "success":
                result.retry_count = attempt
                return result
            
            if attempt < endpoint.retry_count - 1:
                # Exponential backoff: 2s, 4s, 8s
                await asyncio.sleep(2 ** attempt)
                result.status = "retrying"
        
        result.retry_count = endpoint.retry_count
        return result
    
    def _sign_payload(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def broadcast_event(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ) -> List[WebhookDeliveryStatus]:
        """Send event to all registered endpoints that want it"""
        
        endpoints = get_enabled_endpoints(event_type)
        
        if not endpoints:
            logger.debug(f"No endpoints registered for event: {event_type}")
            return []
        
        # Send to all endpoints concurrently
        tasks = [
            self.send_with_retry(ep, event_type, payload)
            for ep in endpoints
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log failures
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Webhook exception: {result}")
            elif result.status == "failed":
                logger.warning(
                    f"Webhook failed: {result.endpoint} "
                    f"for {result.event_type}: {result.response_body}"
                )
        
        return [r for r in results if not isinstance(r, Exception)]


# Global client instance
webhook_client = N8NWebhookClient()


# ============================================================================
# Convenience Functions (Used by Agents)
# ============================================================================

async def notify_sale_made(
    order_id: str,
    channel: str,
    revenue: float,
    campaign_id: Optional[str] = None,
    product_name: Optional[str] = None
):
    """Notify n8n when Merchant agent makes a sale"""
    await webhook_client.broadcast_event("sale_made", {
        "order_id": order_id,
        "channel": channel,
        "revenue": revenue,
        "campaign_id": campaign_id,
        "product_name": product_name,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_campaign_scaled(
    campaign_id: str,
    campaign_name: str,
    roas: float,
    new_budget: float,
    platform: str
):
    """Notify n8n when Promoter agent scales a campaign"""
    await webhook_client.broadcast_event("campaign_scaled", {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "roas": roas,
        "new_budget": new_budget,
        "platform": platform,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_campaign_paused(
    campaign_id: str,
    campaign_name: str,
    roas: float,
    reason: str,
    platform: str
):
    """Notify n8n when Promoter agent pauses a campaign"""
    await webhook_client.broadcast_event("campaign_paused", {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "roas": roas,
        "reason": reason,
        "platform": platform,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_approval_needed(
    approval_id: str,
    action_type: str,
    description: str,
    estimated_cost: float,
    business_id: str
):
    """Notify n8n when approval is needed (for Slack/email routing)"""
    await webhook_client.broadcast_event("approval_needed", {
        "approval_id": approval_id,
        "action_type": action_type,
        "description": description,
        "estimated_cost": estimated_cost,
        "business_id": business_id,
        "review_url": f"/approvals/{approval_id}",
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_task_completed(
    task_id: str,
    task_type: str,
    agent_name: str,
    room_id: str,
    result_summary: str
):
    """Notify n8n when any agent completes a task"""
    await webhook_client.broadcast_event("task_completed", {
        "task_id": task_id,
        "task_type": task_type,
        "agent_name": agent_name,
        "room_id": room_id,
        "result_summary": result_summary,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_diagnosis_complete(
    diagnosis_id: str,
    business_id: str,
    health_score: float,
    top_bottleneck: str,
    recommended_strategy: str
):
    """Notify n8n when diagnosis is complete"""
    await webhook_client.broadcast_event("diagnosis_complete", {
        "diagnosis_id": diagnosis_id,
        "business_id": business_id,
        "health_score": health_score,
        "top_bottleneck": top_bottleneck,
        "recommended_strategy": recommended_strategy,
        "timestamp": datetime.utcnow().isoformat()
    })


# ============================================================================
# API Routes (Management)
# ============================================================================

@router.post("/webhooks/register")
async def register_webhook(
    request: RegisterWebhookRequest,
    db: Session = Depends(get_db)
):
    """Register a new n8n webhook endpoint"""
    # In production: require admin capability
    
    endpoint = WebhookEndpoint(
        name=request.name,
        url=str(request.url),
        events=request.events,
        secret=request.secret,
        retry_count=request.retry_count
    )
    
    register_endpoint(endpoint)
    
    return {
        "success": True,
        "endpoint": request.name,
        "events_subscribed": request.events,
        "message": f"Endpoint registered. Will receive: {', '.join(request.events)}"
    }


@router.get("/webhooks")
async def list_webhooks():
    """List all registered webhook endpoints"""
    return {
        "endpoints": [
            {
                "name": ep.name,
                "url": ep.url,
                "events": ep.events,
                "enabled": ep.enabled,
                "retry_count": ep.retry_count
            }
            for ep in REGISTERED_ENDPOINTS.values()
        ]
    }


@router.post("/webhooks/{name}/test")
async def test_webhook(name: str, request: SendTestEventRequest):
    """Send a test event to a specific webhook"""
    if name not in REGISTERED_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    endpoint = REGISTERED_ENDPOINTS[name]
    
    result = await webhook_client.send_with_retry(
        endpoint,
        request.event_type,
        request.payload
    )
    
    return {
        "success": result.status == "success",
        "endpoint": name,
        "event_type": request.event_type,
        "status": result.status,
        "status_code": result.status_code,
        "latency_ms": result.latency_ms,
        "retry_count": result.retry_count
    }


@router.post("/webhooks/test-broadcast")
async def test_broadcast(request: SendTestEventRequest):
    """Broadcast test event to all matching endpoints"""
    results = await webhook_client.broadcast_event(
        request.event_type,
        request.payload
    )
    
    return {
        "success": True,
        "event_type": request.event_type,
        "endpoints_notified": len(results),
        "results": [
            {
                "endpoint": r.endpoint,
                "status": r.status,
                "latency_ms": r.latency_ms
            }
            for r in results
        ]
    }


@router.post("/events/{event_type}")
async def receive_event(event_type: str, request: Request):
    """
    Receive events FROM n8n (inbound).
    n8n can trigger Agent World workflows via this endpoint.
    """
    payload = await request.json()
    
    handlers = {
        "scheduled_scout": _handle_scheduled_scout,
        "external_data_synced": _handle_external_data,
        "user_action": _handle_user_action,
    }
    
    handler = handlers.get(event_type)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown event type: {event_type}")
    
    return await handler(payload)


# ============================================================================
# Inbound Event Handlers (n8n → Agent World)
# ============================================================================

async def _handle_scheduled_scout(payload: Dict):
    """Trigger Nova scout from n8n schedule"""
    from agent_runtime_router import enqueue_task
    
    task = await enqueue_task(
        task_type="scout_reddit",  # or from payload
        payload={
            "subreddit": payload.get("subreddit", "entrepreneur"),
            "keywords": payload.get("keywords", []),
            "source": "n8n_scheduled"
        },
        room_id=payload.get("room_id"),
        priority=payload.get("priority", 5)
    )
    
    return {
        "success": True,
        "task_id": task.id if hasattr(task, 'id') else str(task),
        "message": f"Scheduled scout task queued from n8n"
    }


async def _handle_external_data(payload: Dict):
    """Handle data synced by n8n (e.g., Google Sheets row added)"""
    # Store in blackboard or trigger agent analysis
    return {
        "success": True,
        "message": "External data received",
        "records_processed": len(payload.get("records", []))
    }


async def _handle_user_action(payload: Dict):
    """Handle user actions from external systems (Slack button, etc.)"""
    action = payload.get("action")
    approval_id = payload.get("approval_id")
    
    if action in ["approve", "reject"] and approval_id:
        # Forward to Ledger governance
        from governance_v2 import LedgerGovernanceSystem
        
        governance = LedgerGovernanceSystem()
        decision = "APPROVED" if action == "approve" else "REJECTED"
        
        # This would actually call the governance system
        return {
            "success": True,
            "action": action,
            "approval_id": approval_id,
            "message": f"Approval {decision} via n8n"
        }
    
    return {
        "success": False,
        "message": "Unknown action or missing approval_id"
    }


# ============================================================================
# Auto-registration (from config or env)
# ============================================================================

def auto_register_from_env():
    """Auto-register n8n endpoints from environment variables"""
    import os
    
    # Format: N8N_WEBHOOK_{NAME}=url|events|secret
    # Example: N8N_WEBHOOK_SLACK=https://n8n.example.com/webhook/slack|sale_made,campaign_scaled|secret123
    
    for key, value in os.environ.items():
        if key.startswith("N8N_WEBHOOK_"):
            name = key.replace("N8N_WEBHOOK_", "").lower()
            parts = value.split("|")
            
            if len(parts) >= 2:
                url = parts[0]
                events = parts[1].split(",")
                secret = parts[2] if len(parts) > 2 else None
                
                endpoint = WebhookEndpoint(
                    name=name,
                    url=url,
                    events=events,
                    secret=secret
                )
                register_endpoint(endpoint)


# Auto-register on import
auto_register_from_env()
