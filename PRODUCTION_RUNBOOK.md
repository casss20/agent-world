

---

## Alerting

### Alert Configuration

**Prometheus Rules:** `alert_rules.yml`
**AlertManager Config:** `alertmanager.yml`

### Active Alerts

| Alert | Severity | Condition | Action |
|-------|----------|-----------|--------|
| AdapterHighLatency | warning | P95 > 1s for 5m | Check instance load |
| AdapterHighErrorRate | critical | Error rate > 1% | Check logs |
| AdapterInstanceDown | critical | Instance down > 1m | Restart instance |
| CircuitBreakerOpen | warning | Breaker opened | Check downstream |
| RedisDown | critical | Redis disconnected | Restart Redis |
| HighActiveWorkflows | warning | > 50 active | Scale up |
| HighMemoryUsage | warning | > 500MB | Restart instance |
| WorkflowFailureRate | warning | > 5% failing | Check ChatDev Money |

### AlertManager Web UI
```
http://localhost:9093
```

### Test Alerts
```bash
# Send test alert
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{"labels":{"alertname":"TestAlert","severity":"warning"},"annotations":{"summary":"Test alert"}}]'
```

### Setup Alerting
```bash
./setup_alerting.sh
```

### Configure Slack Notifications
Edit `alertmanager.yml`:
```yaml
global:
  slack_api_url: 'YOUR_WEBHOOK_URL'
```

---

## Troubleshooting (Alerting)

### AlertManager Not Starting
```bash
# Check config validity
amtool check-config alertmanager.yml

# Check logs
tail -f /tmp/alertmanager.log
```

### Alerts Not Firing
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check alert rules
curl http://localhost:9090/api/v1/rules

# Check active alerts
curl http://localhost:9090/api/v1/alerts
```

---

## Phase 3 Status

| Ticket | Feature | Status |
|--------|---------|--------|
| 1 | Observability | ✅ Complete |
| 2 | Alerting | ✅ Complete |
| 3 | Security | ⏳ |
| 4 | CI/CD | ⏳ |
| 5 | Disaster Recovery | ⏳ |

