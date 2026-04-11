#!/bin/bash
# Run REAL mode integration test with proper process management

set -e

cd /root/.openclaw/workspace/agent-world/backend

# Clean up
rm -f /var/lib/agentverse/audit.db /tmp/guarded_adapter.log
pkill -f guarded_adapter 2>/dev/null || true
sleep 2

# Start adapter
export USE_REAL_CHATDEV=true
export CHATDEV_API_URL=http://localhost:6400
python3 guarded_adapter.py > /tmp/guarded_adapter.log 2>&1 &
ADAPTER_PID=$!
echo "Started adapter with PID: $ADAPTER_PID"

# Wait for startup
sleep 5

# Check health
if ! curl -s http://localhost:8003/health > /dev/null; then
    echo "ERROR: Adapter failed to start"
    cat /tmp/guarded_adapter.log
    kill $ADAPTER_PID 2>/dev/null || true
    exit 1
fi

echo "Adapter is healthy, running tests..."

# Run tests
python3 test_real_integration.py
TEST_EXIT=$?

# Cleanup
kill $ADAPTER_PID 2>/dev/null || true

exit $TEST_EXIT
