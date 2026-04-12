# Disaster Recovery Runbook - Ticket 5
**AgentVerse Money Room Recovery Procedures**

---

## Recovery Objectives

| Metric | Target | Current |
|--------|--------|---------|
| RTO (Recovery Time Objective) | < 15 minutes | TBD |
| RPO (Recovery Point Objective) | < 1 hour | Hourly backups |
| Data Loss Tolerance | < 1 hour | Configurable |

---

## Backup Strategy

### Automated Backups
- **Frequency:** Hourly
- **Retention:** 7 days
- **Location:** `/var/backups/agentverse/redis/`
- **Compression:** gzip
- **Encryption:** At-rest (configure for production)

### Manual Backup
```bash
# Create immediate backup
./scripts/backup_redis.sh

# List available backups
./scripts/backup_redis.sh list
```

### Cron Setup
```bash
# Add to crontab for hourly backups
0 * * * * /root/.openclaw/workspace/agent-world/scripts/backup_redis.sh backup >> /var/log/redis_backup.log 2>&1
```

---

## Recovery Procedures

### Scenario 1: Redis Data Corruption

**Symptoms:**
- Workflows not persisting
- Inconsistent state across instances
- Redis errors in logs

**Recovery Steps:**

1. **Stop all adapter instances**
   ```bash
   docker-compose -f docker-compose.prod.yml stop adapter
   ```

2. **Restore Redis from backup**
   ```bash
   ./scripts/restore_redis.sh latest
   ```

3. **Verify Redis data**
   ```bash
   redis-cli DBSIZE
   redis-cli KEYS "agentverse:*" | wc -l
   ```

4. **Restart services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Verify functionality**
   ```bash
   ./scripts/smoke_test.sh
   ```

**Expected Time:** 5-10 minutes

---

### Scenario 2: Complete Infrastructure Loss

**Symptoms:**
- All instances down
- Data center outage
- Hardware failure

**Recovery Steps:**

1. **Provision new infrastructure**
   - New servers/containers
   - Network configuration
   - DNS updates

2. **Restore from backups**
   ```bash
   # On new Redis server
   mkdir -p /var/backups/agentverse/redis
   # Copy backup from S3/offsite storage
   aws s3 cp s3://agentverse-backups/redis_backup_*.rdb.gz /var/backups/agentverse/redis/
   
   # Restore
   ./scripts/restore_redis.sh latest
   ```

3. **Deploy application**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify and monitor**
   ```bash
   ./scripts/smoke_test.sh
   curl http://localhost:8080/stateless/health
   ```

**Expected Time:** 10-15 minutes (excluding infrastructure provisioning)

---

### Scenario 3: Partial Instance Failure

**Symptoms:**
- 1-2 adapter instances unresponsive
- Load balancer reporting unhealthy
- Partial service degradation

**Recovery Steps:**

1. **Identify failed instances**
   ```bash
   for port in 8004 8005 8006; do
     curl -sf http://localhost:$port/stateless/health && echo "Port $port: OK" || echo "Port $port: FAIL"
   done
   ```

2. **Restart failed instances**
   ```bash
   docker-compose -f docker-compose.prod.yml restart adapter
   # Or scale and scale back:
   docker-compose -f docker-compose.prod.yml up -d --scale adapter=6
   sleep 10
   docker-compose -f docker-compose.prod.yml up -d --scale adapter=3
   ```

3. **Verify**
   ```bash
   ./scripts/smoke_test.sh
   ```

**Expected Time:** 2-5 minutes

---

## Backup Verification

### Monthly DR Drill

1. **Schedule drill** (off-peak hours)
2. **Create fresh backup**
3. **Restore to staging environment**
4. **Verify all functionality**
5. **Document any issues**
6. **Update procedures**

### Quick Verification (Weekly)

```bash
# Verify backup exists and is readable
./scripts/backup_redis.sh list

# Check backup integrity
gunzip -t /var/backups/agentverse/redis/redis_backup_*.rdb.gz

# Verify Redis persistence
redis-cli CONFIG GET save
redis-cli CONFIG GET appendonly
```

---

## Offsite Backup Strategy

### S3 Backup (Recommended)

```bash
# Sync to S3
aws s3 sync /var/backups/agentverse/redis/ s3://agentverse-backups/redis/ \
  --storage-class STANDARD_IA

# Lifecycle policy: Move to Glacier after 30 days
```

### Alternative: rsync to backup server

```bash
rsync -avz /var/backups/agentverse/redis/ backup-server:/backups/agentverse/
```

---

## Monitoring Backups

### Alert if Backup Fails

Add to Prometheus alert rules:
```yaml
- alert: BackupFailed
  expr: time() - redis_last_backup_timestamp > 7200
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Redis backup hasn't run in 2 hours"
```

### Backup Metrics

Log backup results for monitoring:
```bash
# In backup script, emit metrics
echo "redis_backup_last_run $(date +%s)" >> /var/lib/node_exporter/textfile_collector/redis_backup.prom
echo "redis_backup_size_bytes $(stat -f%z $BACKUP_FILE)" >> /var/lib/node_exporter/textfile_collector/redis_backup.prom
```

---

## Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| Primary On-Call | ops@agentverse.local | +1-XXX-XXX-XXXX |
| Secondary | sre@agentverse.local | +1-XXX-XXX-XXXX |
| Engineering Lead | lead@agentverse.local | Slack: #incidents |

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-04-12 | 1.0 | Initial DR runbook |

---

**Last Tested:** _Not yet tested_  
**Next Drill:** _Schedule within 30 days_
