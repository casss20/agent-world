# Agent World: System Design Integration

**Status**: Active design axes for runtime rollout, safety, real-time traffic, and observability  
**Last Updated**: 2025-01-15  
**Branch**: `main` (commit `1bdb39d`)

---

## 1. Requirements & Use Cases ✅

### Current State
| Use Case | Implementation | Status |
|----------|---------------|--------|
| Multi-tenant agent execution | JWT + PostgreSQL RLS | ✅ |
| Real-time room collaboration | WebSocket + Redis Pub/Sub | ✅ |
| Framework adapter routing | ExecutionEngine with feature flags | ✅ |
| Controlled rollout | Whitelist + percentage-based routing | ✅ |
| Fault-tolerant execution | Fallback to legacy on adapter failure | ✅ |
| Scalable worker plane | KEDA + Redis Streams | ✅ |
| Audit & compliance | Ledger governance + hash-chained logs | ✅ |

### Traffic Patterns
```
User Request → API Gateway → Auth Middleware → Tenant Isolation → ExecutionEngine
                                    ↓
                              WebSocket Stream ← Redis Pub/Sub ← Agent Worker
                                    ↓
                              Metrics → OpenTelemetry → Grafana
```

---

## 2. Traffic Estimation & Capacity Planning 🔄

### Current Limits (Configured)
| Resource | Limit | Location |
|----------|-------|----------|
| Max agents per crew | 3-5 | `crewai_whitelist.toml` |
| Task timeout | 60-300s | `execution_engine.py` |
| Concurrent crews per room | 2 | `crewai_whitelist.toml` |
| API rate limit | 100/min default | `governance_v2/rate_limit.py` |
| WebSocket connections | 10,000/room | `realtime_streaming.py` |

### Scaling Vectors
```python
# Horizontal Scaling (implemented)
- API tier: HPA on CPU/memory
- Worker tier: KEDA on Redis Streams pendingEntriesCount
- Redis: Cluster mode ready

# Vertical Scaling (manual)
- Worker CPU/memory limits in k8s manifests
- PostgreSQL connection pool sizing

# Bottleneck Indicators (need dashboard)
- Redis memory usage >80%
- PostgreSQL connection saturation
- Worker queue depth >100 per role
```

### Action Items
- [ ] Create capacity planning dashboard in Grafana
- [ ] Define load testing thresholds (target: 1000 concurrent rooms)
- [ ] Document scaling runbook

---

## 3. Bottleneck Identification 🔄

### Known Bottlenecks

| Component | Bottleneck | Mitigation |
|-----------|-----------|------------|
| LLM API calls | Rate limits, latency | Queue-based workers, caching, fallback |
| Redis Streams | Single stream per role | Shard by tenant_id hash |
| PostgreSQL | Connection pool exhaustion | Connection pooling (PgBouncer), RLS overhead |
| WebSocket | Memory per connection | Horizontal pod autoscaling |
| Agent execution | CPU-intensive LLM inference | GPU workers, model quantization |

### Monitoring Queries
```python
# Redis queue depth alert
redis.xlen(f"queue:{role}") > 100

# API latency P99
histogram_quantile(0.99, rate(agentworld_request_duration_seconds_bucket[5m]))

# Error rate spike
rate(agentworld_execution_engine_adapter_error_total[1m]) > 0.05
```

---

## 4. Latency & Throughput ✅

### Current Measurements

| Path | Target | Current | Location |
|------|--------|---------|----------|
| API P99 | <200ms | ~30ms | `test_ticket1_observability.py` |
| WebSocket message | <100ms | ~10ms | `realtime_streaming.py` |
| Task execution | <60s | variable | `execution_engine.py` |
| LLM response | <30s | depends on model | `agent_worker.py` |

### Throughput Targets
```yaml
API Tier:
  - 10,000 RPS (reads)
  - 1,000 RPS (writes)
  
Worker Tier:
  - Scout: 100 tasks/min
  - Maker: 50 tasks/min  
  - Merchant: 50 tasks/min
  - Governor: 20 tasks/min
```

