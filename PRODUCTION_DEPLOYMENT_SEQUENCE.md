# Production Deployment Sequence

## Deployment Timeline

### Phase 1: Rate Limiting (1 hour) ✅ COMPLETE
**Status:** Deployed

**Protection:**
- Tier 1 (/execute, /token): 3/minute per identity
- Tier 2 (/agents/register): 5/minute per IP
- Tier 3 (read endpoints): 60/minute per IP

**Files:**
- `governance_v2/rate_limit.py` - Rate limiting system
- `governance_v2/routes.py` - Protected endpoints

**Test:**
```bash
# Test Tier 1 limit (3/min)
for i in {1..5}; do
  curl -X POST /governance/v2/execute -H "Authorization: Bearer $TOKEN"
done
# Expect: 3 success, then 429

# Test Tier 2 limit (5/min per IP)
for i in {1..7}; do
  curl -X POST /governance/v2/agents/register -H "Authorization: Bearer $TOKEN"
done
# Expect: 5 success, then 429
```

---

### Phase 2: Health Checks (30 min) ⏳ PENDING

**Endpoints to Add:**
```python
@app.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe - is the process running?"""
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe - is the service ready for traffic?"""
    checks = {
        "database": check_db_connection(),
        "governance": governance_system is not None,
        "redis": check_redis_connection()  # if using Redis
    }
    
    all_ready = all(checks.values())
    
    if all_ready:
        return {"status": "ready", "checks": checks}
    else:
        raise HTTPException(503, {"status": "not_ready", "checks": checks})
```

**Kubernetes Config:**
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

### Phase 3: Nginx Reverse Proxy (1 hour) ⏳ PENDING

**Nginx Config:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.agent-world.com;

    # TLS Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate Limiting (backup to app-level)
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req zone=api burst=20 nodelay;

    # Proxy to FastAPI
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

**Gateway Policy:**
- Block requests without User-Agent
- Block requests with suspicious patterns
- Geo-blocking (optional)
- Bot detection (optional)

---

### Phase 4: Audit Log Viewer (2 hours) ⏳ PENDING

**Endpoint:**
```python
@app.get("/audit")
async def view_audit_logs(
    user: UserPrincipal = Depends(require_admin),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
):
    """
    View audit logs for incident response.
    
    **Required Role:** admin only
    """
    # Query from database (not memory)
    logs = await query_audit_logs(
        start_date=start_date,
        end_date=end_date,
        actor=actor,
        action=action,
        limit=limit
    )
    
    return {
        "count": len(logs),
        "logs": logs
    }
```

**Features:**
- Filter by date range
- Filter by actor (user/agent)
- Filter by action type
- Export to CSV/JSON
- Real-time streaming (WebSocket)

**Database Schema:**
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    actor_type VARCHAR(20),  -- 'user' or 'agent'
    actor_id VARCHAR(120),
    action VARCHAR(120),
    resource_type VARCHAR(80),
    resource_id VARCHAR(120),
    business_id INTEGER,
    result VARCHAR(40),
    request_id VARCHAR(120),
    metadata JSONB
);

CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_actor ON audit_logs(actor_type, actor_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Database migrations applied
- [ ] Environment variables configured
- [ ] SSL certificates ready
- [ ] Backup strategy verified

### Deployment
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Deploy to production (blue/green)
- [ ] Monitor error rates
- [ ] Verify rate limiting active

### Post-Deployment
- [ ] Health checks responding
- [ ] Audit logs flowing
- [ ] Alerts configured
- [ ] Documentation updated
- [ ] Team notified

---

## Rollback Plan

If issues detected:
1. Switch traffic to previous version (blue/green)
2. Investigate logs
3. Fix issues in staging
4. Re-deploy

**Rollback Time:** < 5 minutes with blue/green deployment

---

## Monitoring

**Key Metrics:**
- Request rate (per endpoint)
- Error rate (4xx, 5xx)
- Latency (p50, p95, p99)
- Rate limit hits (429 responses)
- Authentication failures (401, 403)

**Alerts:**
- Error rate > 1%
- Latency p95 > 500ms
- Rate limit hits > 100/min
- Authentication failures > 50/min
- Health check failures

---

*Last Updated: 2026-04-13*
*Status: Phase 1 Complete, Phases 2-4 Pending*
