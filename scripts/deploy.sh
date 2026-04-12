#!/bin/bash
# Ticket 4: Deployment Script with Blue-Green Strategy
# Safe deployment with automatic rollback on failure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_DIR}/.env.production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[DEPLOY]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    command -v docker >/dev/null 2>&1 || { error "Docker not installed"; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { error "Docker Compose not installed"; exit 1; }
    
    if [ ! -f "$ENV_FILE" ]; then
        error "Production env file not found: $ENV_FILE"
        exit 1
    fi
    
    log "Prerequisites OK"
}

# Pre-deployment health check
pre_deploy_check() {
    log "Running pre-deployment health check..."
    
    # Check current deployment is healthy
    if ! curl -sf http://localhost:8080/stateless/health > /dev/null 2>&1; then
        warn "Current deployment not healthy, proceeding with fresh deploy"
    else
        log "Current deployment healthy"
    fi
}

# Deploy with blue-green strategy
deploy_blue_green() {
    local tag="${1:-latest}"
    
    log "Starting blue-green deployment with tag: $tag"
    
    # Pull new images
    log "Pulling new images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    
    # Scale up new instances (green)
    log "Scaling up green instances..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps --scale adapter=6 adapter
    
    # Wait for green instances to be healthy
    log "Waiting for green instances to be healthy..."
    local retries=0
    local max_retries=30
    
    while [ $retries -lt $max_retries ]; do
        sleep 2
        
        # Check health on multiple ports
        healthy_count=0
        for port in 8004 8005 8006 8007 8008 8009; do
            if curl -sf "http://localhost:$port/stateless/health" > /dev/null 2>&1; then
                ((healthy_count++))
            fi
        done
        
        log "Green instances healthy: $healthy_count/6"
        
        if [ $healthy_count -ge 6 ]; then
            log "All green instances healthy!"
            break
        fi
        
        ((retries++))
    done
    
    if [ $retries -eq $max_retries ]; then
        error "Green instances failed health check"
        return 1
    fi
    
    # Switch traffic (nginx automatically uses new instances)
    log "Traffic now routing to green instances..."
    
    # Scale down old instances (blue)
    log "Scaling down blue instances..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps --scale adapter=3 adapter
    
    log "Blue-green deployment complete!"
}

# Smoke tests
smoke_tests() {
    log "Running smoke tests..."
    
    local tests_passed=0
    local tests_failed=0
    
    # Test health endpoint
    if curl -sf http://localhost:8080/stateless/health > /dev/null; then
        log "✓ Health check passed"
        ((tests_passed++))
    else
        error "✗ Health check failed"
        ((tests_failed++))
    fi
    
    # Test metrics endpoint
    if curl -sf http://localhost:8004/metrics > /dev/null; then
        log "✓ Metrics endpoint passed"
        ((tests_passed++))
    else
        error "✗ Metrics endpoint failed"
        ((tests_failed++))
    fi
    
    # Test workflow launch
    local run_id=$(curl -sf -X POST http://localhost:8080/stateless/launch \
        -H "Content-Type: application/json" \
        -d '{"room_id":"smoke_test","user_id":"deploy","workflow_id":"demo_simple_memory","task_prompt":"smoke test"}' | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('run_id',''))")
    
    if [ -n "$run_id" ]; then
        log "✓ Workflow launch passed (run_id: $run_id)"
        ((tests_passed++))
    else
        error "✗ Workflow launch failed"
        ((tests_failed++))
    fi
    
    # Test Redis connectivity
    if redis-cli ping > /dev/null 2>&1; then
        log "✓ Redis connectivity passed"
        ((tests_passed++))
    else
        error "✗ Redis connectivity failed"
        ((tests_failed++))
    fi
    
    log "Smoke tests: $tests_passed passed, $tests_failed failed"
    
    if [ $tests_failed -gt 0 ]; then
        return 1
    fi
    
    return 0
}

# Rollback to previous version
rollback() {
    local previous_tag="$1"
    
    error "Initiating rollback to: $previous_tag"
    
    # Pull previous image
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull adapter:${previous_tag}
    
    # Restart with previous version
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps adapter
    
    # Wait for rollback to stabilize
    sleep 10
    
    # Verify rollback
    if curl -sf http://localhost:8080/stateless/health > /dev/null; then
        log "✅ Rollback successful"
        return 0
    else
        error "❌ Rollback failed - manual intervention required"
        return 1
    fi
}

# Main deployment flow
main() {
    local tag="${1:-latest}"
    local previous_tag="${2:-}"
    
    log "Starting deployment..."
    log "Target tag: $tag"
    
    check_prerequisites
    pre_deploy_check
    
    # Record deployment start
    local deploy_start=$(date -u +%Y-%m-%d_%H:%M:%S)
    echo "DEPLOY_START=$deploy_start" > /tmp/deploy_state
    echo "PREVIOUS_TAG=$previous_tag" >> /tmp/deploy_state
    echo "TARGET_TAG=$tag" >> /tmp/deploy_state
    
    # Deploy
    if deploy_blue_green "$tag"; then
        log "Deployment successful, running smoke tests..."
        
        if smoke_tests; then
            log "✅ Deployment complete and verified!"
            echo "DEPLOY_END=$(date -u +%Y-%m-%d_%H:%M:%S)" >> /tmp/deploy_state
            echo "STATUS=success" >> /tmp/deploy_state
            exit 0
        else
            error "Smoke tests failed, initiating rollback..."
            
            if rollback "$previous_tag"; then
                log "Rollback complete"
                echo "STATUS=rolled_back" >> /tmp/deploy_state
                exit 1
            else
                error "CRITICAL: Rollback failed!"
                echo "STATUS=failed" >> /tmp/deploy_state
                exit 2
            fi
        fi
    else
        error "Deployment failed"
        
        if [ -n "$previous_tag" ]; then
            rollback "$previous_tag"
        fi
        
        exit 1
    fi
}

# Handle script execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
