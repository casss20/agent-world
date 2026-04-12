#!/bin/bash
# Ticket 4: Rollback Script
# Quick rollback to previous stable version

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_DIR}/.env.production"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[ROLLBACK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get previous version from git tags or deploy state
get_previous_version() {
    if [ -f /tmp/deploy_state ]; then
        source /tmp/deploy_state
        echo "$PREVIOUS_TAG"
    else
        # Get previous git tag
        git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo "latest"
    fi
}

# Quick health check
check_health() {
    local url="${1:-http://localhost:8080/stateless/health}"
    curl -sf "$url" > /dev/null 2>&1
}

# Main rollback
main() {
    local target_version="${1:-}"
    
    if [ -z "$target_version" ]; then
        target_version=$(get_previous_version)
        log "No version specified, using previous: $target_version"
    fi
    
    log "Starting rollback to: $target_version"
    
    # Check current state
    log "Checking current deployment..."
    if check_health; then
        warn "Current deployment is healthy - are you sure you want to rollback?"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Rollback cancelled"
            exit 0
        fi
    fi
    
    # Stop current containers
    log "Stopping current containers..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop adapter
    
    # Pull previous version
    log "Pulling version: $target_version"
    export IMAGE_TAG="$target_version"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull adapter
    
    # Start with previous version
    log "Starting previous version..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d adapter
    
    # Wait for stabilization
    log "Waiting for services to stabilize..."
    local retries=0
    local max_retries=30
    
    while [ $retries -lt $max_retries ]; do
        sleep 2
        
        if check_health; then
            log "✅ Rollback successful - services healthy"
            
            # Record rollback
            echo "ROLLBACK_TO=$target_version" >> /tmp/deploy_state
            echo "ROLLBACK_TIME=$(date -u +%Y-%m-%d_%H:%M:%S)" >> /tmp/deploy_state
            
            # Send notification (if configured)
            if [ -n "$SLACK_WEBHOOK_URL" ]; then
                curl -s -X POST "$SLACK_WEBHOOK_URL" \
                    -H 'Content-type: application/json' \
                    -d "{\"text\":\"⚠️ Rolled back to $target_version\"}" > /dev/null || true
            fi
            
            exit 0
        fi
        
        ((retries++))
        log "Health check $retries/$max_retries..."
    done
    
    error "❌ Rollback failed - services not healthy after $max_retries attempts"
    error "Manual intervention required"
    exit 1
}

# Handle script execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
