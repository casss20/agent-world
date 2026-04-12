#!/bin/bash
# Ticket 5: Redis Backup Script
# Automated backups with compression and rotation

set -e

BACKUP_DIR="${BACKUP_DIR:-/var/backups/agentverse/redis}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/redis_backup_${DATE}.rdb.gz"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[BACKUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check Redis connection
check_redis() {
    if [ -n "$REDIS_PASSWORD" ]; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping > /dev/null 2>&1
    else
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1
    fi
}

# Perform backup
backup_redis() {
    log "Starting Redis backup..."
    
    if ! check_redis; then
        error "Cannot connect to Redis at ${REDIS_HOST}:${REDIS_PORT}"
        exit 1
    fi
    
    log "Triggering BGSAVE..."
    if [ -n "$REDIS_PASSWORD" ]; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" BGSAVE
    else
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE
    fi
    
    # Wait for BGSAVE to complete
    log "Waiting for BGSAVE to complete..."
    while true; do
        if [ -n "$REDIS_PASSWORD" ]; then
            status=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" INFO Persistence | grep rdb_bgsave_in_progress)
        else
            status=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" INFO Persistence | grep rdb_bgsave_in_progress)
        fi
        
        if echo "$status" | grep -q ":0"; then
            break
        fi
        sleep 1
    done
    
    # Find Redis data directory
    if [ -n "$REDIS_PASSWORD" ]; then
        redis_dir=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" CONFIG GET dir | tail -1)
        redis_dbfilename=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" CONFIG GET dbfilename | tail -1)
    else
        redis_dir=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" CONFIG GET dir | tail -1)
        redis_dbfilename=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" CONFIG GET dbfilename | tail -1)
    fi
    
    dump_file="${redis_dir}/${redis_dbfilename}"
    
    if [ ! -f "$dump_file" ]; then
        error "Redis dump file not found: $dump_file"
        exit 1
    fi
    
    # Compress and copy
    log "Compressing backup..."
    gzip -c "$dump_file" > "$BACKUP_FILE"
    
    # Verify backup
    if [ -f "$BACKUP_FILE" ]; then
        size=$(du -h "$BACKUP_FILE" | cut -f1)
        log "✅ Backup complete: $BACKUP_FILE ($size)"
    else
        error "Backup file not created"
        exit 1
    fi
}

# Clean old backups
cleanup_old() {
    log "Cleaning backups older than $RETENTION_DAYS days..."
    deleted=$(find "$BACKUP_DIR" -name "redis_backup_*.rdb.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    log "Deleted $deleted old backup(s)"
}

# List backups
list_backups() {
    log "Available backups:"
    ls -lh "$BACKUP_DIR"/redis_backup_*.rdb.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  No backups found"
}

# Main
main() {
    case "${1:-backup}" in
        backup)
            backup_redis
            cleanup_old
            list_backups
            ;;
        list)
            list_backups
            ;;
        *)
            echo "Usage: $0 {backup|list}"
            exit 1
            ;;
    esac
}

main "$@"
