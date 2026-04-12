# Phase 2: Production Readiness Tickets

**Status:** Ready for implementation  
**Estimated Duration:** 2-3 weeks (parallelizable)  
**Goal:** Webhooks + real execution + stateless scaling + validated SLA

---

## Ticket 1: Webhook Receiver Endpoint

**Priority:** P0  
**Assignee:** TBD  
**Estimated:** 2 days  
**Depends on:** None

### Description
Build HTTP webhook receiver endpoint for ChatDev Money to push status/events instead of polling.

### File Changes

| File | Change |
|------|--------|
| `backend/webhook_receiver.py` | **NEW** - FastAPI router for webhook endpoints |
| `backend/models_webhook.py` | **NEW** - Pydantic models for webhook payloads |
| `backend/guarded_adapter.py` | Register webhook routes, add event processor |
| `backend/hybrid_adapter.py` | Add `register_webhook()` method to engines |
| `backend/room_engine_bindings.py` | Route events to room WebSockets |

### Implementation Details

```python
# backend/webhook_receiver.py
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal
import hmac
import hashlib

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class WorkflowEvent(BaseModel):
    event_type: Literal["workflow.started", "step.completed", "workflow.completed", "workflow.failed"]
    run_id: str
    room_id: str
    timestamp: str
    payload: Dict[str, Any]
    
    # Signature for verification
    signature: str = Field(..., description="HMAC-SHA256 signature")

@router.post("/chatdev/events")
async def receive_chatdev_event(
    event: WorkflowEvent,
    request: Request
):
    """Receive events from ChatDev Money"""
    # Verify signature
    verify_webhook_signature(event)
    
    # Process event
    await process_workflow_event(event)
    
    return {"status": "received"}

async def verify_webhook_signature(event: WorkflowEvent):
    """Verify HMAC signature from ChatDev Money"""
    secret = get_webhook_secret()
    expected = hmac.new(
        secret.encode(),
        f"{event.run_id}:{event.timestamp}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(event.signature, expected):
        raise HTTPException(401, "Invalid signature")
```

### Acceptance Criteria

- [ ] POST `/webhooks/chatdev/events` accepts and validates events
- [ ] HMAC-SHA256 signature verification working
- [ ] Events route to correct room via WebSocket
- [ ] Duplicate event detection (idempotency key)
- [ ] 200ms P99 processing time per event
- [ ] Unit tests: signature validation, event routing, duplicates

### Dependencies
None (foundational)

---

## Ticket 2: ChatDev Money Webhook Emitter

**Priority:** P0  
**Assignee:** TBD  
**Estimated:** 1 day  
**Depends on:** Ticket 1

### Description
Add webhook emission to ChatDev Money workflow execution.

### File Changes

| File | Change |
|------|--------|
| `chatdev-money/server/webhook_emitter.py` | **NEW** - Webhook delivery logic |
| `chatdev-money/server/models.py` | Add `webhook_url` to session model |
| `chatdev-money/yaml_instance/content_arbitrage_v1.yaml` | Add webhook registration step |
| `chatdev-money/.env.example` | Add `WEBHOOK_SECRET` |

### Implementation Details

```python
# chatdev-money/server/webhook_emitter.py
import httpx
import hmac
import hashlib
from datetime import datetime, timezone

class WebhookEmitter:
    def __init__(self, webhook_url: str, secret: str):
        self.webhook_url = webhook_url
        self.secret = secret
        self._client = httpx.AsyncClient(timeout=10.0)
    
    async def emit(self, event_type: str, run_id: str, room_id: str, payload: dict):
        """Emit event to registered webhook"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Create signature
        signature = hmac.new(
            self.secret.encode(),
            f"{run_id}:{timestamp}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        event = {
            "event_type": event_type,
            "run_id": run_id,
            "room_id": room_id,
            "timestamp": timestamp,
            "payload": payload,
            "signature": signature
        }
        
        # Send with retry
        for attempt in range(3):
            try:
                response = await self._client.post(
                    self.webhook_url,
                    json=event,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    return True
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        
        # Log failed delivery for retry later
        await self._queue_for_retry(event)
        return False
```

### Acceptance Criteria

- [ ] ChatDev Money emits events at workflow start/complete/step
- [ ] HMAC signatures generated correctly
- [ ] Retry with exponential backoff on failure
- [ ] Failed events queued for later retry
- [ ] Webhook URL configurable per workflow/session

### Dependencies
Ticket 1 (needs receiver endpoint to test against)

---

## Ticket 3: Webhook Integration Test

**Priority:** P1  
**Assignee:** TBD  
**Estimated:** 1 day  
**Depends on:** Tickets 1, 2

### Description
End-to-end test of webhook flow from ChatDev Money to AgentVerse.

### File Changes

