#!/bin/bash
# Option 1: Full Docker Compose Deployment
# Build and start all services including Camofox and Multica

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[OPTION-1]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

cd "$PROJECT_DIR"

log "Starting Option 1: Full Docker Compose Deployment"
log "Project: $PROJECT_DIR"
log "Compose: $COMPOSE_FILE"

echo ""
info "Step 1: Checking prerequisites..."

# Check Docker
docker --version > /dev/null 2>&1 || { error "Docker not installed"; exit 1; }
docker-compose --version > /dev/null 2>&1 || { error "Docker Compose not installed"; exit 1; }
log "✅ Docker and Docker Compose available"

# Check environment file
if [ ! -f ".env" ]; then
    warn ".env file not found, copying from .env.example"
    cp .env.example .env
    warn "⚠️  Please edit .env with your actual values"
fi

echo ""
info "Step 2: Preparing Camofox Browser..."
if [ -d "../camofox-browser" ]; then
    log "✅ Camofox source found"
    cd ../camofox-browser
    if [ ! -d "node_modules" ]; then
        log "Installing Camofox dependencies..."
        npm install
    fi
    if [ ! -d "dist/camoufox" ]; then
        log "Downloading Camoufox binaries..."
        make fetch || npm run setup
    fi
    cd "$PROJECT_DIR"
else
    error "Camofox not found at ../camofox-browser"
    exit 1
fi

echo ""
info "Step 3: Preparing Multica..."
if [ -d "../multica" ]; then
    log "✅ Multica source found"
else
    error "Multica not found at ../multica"
    exit 1
fi

echo ""
info "Step 4: Building Docker images..."
docker-compose -f "$COMPOSE_FILE" build --parallel 2>&1 | tee /tmp/docker-build.log | grep -E "(Step|Successfully|Error)" || true
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    error "Docker build failed, check /tmp/docker-build.log"
    exit 1
fi
log "✅ Docker images built"

echo ""
info "Step 5: Starting services..."
docker-compose -f "$COMPOSE_FILE" up -d
log "✅ Services started"

echo ""
info "Step 6: Waiting for services to be healthy..."
sleep 10

# Health checks
HEALTHY=0
TOTAL=0

check_service() {
    local name=$1
    local url=$2
    TOTAL=$((TOTAL + 1))
    
    if curl -sf "$url" > /dev/null 2>&1; then
        log "✅ $name is healthy"
        HEALTHY=$((HEALTHY + 1))
        return 0
    else
        warn "⚠️  $name not responding"
        return 1
    fi
}

echo ""
log "Checking service health..."
check_service "Nginx" "http://localhost:8080/health"
check_service "Adapter-1" "http://localhost:8004/stateless/health"
check_service "Adapter-2" "http://localhost:8005/stateless/health"
check_service "Adapter-3" "http://localhost:8006/stateless/health"
check_service "Camofox" "http://localhost:9377/health"
check_service "Multica" "http://localhost:8081/health"
check_service "Prometheus" "http://localhost:9090/-/healthy"

echo ""
info "Step 7: Running integration tests..."
python3 backend/test_phase4_integration.py || warn "Some tests failed"

echo ""
log "=========================================="
log "OPTION 1 DEPLOYMENT COMPLETE"
log "=========================================="
echo ""
info "Services:"
echo "  Nginx LB:       http://localhost:8080"
echo "  Adapter API:    http://localhost:8080/stateless/"
echo "  Camofox:        http://localhost:8080/camofox/"
echo "  Multica:        http://localhost:8080/multica/"
echo "  Prometheus:     http://localhost:9090"
echo "  Grafana:        http://localhost:3000"
echo ""
info "Quick commands:"
echo "  Logs:    docker-compose -f $COMPOSE_FILE logs -f"
echo "  Stop:    docker-compose -f $COMPOSE_FILE down"
echo "  Scale:   docker-compose -f $COMPOSE_FILE up -d --scale adapter=5"
echo ""
log "Health: $HEALTHY/$TOTAL services responding"

if [ $HEALTHY -eq $TOTAL ]; then
    log "🎉 All services healthy and ready!"
    exit 0
else
    warn "Some services still starting, check logs"
    exit 0
fi
