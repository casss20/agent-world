#!/bin/bash
# Option 1: Production Service Management
# Start all services for production deployment

set -e

PROJECT_DIR="/root/.openclaw/workspace/agent-world"
CAMOFOX_DIR="/root/.openclaw/workspace/camofox-browser"
MULTICA_DIR="/root/.openclaw/workspace/multica/server"

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

PID_DIR="/tmp/agentverse_pids"
mkdir -p "$PID_DIR"

start_service() {
    local name=$1
    local command=$2
    local pid_file="$PID_DIR/$name.pid"
    
    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        warn "$name already running (PID: $(cat $pid_file))"
        return 0
    fi
    
    log "Starting $name..."
    eval "$command > /tmp/$name.log 2>&1 &"
    echo $! > "$pid_file"
    log "✅ $name started (PID: $(cat $pid_file))"
}

stop_service() {
    local name=$1
    local pid_file="$PID_DIR/$name.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping $name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            rm -f "$pid_file"
            log "✅ $name stopped"
        else
            rm -f "$pid_file"
        fi
    else
        warn "$name not running"
    fi
}

check_service() {
    local name=$1
    local url=$2
    local pid_file="$PID_DIR/$name.pid"
    
    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅${NC} $name: Running & Healthy"
            return 0
        else
            echo -e "${YELLOW}⚠️${NC} $name: Running but not responding"
            return 1
        fi
    else
        echo -e "${RED}❌${NC} $name: Not running"
        return 1
    fi
}

cmd_start() {
    log "=========================================="
    log "OPTION 1: Production Service Startup"
    log "=========================================="
    
    # 1. Start Redis
    if ! pgrep -x "redis-server" > /dev/null; then
        log "Starting Redis..."
        redis-server --daemonize yes
        sleep 1
        if redis-cli ping > /dev/null 2>&1; then
            log "✅ Redis started"
        else
            error "Redis failed to start"
        fi
    else
        log "✅ Redis already running"
    fi
    
    # 2. Start PostgreSQL
    if ! pgrep -x "postgres" > /dev/null; then
        log "Starting PostgreSQL..."
        su - postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/data -l /var/lib/postgresql/logfile start" || true
        sleep 2
        if pgrep -x "postgres" > /dev/null; then
            log "✅ PostgreSQL started"
        else
            error "PostgreSQL failed to start"
        fi
    else
        log "✅ PostgreSQL already running"
    fi
    
    # 3. Start Adapter instances
    cd "$PROJECT_DIR/backend"
    export REDIS_HOST=localhost
    export REDIS_PORT=6379
    export REDIS_PASSWORD=redis_password
    export USE_REAL_CHATDEV=false
    export JWT_SECRET=production_secret_key_here
    
    for port in 8004 8005 8006; do
        start_service "adapter-$port" "cd $PROJECT_DIR/backend && PORT=$port INSTANCE_ID=instance_$port python3 stateless_adapter.py"
        sleep 1
    done
    
    # 4. Start Camofox
    cd "$CAMOFOX_DIR"
    export CAMOFOX_PORT=9377
    start_service "camofox" "cd $CAMOFOX_DIR && node server.js"
    sleep 3
    
    # 5. Start Multica
    cd "$MULTICA_DIR"
    export DATABASE_URL="postgres://multica:multica@localhost:5432/multica?sslmode=disable"
    export JWT_SECRET="multica_production_secret"
    export PORT=8081
    start_service "multica" "cd $MULTICA_DIR && ./multica-server"
    sleep 2
    
    # 6. Start Nginx
    if [ -f "$PID_DIR/nginx.pid" ] && kill -0 $(cat "$PID_DIR/nginx.pid") 2>/dev/null; then
        warn "Nginx already running"
    else
        log "Starting Nginx..."
        nginx -c "$PROJECT_DIR/nginx.conf"
        echo $(pgrep -x nginx | head -1) > "$PID_DIR/nginx.pid"
        log "✅ Nginx started"
    fi
    
    echo ""
    log "=========================================="
    log "ALL SERVICES STARTED"
    log "=========================================="
    sleep 3
    cmd_status
}

cmd_stop() {
    log "=========================================="
    log "Stopping all services..."
    log "=========================================="
    
    stop_service "nginx"
    stop_service "multica"
    stop_service "camofox"
    stop_service "adapter-8004"
    stop_service "adapter-8005"
    stop_service "adapter-8006"
    
    # Note: We don't stop Redis/PostgreSQL as they might be system services
    warn "Note: Redis and PostgreSQL left running (system services)"
    
    log "✅ All application services stopped"
}

cmd_status() {
    echo ""
    log "=========================================="
    log "SERVICE STATUS"
    log "=========================================="
    
    check_service "nginx" "http://localhost:8080/health"
    check_service "adapter-8004" "http://localhost:8004/stateless/health"
    check_service "adapter-8005" "http://localhost:8005/stateless/health"
    check_service "adapter-8006" "http://localhost:8006/stateless/health"
    check_service "camofox" "http://localhost:9377/health"
    check_service "multica" "http://localhost:8081/health"
    
    echo ""
    info "System Services:"
    if pgrep -x "redis-server" > /dev/null; then
        echo -e "${GREEN}✅${NC} Redis: Running"
    else
        echo -e "${RED}❌${NC} Redis: Not running"
    fi
    
    if pgrep -x "postgres" > /dev/null; then
        echo -e "${GREEN}✅${NC} PostgreSQL: Running"
    else
        echo -e "${RED}❌${NC} PostgreSQL: Not running"
    fi
}

cmd_logs() {
    local service=$1
    if [ -f "/tmp/$service.log" ]; then
        tail -f "/tmp/$service.log"
    else
        error "No logs found for $service"
    fi
}

# Main command handler
case "${1:-status}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_stop
        sleep 2
        cmd_start
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "$2"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs <service>}"
        echo ""
        echo "Services: adapter-8004, adapter-8005, adapter-8006, camofox, multica, nginx"
        exit 1
        ;;
esac
