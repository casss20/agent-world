#!/bin/bash
# Ticket 2: Alerting Setup Script
# Configures and starts AlertManager

set -e

echo "=========================================="
echo "Ticket 2: Alerting Setup"
echo "=========================================="

# Check if alertmanager is installed
if ! command -v alertmanager &> /dev/null; then
    echo "AlertManager not found. Installing..."
    
    # Download AlertManager
    ALERTMANAGER_VERSION="0.26.0"
    wget -q "https://github.com/prometheus/alertmanager/releases/download/v${ALERTMANAGER_VERSION}/alertmanager-${ALERTMANAGER_VERSION}.linux-amd64.tar.gz" -O /tmp/alertmanager.tar.gz
    tar -xzf /tmp/alertmanager.tar.gz -C /tmp
    cp /tmp/alertmanager-*/alertmanager /usr/local/bin/
    cp /tmp/alertmanager-*/amtool /usr/local/bin/
    
    echo "✅ AlertManager installed"
else
    echo "✅ AlertManager already installed"
fi

# Create alertmanager data directory
mkdir -p /var/lib/alertmanager
mkdir -p /etc/alertmanager

# Copy configuration
cp /root/.openclaw/workspace/agent-world/alertmanager.yml /etc/alertmanager/alertmanager.yml

echo ""
echo "Starting AlertManager..."
nohup alertmanager \
    --config.file=/etc/alertmanager/alertmanager.yml \
    --storage.path=/var/lib/alertmanager \
    --web.listen-address=:9093 \
    --cluster.listen-address="" \
    > /tmp/alertmanager.log 2>&1 &

ALERTMANAGER_PID=$!
echo "AlertManager PID: $ALERTMANAGER_PID"

sleep 2

# Check health
if curl -s http://localhost:9093/-/healthy > /dev/null; then
    echo "✅ AlertManager is healthy"
else
    echo "❌ AlertManager failed to start"
    tail -20 /tmp/alertmanager.log
    exit 1
fi

echo ""
echo "=========================================="
echo "AlertManager Ready!"
echo "=========================================="
echo ""
echo "Web UI: http://localhost:9093"
echo "API:    http://localhost:9093/api/v1/alerts"
echo ""
echo "To test an alert:"
echo "  curl -X POST http://localhost:9093/api/v1/alerts \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '[{\"labels\":{\"alertname\":\"TestAlert\",\"severity\":\"warning\"}}]'"
echo ""
