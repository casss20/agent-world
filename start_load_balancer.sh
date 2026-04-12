#!/bin/bash
# Ticket 6: Multi-Instance Load Balancer Setup
# Starts 3 stateless adapter instances behind nginx

set -e

echo "=========================================="
echo "Ticket 6: Multi-Instance Load Balancer"
echo "=========================================="

# Kill existing processes
echo "Cleaning up existing processes..."
pkill -f stateless_adapter 2>/dev/null || true
pkill -f nginx 2>/dev/null || true
sleep 2

cd /root/.openclaw/workspace/agent-world/backend

# Export shared config
export USE_REAL_CHATDEV=false
export REDIS_HOST=localhost
export REDIS_PORT=6379

echo ""
echo "Starting 3 adapter instances..."

# Instance 1 (port 8004)
INSTANCE_ID=instance_1 ADAPTER_PORT=8004 nohup python3 stateless_adapter.py > /tmp/instance1.log 2>&1 &
echo "Instance 1 (8004): PID $!"

# Instance 2 (port 8005)
INSTANCE_ID=instance_2 ADAPTER_PORT=8005 nohup python3 stateless_adapter.py > /tmp/instance2.log 2>&1 &
echo "Instance 2 (8005): PID $!"

# Instance 3 (port 8006)
INSTANCE_ID=instance_3 ADAPTER_PORT=8006 nohup python3 stateless_adapter.py > /tmp/instance3.log 2>&1 &
echo "Instance 3 (8006): PID $!"

echo ""
echo "Waiting for instances to start..."
sleep 5

# Check instances
echo ""
echo "Checking instances..."
for port in 8004 8005 8006; do
    status=$(curl -s http://localhost:$port/stateless/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "error")
    echo "  Port $port: $status"
done

# Start nginx
echo ""
echo "Starting nginx load balancer..."
nginx -c /root/.openclaw/workspace/agent-world/nginx.conf 2>/dev/null || nginx -s reload -c /root/.openclaw/workspace/agent-world/nginx.conf

echo ""
echo "Checking nginx..."
nginx_status=$(curl -s http://localhost:8080/health)
echo "  Nginx: $nginx_status"

echo ""
echo "=========================================="
echo "Load balancer ready!"
echo "=========================================="
echo ""
echo "Endpoints:"
echo "  Load Balancer: http://localhost:8080"
echo "  Instance 1:    http://localhost:8004"
echo "  Instance 2:    http://localhost:8005"
echo "  Instance 3:    http://localhost:8006"
echo ""
echo "Test with:"
echo "  curl http://localhost:8080/stateless/health"
echo ""
