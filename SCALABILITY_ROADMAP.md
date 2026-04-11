# AgentVerse Scalability Roadmap
## 5 Critical Changes for 100+ Concurrent Workflows

**Date:** April 12, 2026  
**Source:** Expert synthesis from architecture review  
**Status:** Week 1 implementation in progress

---

## 🚨 IMMEDIATE (Week 1)

### 1. Fix Adapter Polling (Highest Risk)

**Current State:**
- Single HTTP client instance
- 5-second polling intervals
- Individual SQLite writes per event
- Synchronous Redis publishes

**Changes Required:**

```python
# NEW: Connection pooling + batching
adapter = GuardedAdapter(
    pool_size=20,              # HTTP connection pool
    batch_writes=True,         # 100ms buffer for audit writes
    pipeline_events=True,      # Redis pipeline for events
    max_concurrent_polls=50    # Limit concurrent polling loops
)
```

**Implementation:**
- [ ] Add `httpx.AsyncClient` with connection pooling
- [ ] Add `BufferedAuditWriter` for batch SQLite writes
- [ ] Add `RedisPipeline` for batched event publishing
- [ ] Add semaphore for concurrent polling limit

**Files to modify:**
- `guarded_adapter.py`
- `chatdev_client.py`
- `audit_guardrails.py`

---

### 2. Add Monitoring Dashboard

**8 Critical Metrics with Alerts:**

| Metric | Warning | Critical | Alert Channel |
|--------|---------|----------|---------------|
| Adapter P99 latency | >500ms | >2s | PagerDuty |
| Redis memory usage | >70% | >85% | Slack |
| PostgreSQL connections | >80% pool | 100% | PagerDuty |
| Event loop lag | >100ms | >500ms | Slack |
| Fallback activation rate | >5% | >20% | PagerDuty |
| Workflow error rate | >2% | >10% | Slack |
| Cost per successful run | >$0.50 | >$1.00 | Email |
| Manual intervention rate | >1% | >5% | Slack |

**Implementation:**
- [ ] Add Prometheus metrics endpoint
- [ ] Create Grafana dashboard JSON
- [ ] Configure alert rules
- [ ] Add health check endpoint with all metrics

**Files to create:**
- `metrics.py` - Prometheus instrumentation
- `dashboard.json` - Grafana dashboard
- `alerts.yml` - AlertManager rules

---

## 📈 PHASE 2 (Month 1)

### 3. Replace Polling → Webhooks

**Architecture Change:**

```
CURRENT (Polling):
AgentVerse ──poll 5s──→ ChatDev Money
   ↑                      │
   └────status check──────┘

NEW (Webhooks):
AgentVerse ←──webhook─── ChatDev Money
   │                      │
   └── ACK + route ───────┘
```

**Benefits:**
- Eliminates 5s polling overhead
- Near real-time event delivery
- Scales to 1000+ workflows

**Implementation:**
- [ ] Add webhook endpoint to AgentVerse: `/webhooks/chatdev/events`
- [ ] Configure ChatDev Money to emit webhooks
- [ ] Add webhook signature verification
- [ ] Implement idempotency for duplicate events
- [ ] Add webhook retry with exponential backoff

**Files to modify:**
- `guarded_adapter.py` - Add webhook handler
- `main_v2.py` - Register webhook routes
- `chatdev_client.py` - Configure webhooks

---

### 4. Add Intervention Points

**4 Critical Interception Points:**

| Point | Purpose | Implementation |
|-------|---------|----------------|
| Task handoff | Route between agents | Middleware in workflow adapter |
| Budget enforcement | Token/cost limits | Pre-execution check |
| Human approval | Gate sensitive actions | Pause workflow, notify UI |
| Cross-workflow state | Share context | Shared Redis cache |

**Example: Budget Enforcement:**

```python
async def execute_with_budget(run_id: str, budget: Budget):
    if budget.remaining < estimated_cost:
        await pause_workflow(run_id, reason="budget_exceeded")
        notify_user("Workflow paused: budget limit reached")
        return
    
    await execute_workflow(run_id)
    budget.deduct(actual_cost)
```

**Files to create:**
- `intervention_middleware.py`
- `budget_enforcer.py`
- `approval_gates.py`

---

### 5. Roadmap Cleanup Dates

| Milestone | Date | Deliverable |
|-----------|------|-------------|
| Delete ChatDev Scout | Month 6 | Native Scout runtime |
| Delete remaining ChatDev | Month 9 | All workflows native |
| Full ChatDev decommission | Month 12 | Zero ChatDev dependencies |

**Success Criteria:**
- [ ] All workflows run on native runtime
- [ ] Zero ChatDev API calls
- [ ] All data migrated to PostgreSQL
- [ ] Documentation updated

---

## ✅ What NOT to Change

These are validated and should remain:

| Component | Status | Reason |
|-----------|--------|--------|
| Control plane / execution plane separation | ✅ Keep | Industry best practice |
| Room-scoped events | ✅ Keep | Clean isolation model |
| Guarded adapters | ✅ Keep | Production safety |
| Strangler pattern | ✅ Keep | Proven migration strategy |
| PostgreSQL as source of truth | ✅ Keep | ACID guarantees |

---

## Implementation Priority

```
Week 1 (NOW):
├── 1. Connection pooling (blocks scale)
├── 2. Monitoring dashboard (measure everything)
└── Setup webhook infrastructure

Month 1:
├── 3. Webhook events (eliminate polling)
├── 4. Intervention points (platform value)
└── Performance testing at 100 workflows

Month 2-3:
├── Native Scout runtime
├── Migration tooling
└── Gradual ChatDev extraction

Month 6-12:
├── Complete ChatDev removal
└── Full decommission
```

---

## Key Metrics to Track

**Before Changes (Baseline):**
- Adapter P99 latency: ~200ms
- Max concurrent workflows: ~20
- CPU usage at 20 workflows: ~40%
- Memory usage: ~500MB

**After Week 1 Changes (Target):**
- Adapter P99 latency: <100ms
- Max concurrent workflows: ~50
- CPU usage at 50 workflows: ~50%
- Memory usage: ~800MB

**After Month 1 Changes (Target):**
- Adapter P99 latency: <50ms
- Max concurrent workflows: 100+
- CPU usage at 100 workflows: ~60%
- Event delivery: Real-time (no polling delay)

---

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Webhook delivery failures | Medium | Retry + fallback to polling |
| Batch write data loss | Low | 100ms flush + WAL |
| Connection pool exhaustion | Low | Max 50 concurrent + queue |
| Monitoring overhead | Low | Async metrics collection |

---

## Notes

- No rewrite needed — evolutionary improvements only
- Each change is independently deployable
- Fallback to current behavior always available
- Monitor before and after each change

**Next Action:** Implement Week 1 changes (connection pooling + monitoring)