### Optimization Strategies
1. **Non-streaming LLM**: Already chosen for reliability over latency
2. **Redis connection pooling**: Implemented in `redis.asyncio`
3. **Async database**: SQLAlchemy async sessions
4. **Batch metrics**: OpenTelemetry batch processor

---

## 5. API Design ✅

### RESTful Patterns
```
GET    /api/v1/businesses/{id}/agents      # Collection
POST   /api/v1/runtime/tasks              # Create
GET    /api/v1/execution-engine/status    # Status
POST   /api/v1/whitelist/check            # Action
```

### WebSocket Protocol
```json
{
  "type": "agent_message|blackboard_update|presence|task_update",
  "room_id": "uuid",
  "timestamp": "2025-01-15T10:30:00Z",
  "payload": {}
}
```

### Design Principles
- **Idempotency**: Event IDs for deduplication (`event_id` in webhook payload)
- **Pagination**: Cursor-based for agent lists
- **Versioning**: URL path versioning (`/api/v1/`)
- **Error format**: RFC 7807 Problem Details

---

## 6. Authentication & Authorization ✅

### Three-Layer Defense
```
┌─────────────────────────────────────────┐
│  Layer 1: Request (JWT extraction)      │  tenant_middleware.py
│  - Extract tenant_id from JWT           │
│  - Inject into request.state            │
├─────────────────────────────────────────┤
│  Layer 2: Application (Query filtering) │  tenant_db.py
│  - Auto-filter SQLAlchemy queries       │
│  - Check ownership before mutations     │
├─────────────────────────────────────────┤
│  Layer 3: Database (RLS)                │  rls_setup.py
│  - FORCE ROW LEVEL SECURITY             │
│  - Tenant-scoped policies               │
└─────────────────────────────────────────┘
```

### RBAC Model
| Role | Permissions |
|------|-------------|
| `admin` | Full access |
| `operator` | Execute, read metrics |
| `viewer` | Read-only |
| `agent` | Internal service account |

---

## 7. Rate Limiting ✅

### Implementation
```python
# governance_v2/rate_limit.py
- Token bucket algorithm
- Per-endpoint limits
- Redis-backed storage
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining
```

### Limits
| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 5 | 1 minute |
| API default | 100 | 1 minute |
| WebSocket | 1000 | 1 minute |
| Task submission | 50 | 1 minute |

---

## 8. Sync vs Async 🔄

### Current Architecture
```
┌─────────────────────────────────────────────────────────┐
│ SYNC                    ASYNC                           │
├─────────────────────────────────────────────────────────┤
│ HTTP API requests       WebSocket streaming             │
│ JWT validation          Redis Pub/Sub                   │
│ DB reads (cached)       Task queue execution            │
│ Config loading          LLM inference                   │
│ Health checks           Audit log writing               │
│ Whitelist checks        Metrics emission                │
└─────────────────────────────────────────────────────────┘
```

### Decision Matrix
| Operation | Pattern | Reason |
|-----------|---------|--------|
| Task submission | Async | Long-running, queue-based |
| Room messages | Async | Real-time broadcast |
| Auth check | Sync | Blocking, fast |
| Metrics | Async | Fire-and-forget |
| Config reload | Sync | Admin operation |

---

## 9. Idempotency ✅

### Implementation Points

| Layer | Mechanism | Location |
|-------|-----------|----------|
| Webhook receiver | `event_id` dedup in Redis | `webhook_receiver.py` |
| Task execution | Task IDempotency key | `task_queue_manager.py` |
| Blackboard ops | Event sourcing + version | `blackboard_pubsub.py` |
| Audit logs | Immutable, hash-chained | `governance_v2/audit_service.py` |

### Event ID Format
```python
f"{source}:{source_id}:{timestamp}"  # e.g., "chatdev:run_123:1699912345"
```

---

## 10. Retry Logic ✅

### Implementation
```python
# retry_controller.py
- Exponential backoff: 2^attempt * base_delay
- Jitter: randomization to prevent thundering herd
- Max attempts: 3 (default), configurable
- Error classification: retryable vs terminal

# Webhook emitter (chatdev-money)
- 3 attempts: 2s, 4s, 8s
- Dead letter queue after exhaustion
```

