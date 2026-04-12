# Ledger 2.0 Governance API
## Production Readiness Implementation & QA Plan

**Service:** Governance Control Plane  
**Endpoints:** 30+  
**Risk Level:** HIGH (controls agent execution, kill switches, degradation)  
**Deployment Target:** Kubernetes / Container Platform  

---

## 1. Executive Summary

This governance service controls high-impact system behavior including agent execution, emergency kill switches, and system degradation. **Production readiness requires fail-safe defaults, comprehensive audit logging, and strict access controls.**

**Critical Gap Areas:**
- ❌ No authentication/authorization on control endpoints
- ❌ Single health endpoint (no live/ready separation)
- ❌ No rate limiting on sensitive operations
- ❌ Incomplete audit logging
- ❌ No circuit breakers for dependencies

**Launch Blockers:**
1. Authentication on all mutating endpoints
2. Rate limiting on /execute, /token, /killswitches/trigger
3. Proper health probe separation
4. Structured audit logging
5. Fail-closed behavior validation

---

## 2. Health Check Architecture

### Endpoint Design

```
GET /health/live     → Liveness probe (Kubernetes)
GET /health/ready    → Readiness probe (Kubernetes)  
GET /health/startup  → Startup probe (optional, for slow init)
```

### /health/live (Liveness)
**Purpose:** Is the process running?  
**Checks:**
- [ ] HTTP server responding
- [ ] Main event loop not blocked
- [ ] Memory usage < 90% limit
- [ ] No deadlock detected

**Out of Scope (DO NOT CHECK):**
- Database connectivity
- External service availability
- Disk space

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2026-04-13T01:30:00Z",
  "pid": 12345,
  "uptime_seconds": 3600
}
```

**Failure Action:** Kubernetes restarts pod

---

### /health/ready (Readiness)
**Purpose:** Can the service accept traffic?  
**Checks:**
- [ ] Governance system initialized
- [ ] Event stream writable
- [ ] Agent registry accessible
- [ ] Feature flags loaded
- [ ] Critical dependencies responsive (< 500ms)

**Readiness Definition for Governance:**
```
Ready = (
  governance_system.initialized AND
  can_write_audit_log AND
  agent_registry_responsive AND
  feature_flags_loaded AND
  NOT in_degradation_mode_critical
)
```

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2026-04-13T01:30:00Z",
  "checks": {
    "governance_engine": {"status": "pass", "latency_ms": 12},
    "event_stream": {"status": "pass", "latency_ms": 5},
    "agent_registry": {"status": "pass", "agents": 5},
    "feature_flags": {"status": "pass", "flags": 10}
  }
}
```

**Failure Action:** Kubernetes removes pod from service endpoints

---

### /health/startup (Optional)
**Purpose:** For services with slow initialization  
**Use When:** Initial feature flag loading, warming caches takes > 10s  
**Checks:** Same as ready but more lenient timeouts

---

## 3. Security Hardening Checklist

### Authentication Requirements

