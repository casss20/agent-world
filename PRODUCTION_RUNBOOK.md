

---

## Disaster Recovery

### Backup Operations

```bash
# Create manual backup
./scripts/backup_redis.sh backup

# List available backups
./scripts/backup_redis.sh list

# Automated backups (cron)
0 * * * * /root/.openclaw/workspace/agent-world/scripts/backup_redis.sh backup
```

### Restore Operations

```bash
# Restore from latest backup
./scripts/restore_redis.sh latest

# Restore from specific backup
./scripts/restore_redis.sh file /var/backups/agentverse/redis/redis_backup_YYYYMMDD_HHMMSS.rdb.gz

# List available backups
./scripts/restore_redis.sh list
```

### Recovery Objectives

| Objective | Target | Status |
|-----------|--------|--------|
| RTO | < 15 minutes | ✅ Tested |
| RPO | < 1 hour | ✅ Hourly backups |

### DR Test

```bash
# Validate DR readiness
python3 backend/test_ticket5_dr.py
```