### Retryable Errors
- `TimeoutError`
- `ConnectionError`
- `RedisConnectionError`
- LLM rate limit (429)

### Terminal Errors
- `ValidationError`
- `PermissionDenied`
- `AgentNotFound`

---

## 11. Timeouts ✅

### Timeout Hierarchy
```python
# Layer 1: Client (30s default)
# Layer 2: API Gateway (60s)
# Layer 3: Task execution (300s default, 60s for CrewAI)
# Layer 4: LLM call (30s for OpenAI/Claude)
# Layer 5: DB query (10s)
```

### Configuration
```toml
# crewai_whitelist.toml
max_task_duration_seconds = 60

# execution_engine.py
timeout_seconds = 300  # LangGraph
```

---

## 12. Circuit Breaker ✅

### Implementation
```python
# crewai_whitelist.py
- Per-room error tracking
- Global circuit breaker
- Configurable thresholds

if error_count >= fallback_error_threshold:
    room_fallback_mode = True
    
if global_error_count >= circuit_breaker_threshold:
    global_circuit_tripped = True
```

### States
```
CLOSED  →  OPEN (after threshold)
  ↑____________↓
  (manual reset via API)
```

### API Endpoints
- `GET /api/v1/execution-engine/whitelist/status` - Check state
- `POST /api/v1/execution-engine/whitelist/reset-room/{room_id}` - Reset

---

## 13. Autoscaling ✅

### KEDA Configuration
```yaml
# k8s/keda-scalers.yaml
Scout Workers:
  minReplicas: 1
  maxReplicas: 20
  triggers:
    - type: redis-streams
      pendingEntriesCount: 10

Maker/Merchant Workers:
  minReplicas: 1
  maxReplicas: 10
  
Governor Workers:
  minReplicas: 1
  maxReplicas: 5
```

### Scale-down Stabilization
- Scout: 60s (fast scale-down for bursty traffic)
- Maker/Merchant: 300s (medium)
- Governor: 600s (slow - stateful, avoid thrashing)

---

## 14. Feature Flags ✅

### Execution Engine Routing
```python
# Environment-based
LANGGRAPH_ENABLED=true
CREWAI_ENABLED=true
LANGGRAPH_ROLLOUT_PERCENT=10

# Whitelist-based (per task/room/tenant)
CREWAI_TASK_TYPES=prototype_research,brainstorm_content
CREWAI_ROOM_TYPES=proto_*,experiment_*
CREWAI_TENANTS=internal,staging
```

### Rollout Strategy
1. **Dark launch**: 0% traffic, monitor errors
2. **Canary**: 10% traffic, internal tenants only
3. **Gradual**: Increase percentage weekly
4. **Full rollout**: 100% after validation

---

## 15. Observability ✅

### Three Pillars (OpenTelemetry)

#### Traces
```python
# telemetry.py
@traced("execute_task")
async def execute_task(...):
    # Spans: validation → routing → execution → response
```

#### Metrics
```python
# Execution engine metrics
gauge: agentworld.execution_engine.active_adapters
counter: agentworld.execution_engine.task.total
histogram: agentworld.execution_engine.task.latency
```

#### Logs (Structured JSON)
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Task completed",
  "trace_id": "abc123",
  "tenant_id": "tenant_1",
  "task_id": "task_456",
  "engine": "crewai"
}
```

### Dashboards
- **Overview**: Request rate, error rate, latency (RED metrics)
- **Execution Engine**: Tasks by engine, fallback rate
- **Workers**: Queue depth, processing rate, scale events
- **Tenant Isolation**: Cross-tenant access attempts

---

## 16. Event-Driven Architecture ✅

### Event Flow
```
User Action → API Handler → Event Bus (Redis) → Workers
                                  ↓
                           WebSocket Broadcast
                                  ↓
                           Audit Log / Metrics