| Endpoint Category | Auth Required | Method |
|-------------------|---------------|--------|
| /health/* | No | Public |
| /governance/v2/flags (GET) | Optional | API Key |
| /governance/v2/classify | Yes | JWT + Service Account |
| /governance/v2/agents/* | Yes | JWT + Service Account |
| /governance/v2/execute | Yes | JWT + mTLS |
| /governance/v2/token | Yes | JWT + mTLS |
| /governance/v2/killswitches/* | Yes | JWT + Admin Role |
| /governance/v2/degradation/* | Yes | JWT + Admin Role |

### Authorization Matrix

```yaml
roles:
  agent_service:
    endpoints:
      - /execute
      - /token
      - /classify
      - POST:/agents/{id}/heartbeat
    rate_limit: 1000/min
    
  operator:
    endpoints:
      - GET:/flags/*
      - GET:/agents/*
      - GET:/events
      - GET:/status
    rate_limit: 100/min
    
  admin:
    endpoints:
      - ALL
    rate_limit: 50/min
    
  emergency_responder:
    endpoints:
      - POST:/killswitches/trigger
      - POST:/degradation/component/*
    rate_limit: 10/min
    requires_approval: second_admin
```

### Special Endpoint Handling

#### POST /execute
```yaml
authentication: JWT + mTLS certificate pinning
authorization: agent_service role only
rate_limit: 100/min per agent
audit: full request/response logged
validation:
  - capability token required
  - action in allowlist
  - business_id matches token
failure_mode: fail_closed (reject if uncertain)
```

#### POST /token
```yaml
authentication: JWT + service account
authorization: agent_service role
rate_limit: 500/min per agent
audit: all token issuances logged
validation:
  - agent_id in registry
  - requested_action permitted
  - ttl_seconds < max_allowed
failure_mode: fail_closed
```

#### POST /killswitches/trigger
```yaml
authentication: JWT + admin role
authorization: emergency_responder OR admin
rate_limit: 5/min (strict to prevent accidents)
audit: CRITICAL - log who, when, why, affected_capabilities
validation:
  - dual_approval for production
  - confirmation_token required
  - incident_id linked
alerting: immediate PagerDuty alert
failure_mode: fail_open (if kill switch fails, safest is to disable)
```

#### POST /degradation/component/{name}
```yaml
authentication: JWT + admin role
authorization: admin OR auto-governor (for self-healing)
rate_limit: 30/min
audit: log component state changes
validation:
  - component_name in allowlist
  - reason provided
alerting: alert on manual degradation changes
failure_mode: fail_safe (assume degraded if uncertain)
```

### Secure Defaults

```python
# All control endpoints require auth by default
@router.post("/execute", auth_required=True, roles=["agent_service"])

# Rate limiting on all mutating endpoints
@router.post("/token", rate_limit="500/min")

# Audit logging on all privileged operations
@router.post("/killswitches/trigger", audit_level="CRITICAL")

# Fail closed by default
default_failure_mode = "fail_closed"
```

---

## 4. Route-by-Route Test Matrix

### Core Governance Tests

| Endpoint | Success | 401 Unauthorized | 403 Forbidden | Invalid Payload | Not Found | Rate Limited | Dependency Failure |
|----------|---------|------------------|---------------|-----------------|-----------|--------------|-------------------|
| GET /health/live | 200 + alive | N/A | N/A | N/A | N/A | N/A | 200 (no deps) |
| GET /health/ready | 200 + ready | N/A | N/A | N/A | N/A | N/A | 503 if critical |
| POST /classify | 200 + risk | 401 | 403 | 400 | N/A | 429 | 503 + retry |
| GET /flags | 200 + flags | 401 (optional) | 403 | N/A | N/A | 429 | 200 (cache) |
| POST /execute | 200 + result | 401 | 403 | 400 | N/A | 429 | 503 + queue |
| POST /token | 200 + token | 401 | 403 | 400 | N/A | 429 | 503 + deny |
| POST /flags/{cap}/kill | 200 + killed | 401 | 403 | 400 | 404 | 429 | 503 + alert |

### Orchestration Tests

| Endpoint | Success | 401 | 403 | Invalid | Not Found | Rate Limited | Dependency Failure |
|----------|---------|-----|-----|---------|-----------|--------------|-------------------|
| POST /agents/register | 201 + agent | 401 | 403 | 400 | N/A | 429 | 503 + queue |
| GET /agents | 200 + list | 401 | 403 | N/A | N/A | 429 | 200 (cache) |
| POST /agents/{id}/heartbeat | 200 + ack | 401 | 403 (wrong agent) | 400 | 404 | 429 | 202 (queued) |
| GET /agents/{id}/health | 200 + health | 401 | 403 | N/A | 404 | 429 | 503 + stale |
| POST /tasks/submit | 201 + task_id | 401 | 403 | 400 | N/A | 429 | 503 + queue |
| GET /tasks/queue | 200 + status | 401 | 403 | N/A | N/A | 429 | 503 + cached |
| GET /businesses/{id}/health | 200 + health | 401 | 403 (wrong biz) | N/A | 404 | 429 | 503 + stale |

### Memory & Audit Tests

| Endpoint | Success | 401 | 403 | Invalid | Not Found | Rate Limited | Dependency Failure |
|----------|---------|-----|-----|---------|-----------|--------------|-------------------|
| GET /events | 200 + events | 401 | 403 | N/A | N/A | 429 | 503 + retry |
| POST /consolidate | 202 + started | 401 | 403 | N/A | N/A | 429 | 503 + queued |
| GET /consolidate/status | 200 + status | 401 | 403 | N/A | N/A | 429 | 200 (cache) |

### Hardening & Control Tests

| Endpoint | Success | 401 | 403 | Invalid | Not Found | Rate Limited | Dependency Failure |
|----------|---------|-----|-----|---------|-----------|--------------|-------------------|
| GET /degradation/status | 200 + status | 401 | 403 | N/A | N/A | 429 | 200 (local) |
| POST /degradation/component/{name} | 200 + updated | 401 | 403 | 400 | 404 | 429 | 202 (queued) |
| GET /killswitches | 200 + switches | 401 | 403 | N/A | N/A | 429 | 200 (local) |
| POST /killswitches/trigger | 200 + triggered | 401 | 403 | 400 | 404 | 429 | 503 + alert |
| POST /killswitches/{name}/reset | 200 + reset | 401 | 403 | 400 | 404 | 429 | 503 + alert |

---

## 5. Observability Requirements

### Structured Logging (JSON)

**Every Request:**
```json
{
  "timestamp": "2026-04-13T01:30:00.123Z",
  "level": "INFO",
  "request_id": "req_abc123",
  "trace_id": "trace_xyz789",
  "span_id": "span_123",
  "method": "POST",
  "path": "/governance/v2/execute",
  "status_code": 200,
  "latency_ms": 45,
  "user_agent": "agent-service/1.0",
  "client_ip": "10.0.1.23",
  "auth": {
    "subject": "agent:test_scout_001",
    "roles": ["agent_service"]
  }
}
```

**Governance Decision Logs:**
```json
{
  "timestamp": "2026-04-13T01:30:00.123Z",
  "level": "INFO",
  "event_type": "governance_decision",
  "trace_id": "trace_xyz789",
  "decision_id": "dec_abc123",
  "agent_id": "test_scout_001",
  "business_id": 1,
  "action": "execute",
  "resource": "workflow:123",
  "decision": "approved",
  "risk_level": "medium",
  "constitution_rules_applied": ["external_action_guardrail"],
  "latency_ms": 12,
  "token_issued": "tok_xxx",
  "token_expiry": "2026-04-13T02:30:00Z"
}
```

**Security Events:**
```json
{
  "timestamp": "2026-04-13T01:30:00.123Z",
  "level": "WARN",
  "event_type": "security_event",
  "subtype": "rate_limit_exceeded",
  "trace_id": "trace_xyz789",
  "subject": "agent:test_scout_001",
  "endpoint": "/governance/v2/execute",
  "limit": "100/min",
  "current": 105,
  "action_taken": "throttled"
}
```

### Metrics

**Request Metrics:**
```
governance_requests_total{method, endpoint, status}
governance_request_duration_seconds{method, endpoint, quantile}
governance_requests_in_flight{endpoint}
```

**Governance Metrics:**
```
governance_decisions_total{decision, risk_level}
governance_tokens_issued_total{agent_type}
governance_tokens_revoked_total{reason}
governance_kill_switches_triggered_total{switch_name}
governance_degradation_level{level}
```

**Dependency Metrics:**
```
governance_dependency_health{name, status}
governance_dependency_latency_seconds{name}
governance_circuit_breaker_state{name}
```

### Alerting Triggers

**P1 (Page Immediately):**
- Kill switch triggered
- Degradation level = critical
- /health/ready failing for > 30s
- Error rate > 10% for 2 minutes
- Dependency down for > 60s

**P2 (Alert within 15 min):**
- Error rate > 5% for 5 minutes
- Latency p99 > 1s for 5 minutes
- Rate limiting triggered > 100/min
- Memory consolidation failing

**P3 (Log/Monitor):**
- Any 401/403 response
- Slow governance decisions (> 500ms)
- Token issuance spikes

### Tracing

**Trace Context Propagation:**
- Extract trace_id from incoming headers (W3C traceparent)
- Create span for each governance decision
- Propagate to all downstream calls

**Span Names:**
- `governance.execute`
- `governance.token.issue`
- `governance.classify`
- `governance.kill_switch.trigger`

---

## 6. Failure Handling Rules

### Fail-Closed vs Fail-Safe Matrix

| Scenario | Behavior | Response | Logging | Alert |
|----------|----------|----------|---------|-------|
| **Governance engine uninitialized** | Fail closed | 503 + retry-after | ERROR | P1 |
| **Audit log unavailable** | Degrade (continue) | 200 + warning | WARN | P2 |
| **Registry unavailable** | Fail closed | 503 + retry-after | ERROR | P1 |
| **Queue unavailable** | Fail closed | 503 + retry-after | ERROR | P1 |
| **Rate limit exceeded** | Throttle | 429 + retry-after | WARN | P2 |
| **Partial subsystem outage** | Degrade gracefully | 200 + degraded flag | WARN | P2 |
| **Memory consolidation failing** | Degrade (skip) | 202 (queued) | WARN | P2 |
| **Feature flags stale** | Use cached + warn | 200 + stale flag | WARN | P3 |

### Dependency Failure Specifics

**Memory/Audit Storage Unavailable:**
- Continue operating (fail-safe)
- Buffer events in memory (max 1000)
- Alert P2
- If buffer full, drop oldest + log

**Governance Engine Not Initialized:**
- Fail closed (503)
- All control endpoints reject
- /health/ready returns false
- Alert P1

**Registry Unavailable:**
- Fail closed for new registrations
- Allow heartbeats (update cache)
- Allow queries from cache (max 60s stale)
- Alert P1

**Queue Unavailable:**
- Fail closed for new tasks
- Queue in memory (max 100)
- Alert P2
- If memory full, reject with 503

---

## 7. Deployment Readiness Checklist

### Infrastructure
- [ ] Kubernetes deployment manifests
- [ ] Service definition with proper ports
- [ ] Ingress with TLS termination
- [ ] Horizontal Pod Autoscaler (HPA)
- [ ] Pod Disruption Budget (PDB)
- [ ] Resource limits (CPU/Memory)
- [ ] Network policies

### Security
- [ ] TLS certificates configured
- [ ] Secrets in vault/Kubernetes secrets
- [ ] Service account with minimal permissions
- [ ] Network policies restrict traffic
- [ ] Pod security context (non-root)
- [ ] Container image scanned
- [ ] No secrets in environment variables

### Configuration
- [ ] Feature flags configured for production
- [ ] Rate limits set appropriately
- [ ] Audit log destination configured
- [ ] Alerting endpoints configured
- [ ] Health check paths configured in k8s

### Validation
- [ ] Smoke tests pass
- [ ] Load tests pass (target: 500 req/s)
- [ ] Security scan pass
- [ ] Penetration test (optional)
- [ ] Chaos engineering test (kill pod)

### Rollout
- [ ] Staging validation complete
- [ ] Canary deployment plan (5% → 25% → 100%)
- [ ] Rollback plan documented
- [ ] On-call engineer assigned
- [ ] Runbook created

---

## 8. 7-Day Priority Plan

### Day 1: Health & Readiness
**Actions:**
1. Implement /health/live and /health/ready endpoints
2. Configure Kubernetes probes
3. Add readiness dependency checks

**Risk Reduction:** Prevents traffic to unhealthy pods, reduces downtime  
**Validation:** kubectl describe pod shows Ready=True, probes passing

---

### Day 2: Authentication
**Actions:**
1. Add JWT middleware to all mutating endpoints
2. Implement service account validation
3. Add mTLS for /execute and /token

**Risk Reduction:** Prevents unauthorized control plane access  
**Validation:** curl without token returns 401, with token returns 200

---

### Day 3: Authorization & Rate Limiting
**Actions:**
1. Implement role-based access control
2. Add rate limiting middleware (Redis-backed)
3. Configure limits per endpoint tier

**Risk Reduction:** Prevents abuse, ensures fair resource usage  
**Validation:** Bursty requests get 429, different roles get different access

---

### Day 4: Audit Logging
**Actions:**
1. Add structured JSON logging
2. Implement governance decision logging
3. Ship logs to SIEM/Splunk

**Risk Reduction:** Enables incident investigation, compliance requirements  
**Validation:** All governance decisions appear in logs with trace IDs

---

### Day 5: Failure Handling
**Actions:**
1. Implement circuit breakers for dependencies
2. Add fallback behaviors
3. Test each failure scenario

**Risk Reduction:** Service degrades gracefully instead of failing hard  
**Validation:** Kill dependency pods, verify service continues operating

---

### Day 6: Observability
**Actions:**
1. Add Prometheus metrics endpoint
2. Configure Grafana dashboards
3. Set up PagerDuty alerts

**Risk Reduction:** Detect issues before they impact users  
**Validation:** Alerts fire when error rate increases

---

### Day 7: Integration Testing
**Actions:**
1. Run full test matrix
2. Load test (500 req/s)
3. Chaos test (kill pods randomly)

**Risk Reduction:** Validate production readiness  
**Validation:** 99.9% success rate under load, auto-recovery from failures

---

## 9. Endpoint Risk Tiers

### Tier 1: Highest Risk (Launch Blockers)
**Endpoints:**
- `POST /governance/v2/execute` - Executes arbitrary actions
- `POST /governance/v2/token` - Issues capability tokens
- `POST /governance/v2/killswitches/trigger` - Emergency shutdown
- `POST /governance/v2/degradation/component/{name}` - System degradation

**Why:** Direct system control, high blast radius, irreversible actions  
**Controls Required:**
- JWT + mTLS auth
- Strict rate limiting (10-100/min)
- Full audit logging
- Admin role required
- Dual approval for production

---

### Tier 2: Medium Risk
**Endpoints:**
- `POST /governance/v2/agents/register` - Agent registration
- `POST /governance/v2/tasks/submit` - Task submission
- `POST /governance/v2/consolidate` - Memory consolidation
- `POST /governance/v2/classify` - Risk classification

**Why:** Important operations but reversible/auditable  
**Controls Required:**
- JWT auth
- Service account role
- Moderate rate limiting (500/min)
- Decision logging

---

### Tier 3: Lower Risk
**Endpoints:**
- `GET /health/*` - Health checks
- `GET /governance/v2/flags` - Feature flags
- `GET /governance/v2/agents` - Agent listing
- `GET /governance/v2/events` - Event queries
- `GET /governance/v2/status` - System status
- `POST /agents/{id}/heartbeat` - Heartbeats

**Why:** Read-only or low-impact operations  
**Controls Required:**
- Optional auth (public for health)
- Standard rate limiting
- Access logging

---

## 10. Final Recommendation

**DO NOT LAUNCH** the governance service to production without:

1. ✅ Authentication on all Tier 1 endpoints
2. ✅ Rate limiting on /execute, /token, /killswitches/trigger
3. ✅ Proper health/ready probe separation
4. ✅ Structured audit logging to SIEM
5. ✅ Fail-closed behavior validation

**Estimated Time to Production Ready:** 7 days (see priority plan)

**Immediate Next Steps:**
1. Implement health endpoints (Day 1)
2. Add JWT middleware (Day 2)
3. Run security review

**Risk Assessment:**
- Current: HIGH (no auth, no rate limiting)
- After Week 1: LOW (proper controls in place)

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-13  
**Owner:** Backend Reliability Team  
