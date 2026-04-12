# Production Runbook - AgentVerse Money Room
**Ticket 8: Phase 2 Documentation**

---

## Quick Start

```bash
# 1. Start all services
cd /root/.openclaw/workspace/agent-world
./start_load_balancer.sh

# 2. Verify health
curl http://localhost:8080/stateless/health

# 3. Launch workflow
curl -X POST http://localhost:8080/stateless/launch \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": "room_001",
    "user_id": "user_001",
    "workflow_id": "demo_simple_memory",
    "task_prompt": "Find trending content"
  }'
```

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Nginx :8080│────▶│  Instance 1 │
└─────────────┘     │  (load bal) │     │   :8004     │
                    └──────┬──────┘     └──────┬──────┘
                           │                    │
                    ┌──────┴──────┐     ┌──────┴──────┐
                    │  Instance 2 │     │  Instance 3 │
                    │   :8005     │     │   :8006     │
                    └──────┬──────┘     └──────┬──────┘
                           │                    │
                           └────────┬───────────┘
                                    │
                           ┌────────▼────────┐
                           │  Redis (shared  │
                           │   state) :6379  │
                           └─────────────────┘
```

---

## Services

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| nginx | 8080 | Load balancer | `GET /health` |
| adapter-1 | 8004 | Instance 1 | `GET /stateless/health` |
| adapter-2 | 8005 | Instance 2 | `GET /stateless/health` |
| adapter-3 | 8006 | Instance 3 | `GET /stateless/health` |
| redis | 6379 | Shared state | `redis-cli ping` |

---

## API Reference

### Launch Workflow
```http
POST /stateless/launch
Content-Type: application/json

{
  "room_id": "string",
  "user_id": "string",
  "workflow_id": "demo_simple_memory",
  "task_prompt": "string",
  "variables": {},
  "webhook_url": "optional"
}

Response:
{
  "run_id": "run_2026...",
  "status": "pending",
  "estimated_duration": 30,
  "correlation_id": "abc123"
}
```

### Get Status
```http
GET /stateless/status/{run_id}

Response:
{
  "run_id": "run_2026...",
  "status": "running",
  "progress_percent": 50,
  "current_agent": null,
  "started_at": "2026-04-12T...",
  "estimated_completion": null
}
```

### Cancel Workflow
```http
POST /stateless/cancel/{run_id}

Response:
{
  "run_id": "run_2026...",
  "status": "cancelled",
  "correlation_id": "abc123"
}
```

### Health Check
```http
GET /stateless/health

Response:
{
  "status": "healthy",
  "instance_id": "instance_1",
  "engine_mode": "MOCK",
  "shared_state": {"status": "connected"},
  "correlation_id": "abc123"
}
```

---

## Monitoring

### Check Instance Health
```bash
# All instances
for port in 8004 8005 8006; do
  curl -s http://localhost:$port/stateless/health | jq '.instance_id, .status'
done

# Via load balancer (round-robin)
curl -s http://localhost:8080/stateless/health | jq '.instance_id'
```

### Check Redis
```bash
redis-cli ping  # Should return PONG
redis-cli info clients
redis-cli dbsize
```

### Check Nginx
```bash
curl http://localhost:8080/nginx_status
```

---

## Troubleshooting

### Instance Not Responding
```bash
# Check if process is running
ps aux | grep stateless_adapter

# Restart single instance
INSTANCE_ID=instance_1 ADAPTER_PORT=8004 python3 backend/stateless_adapter.py

# Check logs
tail -f /tmp/instance1.log
```

### Redis Connection Failed
```bash
# Check Redis
redis-cli ping

# Restart Redis
redis-server --daemonize yes

# Check adapter logs for connection errors
grep -i redis /tmp/instance*.log
```

### High Latency
```bash
# Run quick latency test
for i in {1..10}; do
  time curl -s http://localhost:8080/stateless/health > /dev/null
done

# Check circuit breaker status
# (View logs for circuit breaker events)
grep -i "circuit" /tmp/instance*.log
```

### Workflow Stuck
```bash
# Check run status
curl http://localhost:8080/stateless/status/{run_id}

# Check which instance is handling it
# (View logs for run_id)
grep {run_id} /tmp/instance*.log
```

---

## Configuration

### Environment Variables
```bash
# Adapter
INSTANCE_ID=instance_1        # Unique per instance
ADAPTER_PORT=8004             # Port for this instance
USE_REAL_CHATDEV=false        # MOCK or REAL
REDIS_HOST=localhost
REDIS_PORT=6379

# ChatDev Money (for REAL mode)
BASE_URL=https://api.openai.com/v1
API_KEY=sk-proj-...
```

### Nginx Configuration
See `nginx.conf`:
- `least_conn` load balancing
- 3 upstream instances
- Health checks every request
- Keepalive connections

---

## Load Testing

### Quick Test
```bash
cd backend
python3 test_load_balancer.py
```

### Production Validation
```bash
cd backend
python3 ticket7_load_test_fast.py  # ~2 minutes
python3 ticket7_load_test.py        # ~30 minutes (full)
```

### Expected Results
- 100 workflows sustained
- P95 latency < 1000ms
- Error rate < 1%
- 100% health check success

---

## Scaling

### Add More Instances
1. Edit `nginx.conf`, add new server:
```nginx
upstream stateless_adapter {
    server 127.0.0.1:8004;
    server 127.0.0.1:8005;
    server 127.0.0.1:8006;
    server 127.0.0.1:8007;  # New
}
```

2. Start new instance:
```bash
INSTANCE_ID=instance_4 ADAPTER_PORT=8007 python3 stateless_adapter.py
```

3. Reload nginx:
```bash
nginx -s reload
```

---

## Phase 2 Summary

| Ticket | Feature | Status |
|--------|---------|--------|
| 1 | Webhook Receiver | ✅ 29.5ms P99 |
| 2 | Webhook Emitter | ✅ Retry logic |
| 3 | Integration Test | ✅ 7/7 passed |
| 4 | Real LLM | ✅ 481 tokens |
| 5 | Stateless Adapter | ✅ Redis-backed |
| 6 | Load Balancer | ✅ 3 instances |
| 7 | Production Test | ✅ 100 workflows |
| 8 | Documentation | ✅ This file |

---

## Support

- **GitHub**: `arch/v2-multi-agent-platform` branch
- **Logs**: `/tmp/instance*.log`
- **Test Results**: `/tmp/production_load_test.json`

---

**Version**: 2.1.0-stateless  
**Last Updated**: April 12, 2026  
**Total Commits**: 28