| File | Change |
|------|--------|
| `backend/test_webhook_integration.py` | **NEW** - Integration test suite |

### Test Scenarios

```python
# Test cases
async def test_webhook_delivery():
    """Full flow: ChatDev emits → AgentVerse receives → Room updated"""
    
async def test_signature_validation():
    """Invalid signatures rejected"""
    
async def test_duplicate_events():
    """Same event_id processed once only"""
    
async def test_retry_mechanism():
    """Failed deliveries retried with backoff"""
    
async def test_latency_under_load():
    """100 events/sec, P99 <200ms processing"""
```

### Acceptance Criteria

- [ ] 100% event delivery success (with retries)
- [ ] P99 latency <200ms (processing time)
- [ ] Zero duplicate processing
- [ ] Failed events recoverable

### Dependencies
Tickets 1, 2

---

## Ticket 4: OpenAI API Integration

**Priority:** P0  
**Assignee:** TBD  
**Estimated:** 1 day  
**Depends on:** None (parallel with webhooks)

### Description
Configure and verify real OpenAI-backed execution in ChatDev Money.

### File Changes

| File | Change |
|------|--------|
| `chatdev-money/.env` | **NEW** (gitignored) - Real API credentials |
| `chatdev-money/.env.example` | Update with instructions |
| `chatdev-money/README_DEPLOYMENT.md` | **NEW** - Deployment guide |

### Setup Steps

```bash
# 1. Set credentials
export BASE_URL=https://api.openai.com/v1
export API_KEY=sk-...

# 2. Verify one real run
python3 -c "
import requests
resp = requests.post(
    'http://localhost:6400/api/workflow/execute',
    json={
        'yaml_file': 'content_arbitrage_v1.yaml',
        'task_prompt': 'Test real execution',
        'variables': {'subreddit': 'sidehustle'}
    }
)
print(resp.json())
"

# 3. Check output quality
# 4. Verify latency (should be 10-30s for full workflow)
```

### Acceptance Criteria

- [ ] One complete real workflow execution
- [ ] Output quality acceptable (human review)
- [ ] Latency baseline established (10-30s expected)
- [ ] Cost per run documented (~$0.05-0.20)
- [ ] API error handling verified (rate limits, etc.)

### Dependencies
None

---

## Ticket 5: Stateless Adapter Refactor

**Priority:** P1  
**Assignee:** TBD  
**Estimated:** 3 days  
**Depends on:** Ticket 3 (webhooks stable)

### Description
Remove instance-local state from adapter to enable horizontal scaling.

### File Changes

| File | Change |
|------|--------|
| `backend/stateless_adapter.py` | **NEW** - Refactored stateless adapter |
| `backend/shared_state.py` | **NEW** - Redis-backed state store |
| `backend/guarded_adapter.py` | Replace local state with Redis |
| `docker-compose.yml` | Add Redis, nginx load balancer |

### Current (Stateful)

```python
# Problem: Local in-memory state
class GuardedAdapter:
    def __init__(self):
        self._circuit_breakers = {}  # ❌ Instance-local
        self._active_polls = {}      # ❌ Instance-local
        self._metrics = MetricCollector()  # ❌ Instance-local
```

### Target (Stateless)

```python
# Solution: Redis-backed state
class StatelessAdapter:
    def __init__(self):
        self._redis = RedisClient()
        self._state = SharedState(redis=self._redis)
    
    async def launch_workflow(self, request):
        # Check circuit breaker in Redis
        if await self._state.circuit_breaker.is_open("workflow_launch"):
            raise CircuitBreakerOpen()
        
        # Record in shared state
        await self._state.runs.create(run_id, request)
        
        # Any instance can pick this up
```

### State Migration

| Current (Local) | New (Redis) |
|-----------------|-------------|
| `_circuit_breakers` | `redis:hset:circuit_breakers:{name}` |
| `_active_polls` | `redis:set:active_polls:{run_id}` |
| `_metrics` | Redis TimeSeries or Prometheus |
| `_audit_buffer` | Redis Streams |

### Acceptance Criteria

- [ ] Two adapter instances run behind nginx
- [ ] Circuit breaker state shared across instances
- [ ] Metrics aggregated correctly
- [ ] No data loss during instance restart
- [ ] Load balanced (round-robin) requests

### Dependencies
Ticket 3 (webhooks must be stable first)

---

## Ticket 6: Multi-Instance Load Balancer

**Priority:** P2  
**Assignee:** TBD  
**Estimated:** 1 day  
**Depends on:** Ticket 5

### Description
Deploy multiple adapter instances with nginx load balancing.

### File Changes

| File | Change |
|------|--------|
| `docker-compose.yml` | Add nginx, scale adapter to 3 replicas |
| `nginx.conf` | **NEW** - Load balancer config |
| `backend/health_check.py` | **NEW** - Deep health check for LB |