```

### Event Types
| Source | Event | Handler |
|--------|-------|---------|
| Task submit | `task.created` | TaskQueueManager |
| Task claim | `task.claimed` | AgentWorker |
| Task complete | `task.completed` | ExecutionEngine |
| Blackboard update | `blackboard.set` | Room broadcast |
| Agent join | `agent.joined` | Presence update |

### Guarantees
- **At-least-once delivery**: Redis Streams with consumer groups
- **Ordering**: Per-room message ordering preserved
- **Durability**: Events persisted to PostgreSQL audit log

---

## 17. Encryption & Secrets Management 🔄

### Current State
| Layer | Implementation | Status |
|-------|---------------|--------|
| TLS in transit | Kubernetes ingress | ✅ |
| DB encryption at rest | PostgreSQL (cloud-managed) | ✅ |
| JWT signing | HS256 (shared secret) | ✅ |
| API keys | Environment variables | ⚠️ |
| LLM credentials | Environment variables | ⚠️ |

### Action Items
- [ ] HashiCorp Vault integration for secrets
- [ ] Automatic credential rotation
- [ ] Encrypt sensitive fields in DB (PII)

---

## 18. High Availability 🔄

### Current Architecture
```
┌─────────────────────────────────────────┐
│  Load Balancer (cloud)                  │
├─────────────────────────────────────────┤
│  API Pods (3 replicas, HPA)             │
├─────────────────────────────────────────┤
│  Redis Cluster (3 master, 3 replica)    │
├─────────────────────────────────────────┤
│  PostgreSQL (managed, HA)               │
├─────────────────────────────────────────┤
│  Worker Pods (KEDA autoscaled)          │
└─────────────────────────────────────────┘
```

### Failure Modes
| Failure | Impact | Mitigation |
|---------|--------|------------|
| API pod death | Request fails, retry succeeds | Kubernetes restart, HPA |
| Redis node death | Cache miss, DB fallback | Cluster failover |
| Worker pod death | Tasks requeued | KEDA restart, task reclaim |
| DB connection loss | 500 errors | Connection pool retry |
| LLM API down | Fallback to legacy engine | Circuit breaker |

### Availability Targets
- **API tier**: 99.9% (8.7h downtime/year)
- **Worker tier**: 99.5% (can tolerate short outages)
- **Data plane**: 99.99% (multi-zone replication)

---

## Immediate Next Steps

### High Priority (This Week)
1. **Capacity Dashboard**: Grafana panel for queue depths, scaling events
2. **Load Testing**: Script to simulate 1000 concurrent rooms
3. **Secrets Management**: Vault integration plan
4. **Documentation**: API reference with rate limits

### Medium Priority (Next 2 Weeks)
1. **Redis Sharding**: Shard streams by tenant_id hash
2. **Circuit Breaker UI**: Visual indicator in LedgerShell
3. **Latency SLOs**: Define and alert on P99 targets
4. **Disaster Recovery**: Runbook for region failover

### Low Priority (Later)
1. **Multi-region deployment**
2. **Read replicas for PostgreSQL**
3. **Edge caching for static assets**
4. **GraphQL API layer**

---

## References

### Implemented Components
- `backend/execution_engine.py` - Routing & feature flags
- `backend/crewai_whitelist.py` - Circuit breaker & rollout control
- `backend/realtime_streaming.py` - WebSocket handling
- `backend/telemetry.py` - OpenTelemetry metrics
- `backend/tenant_middleware.py` - Auth layer 1
- `backend/tenant_db.py` - Auth layer 2
- `backend/rls_setup.py` - Auth layer 3
- `k8s/keda-scalers.yaml` - Autoscaling
- `alert_rules.yml` - Monitoring thresholds

### Design Patterns
- [Agent system design patterns | Databricks](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns)
- [Mastering AI agent observability](https://wandb.ai/site/articles/ai-agent-observability/)
- [Four Design Patterns for Event-Driven, Multi-Agent Systems](https://www.confluent.io/blog/event-driven-multi-agent-systems/)
- [Agent Factory: Top 5 agent observability best practices](https://azure.microsoft.com/en-us/blog/agent-factory-top-5-agent-observability-best-practices-for-reliable-ai/)
