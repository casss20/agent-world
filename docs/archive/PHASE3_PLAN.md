# Phase 3: Operational Maturity Plan
**Production Readiness — Observability, Security, CI/CD, Recovery**

---

## Goal
Transform the platform from "works under load" to "safely operable in production" with full visibility, automated response, and secure deployment practices.

---

## Tickets

### Ticket 1: Observability Stack
**Priority: P0** — Can't operate what you can't see

**Deliverables:**
- [ ] Prometheus metrics endpoint (`/metrics`)
- [ ] Key metrics:
  - Request rate, latency (p50/p95/p99)
  - Error rate by endpoint
  - Active workflow count
  - Redis connection health
  - Instance resource usage (CPU, memory)
- [ ] Grafana dashboard (JSON export)
- [ ] Distributed tracing (OpenTelemetry)

**Files:**
- `backend/metrics_exporter.py`
- `backend/tracing_middleware.py`
- `grafana/dashboard.json`

---

### Ticket 2: Alerting
**Priority: P0** — Detect problems before users do

**Deliverables:**
- [ ] AlertManager configuration
- [ ] Alert rules:
  - Health check failure > 1 min
  - P95 latency > 1s for 5 min
  - Error rate > 1% for 2 min
  - Redis disconnected
  - Circuit breaker opened
  - Instance down
- [ ] Notification channels (webhook, email)
- [ ] Alert runbook (response procedures)

**Files:**
- `alerting/prometheus-rules.yml`
- `alerting/alertmanager.yml`
- `alerting/RUNBOOK.md`

---

### Ticket 3: Security Hardening
**Priority: P0** — Protect production data and access

**Deliverables:**
- [ ] API authentication (JWT tokens)
- [ ] Rate limiting (per user, per IP)
- [ ] Input validation/sanitization
- [ ] Secrets management (HashiCorp Vault or AWS Secrets Manager)
- [ ] Security headers (CSP, HSTS, X-Frame-Options)
- [ ] Vulnerability scanning (dependency check)

**Files:**
- `backend/auth_middleware.py`
- `backend/rate_limiter.py`
- `backend/security_headers.py`
- `security/SECURITY_CHECKLIST.md`

---

### Ticket 4: CI/CD with Rollback
**Priority: P1** — Safe, repeatable deployments

**Deliverables:**
- [ ] GitHub Actions workflow
- [ ] Build pipeline (lint, test, build Docker)
- [ ] Staging deployment
- [ ] Production deployment (blue-green or canary)
- [ ] Automated rollback on health check failure
- [ ] Smoke tests post-deploy

**Files:**
- `.github/workflows/deploy.yml`
- `scripts/deploy.sh`
- `scripts/rollback.sh`
- `scripts/smoke_test.sh`

---

### Ticket 5: Disaster Recovery
**Priority: P1** — Recover from failures

**Deliverables:**
- [ ] Redis backup strategy (RDB + AOF)
- [ ] Automated backups (hourly snapshots)
- [ ] Recovery procedure documentation
- [ ] Recovery time objective (RTO): < 15 min
- [ ] Recovery point objective (RPO): < 1 hour
- [ ] DR drill runbook

**Files:**
- `scripts/backup_redis.sh`
- `scripts/restore_redis.sh`
- `disaster-recovery/RUNBOOK.md`
- `disaster-recovery/DR_TEST.md`

---

## SLOs (Service Level Objectives)

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Availability | 99.9% | < 99% triggers page |
| P95 Latency | < 500ms | > 1s for 5 min |
| Error Rate | < 0.1% | > 1% for 2 min |
| Workflow Success Rate | > 99% | < 95% |

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Nginx :8080│────▶│  Adapter    │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                    │
                    ┌──────┴──────┐            │
                    │  Prometheus │◀───────────┘
                    │  :9090      │   (metrics)
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │  Grafana    │
                    │  :3000      │
                    └─────────────┘
                           ▲
                    ┌──────┴──────┐
                    │ AlertManager│
                    │  (alerts)   │
                    └─────────────┘
```

---

## Timeline

| Ticket | Duration | Cumulative |
|--------|----------|------------|
| 1. Observability | 2 days | 2 days |
| 2. Alerting | 1 day | 3 days |
| 3. Security | 2 days | 5 days |
| 4. CI/CD | 2 days | 7 days |
| 5. Disaster Recovery | 1 day | 8 days |

**Total: 8 days (2 weeks with buffer)**

---

## Definition of Done

Phase 3 is complete when:
1. ✅ Grafana dashboard shows real-time metrics
2. ✅ Alerts fire within 2 minutes of anomaly
3. ✅ Security scan passes with 0 critical findings
4. ✅ Deployment is one-click with automatic rollback
5. ✅ DR drill completes in < 15 minutes

---

**Started:** April 12, 2026
**Target:** April 26, 2026
