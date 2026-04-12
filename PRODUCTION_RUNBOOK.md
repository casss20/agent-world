

---

## CI/CD Pipeline

### GitHub Actions Workflow
**File:** `.github/workflows/deploy.yml`

**Triggers:**
- Push to `main` or `arch/v2-multi-agent-platform`
- Tags starting with `v`
- Pull requests to `main`

**Stages:**
1. **Test** — Run pytest, security scan (bandit, safety)
2. **Build** — Build Docker image, push to GHCR
3. **Deploy Staging** — Deploy to staging, run smoke tests
4. **Deploy Production** — Blue-green deploy with auto-rollback

### Manual Deployment

```bash
# Deploy to production
./scripts/deploy.sh [tag]

# Rollback to previous version
./scripts/rollback.sh [tag]

# Run smoke tests
./scripts/smoke_test.sh
python3 backend/test_ticket4_smoke.py
```

### Blue-Green Deployment

1. **Green instances** scaled up alongside blue
2. **Health checks** verify green is healthy
3. **Traffic switches** to green (nginx handles this)
4. **Blue instances** scaled down
5. **Automatic rollback** if smoke tests fail

### Environment Variables

```bash
# Required for production
JWT_SECRET=your-256-bit-secret
REDIS_PASSWORD=strong-redis-password
REGISTRY=ghcr.io/casss20
IMAGE_TAG=v1.2.3

# Optional
USE_REAL_CHATDEV=true
CHATDEV_API_URL=http://chatdev:8000
GRAFANA_PASSWORD=admin
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Docker Compose Production

```bash
# Start production stack
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f adapter

# Scale adapter instances
docker-compose -f docker-compose.prod.yml up -d --scale adapter=5
```

---

## Phase 3 Status

| Ticket | Feature | Status |
|--------|---------|--------|
| 1 | Observability | ✅ Complete |
| 2 | Alerting | ✅ Complete |
| 3 | Security Hardening | ✅ Complete |
| 4 | CI/CD + Rollback | ✅ Complete |
| 5 | Disaster Recovery | ⏳ Next |