### nginx Configuration

```nginx
upstream adapter_cluster {
    least_conn;  # Least connections
    server adapter_1:8003;
    server adapter_2:8003;
    server adapter_3:8003;
    
    keepalive 32;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://adapter_cluster;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    location /health {
        # Health checks don't count toward load balancing
        proxy_pass http://adapter_cluster/health;
    }
}
```

### Acceptance Criteria

- [ ] 3 adapter instances running
- [ ] nginx load balancing requests
- [ ] Health checks route to healthy instances only
- [ ] Rolling restart (zero downtime deploy)
- [ ] Connection pooling maintained

### Dependencies
Ticket 5

---

## Ticket 7: Final Production Load Test

**Priority:** P0  
**Assignee:** TBD  
**Estimated:** 2 days  
**Depends on:** Tickets 3, 4, 6

### Description
Sustained load test with webhooks + real LLM + multi-instance setup.

### File Changes

| File | Change |
|------|--------|
| `backend/load_test_production.py` | **NEW** - Production-grade test suite |

### Test Configuration

```python
# Production load test config
CONFIG = {
    "target_workflows": 100,
    "duration_minutes": 30,  # Sustained
    "webhook_mode": True,    # No polling
    "real_llm": True,        # Real OpenAI
    "instances": 3,          # Multi-instance
    
    "sla": {
        "p95_ms": 35000,     # 35s (real LLM takes time)
        "p99_ms": 45000,     # 45s
        "error_rate": 0.001, # 0.1% (enterprise standard)
        "cost_per_run_usd": 0.20
    }
}
```

### Test Phases

1. **Baseline** (10 workflows)
   - Verify end-to-end with real LLM
   - Establish latency baseline

2. **Ramp** (10 → 25 → 50 → 100)
   - 10 minutes per level
   - Monitor for degradation

3. **Sustained** (100 workflows, 30 minutes)
   - Real SLA validation
   - Cost tracking
   - Error rate monitoring

4. **Spike** (150 workflows)
   - Find breaking point
   - Verify graceful degradation

### Acceptance Criteria

- [ ] 100 workflows sustained for 30 minutes
- [ ] p95 latency <35s (adjusted for real LLM)
- [ ] **Error rate <0.1%** (enterprise standard)
- [ ] Cost per run <$0.20
- [ ] No memory leaks (stable over 30min)
- [ ] Recovery from instance failure <30s

### Dependencies
Tickets 3 (webhooks), 4 (real LLM), 6 (multi-instance)

---

## Ticket 8: Phase 2 Documentation

**Priority:** P1  
**Assignee:** TBD  
**Estimated:** 1 day  
**Depends on:** Ticket 7

### Description
Document Phase 2 architecture and deployment procedures.

### File Changes

| File | Change |
|------|--------|
| `PHASE2_COMPLETE.md` | **NEW** - Summary of Phase 2 work |
| `DEPLOYMENT_GUIDE.md` | **NEW** - Production deployment steps |
| `ARCHITECTURE_v2.md` | **NEW** - Updated architecture diagrams |
| `RUNBOOK.md` | **NEW** - Incident response procedures |

### Acceptance Criteria

- [ ] Architecture diagrams updated
- [ ] Deployment steps verified (dry-run)
- [ ] Incident response procedures documented
- [ ] Performance benchmarks recorded
- [ ] Cost estimates documented

### Dependencies
Ticket 7

---

## Dependency Graph

```
Ticket 1 (Webhook Receiver) ─────┐
                                 ├──→ Ticket 3 (Integration Test)
Ticket 2 (Webhook Emitter) ──────┘
                                 
Ticket 4 (OpenAI Integration) ───┐
                                 ├──→ Ticket 7 (Final Load Test)
Ticket 3 ────────────────────────┤
                                 │
Ticket 5 (Stateless Refactor) ───┼──→ Ticket 6 (Load Balancer) ───┘
```

---

## Execution Order

| Week | Tickets | Deliverable |
|------|---------|-------------|
| 1 | 1, 2, 3, 4 | Webhooks working + real LLM verified |
| 2 | 5, 6 | Stateless adapter + multi-instance |
| 3 | 7, 8 | Production load test + documentation |

---

## Success Criteria (Phase 2 Gate)

✅ **All of the following must pass:**

1. Webhook event delivery <200ms P99
2. Real LLM execution verified (one complete run)
3. 3 adapter instances load balanced
4. 100 workflows sustained for 30 minutes
5. p95 latency <35s (real LLM adjusted)
6. **Error rate <0.1%** (enterprise standard)
7. Zero data loss during instance restart
8. Documentation complete

**Then we claim:**
> "The architecture remains the same, but transport is now push-based, execution is real, scaling is horizontal, and SLA claims are backed by sustained load data."
