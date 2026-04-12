#!/bin/bash
# Ticket 5: Redis Restore Script
# Restore Redis from backup with validation

set -e

BACKUP_DIR="${BACKUP_DIR:-/var/backups/agentverse/redis}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[RESTORE]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# List available backups
list_backups() {
    log "Available backups:"
    ls -1t "$BACKUP_DIR"/redis_backup_*.rdb.gz 2>/dev/null | head -10 | nl
}

# Restore from backup
restore_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log "Restoring from: $backup_file"
    
    # Safety check
    warn "⚠️  This will REPLACE current Redis data!"
    read -p "Are you sure? (type 'yes' to continue): " confirm
    if [ "$confirm" != "yes" ]; then
        log "Restore cancelled"
        exit 0
    fi
    
    # Stop Redis or use replication
    log "Creating temporary restore directory..."
    local temp_dir=$(mktemp -d)
    
    # Decompress backup
    log "Decompressing backup..."
    gunzip -c "$backup_file" > "$temp_dir/dump.rdb"
    
    # Get Redis data directory
    if [ -n "$REDIS_PASSWORD" ]; then
        redis_dir=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" CONFIG GET dir | tail -1)
    else
        redis_dir=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" CONFIG GET dir | tail -1)
    fi
    
    # Backup current data
    if [ -f "$redis_dir/dump.rdb" ]; then
        local current_backup="$redis_dir/dump.rdb.pre_restore_$(date +%Y%m%d_%H%M%S)"
        log "Backing up current data to: $current_backup"
        cp "$redis_dir/dump.rdb" "$current_backup"
    fi
    
    # Stop Redis (if running locally)
    log "Stopping Redis..."
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ${REDIS_PASSWORD:+-a "$REDIS_PASSWORD"} SHUTDOWN NOSAVE 2>/dev/null || true
    sleep 2
    
    # Copy restore file
    log "Installing backup..."
    cp "$temp_dir/dump.rdb" "$redis_dir/dump.rdb"
    
    # Start Redis
    log "Starting Redis..."
    redis-server --daemonize yes
    sleep 2
    
    # Verify
    if redis-cli ping > /dev/null 2>&1; then
        local db_size=$(redis-cli DBSIZE)
        log "✅ Restore complete! Redis has $db_size keys"
    else
        error "❌ Restore failed - Redis not responding"
        exit 1
    fi
    
    # Cleanup
    rm -rf "$temp_dir"
}

# Quick restore (latest backup)
restore_latest() {
    local latest=$(ls -1t "$BACKUP_DIR"/redis_backup_*.rdb.gz 2>/dev/null | head -1)
    if [ -z "$latest" ]; then
        error "No backups found in $BACKUP_DIR"
        exit 1
    fi
    restore_backup "$latest"
}

# Main
main() {
    case "${1:-}" in
        list)
            list_backups
            ;;
        latest)
            restore_latest
            ;;
        file)
            if [ -z "${2:-}" ]; then
                error "Usage: $0 file <backup_file>"
                exit 1
            fi
            restore_backup "$2"
            ;;
        *)
            echo "Usage: $0 {list|latest|file <backup_file>}"
            echo ""
            echo "Commands:"
            echo "  list              - Show available backups"
            echo "  latest            - Restore from most recent backup"
            echo "  file <file>      - Restore from specific backup file"
            exit 1
            ;;
    esac
}

main "$@"
