#!/bin/bash
#
# Hybrid Adapter Test Script
# Demonstrates toggling between MOCK and REAL ChatDev Money execution
#

set -e

ADAPTER_DIR="/root/.openclaw/workspace/agent-world/backend"
ADAPTER_URL="http://localhost:8002"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Hybrid Adapter Mode Test                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Function to start adapter
start_adapter() {
    local mode=$1
    echo "🚀 Starting adapter in $mode mode..."
    
    cd $ADAPTER_DIR
    if [ "$mode" == "MOCK" ]; then
        USE_REAL_CHATDEV=false python3 hybrid_adapter.py > /tmp/adapter.log 2>&1 &
    else
        USE_REAL_CHATDEV=true python3 hybrid_adapter.py > /tmp/adapter.log 2>&1 &
    fi
    
    ADAPTER_PID=$!
    echo "   PID: $ADAPTER_PID"
    
    # Wait for startup
    sleep 2
    
    # Check health
    for i in {1..5}; do
        if curl -s $ADAPTER_URL/health > /dev/null 2>&1; then
            echo "   ✅ Adapter ready"
            return 0
        fi
        sleep 1
    done
    
    echo "   ❌ Adapter failed to start"
    return 1
}

# Function to stop adapter
stop_adapter() {
    if [ -n "$ADAPTER_PID" ]; then
        echo "🛑 Stopping adapter (PID: $ADAPTER_PID)..."
        kill $ADAPTER_PID 2>/dev/null || true
        wait $ADAPTER_PID 2>/dev/null || true
        ADAPTER_PID=""
    fi
}

# Cleanup on exit
trap stop_adapter EXIT

echo "════════════════════════════════════════════════════════════════"
echo "TEST 1: MOCK Mode (Simulation)"
echo "════════════════════════════════════════════════════════════════"
echo ""

start_adapter "MOCK"

echo "📡 Checking mode endpoint..."
curl -s $ADAPTER_URL/mode | jq .

echo ""
echo "🧪 Running demo workflow (simulated)..."
echo "   This uses the mock engine to simulate Scout→Maker→Merchant"
echo ""

RESULT=$(curl -s $ADAPTER_URL/prototype/demo)
echo $RESULT | jq '.run | {run_id, status, engine, progress, revenue: .outputs.estimated_revenue}'

echo ""
echo "✅ MOCK mode test complete"
echo ""

stop_adapter
sleep 1

echo "════════════════════════════════════════════════════════════════"
echo "TEST 2: REAL Mode (Live ChatDev Money)"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  Note: This requires ChatDev Money to be running on port 8000"
echo ""

# Check if ChatDev is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ ChatDev Money detected on port 8000"
    
    start_adapter "REAL"
    
    echo "📡 Checking mode endpoint..."
    curl -s $ADAPTER_URL/mode | jq .
    
    echo ""
    echo "🧪 Starting REAL workflow execution..."
    echo "   This will call actual ChatDev Money API"
    echo ""
    
    # Start a workflow
    START_RESULT=$(curl -s -X POST $ADAPTER_URL/prototype/start \
        -H "Content-Type: application/json" \
        -d '{
            "room_id": "test-room-real", 
            "user_id": "test-user",
            "workflow_id": "content_arbitrage_v1",
            "subreddit": "entrepreneur",
            "min_upvotes": 200
        }')
    
    echo "Start result:"
    echo $START_RESULT | jq .
    
    RUN_ID=$(echo $START_RESULT | jq -r '.run_id')
    
    if [ "$RUN_ID" != "null" ] && [ -n "$RUN_ID" ]; then
        echo ""
        echo "⏳ Polling status for $RUN_ID..."
        
        for i in {1..20}; do
            STATUS=$(curl -s $ADAPTER_URL/prototype/status/$RUN_ID)
            PROGRESS=$(echo $STATUS | jq -r '.progress')
            STEP=$(echo $STATUS | jq -r '.current_step // "starting"')
            echo "   Poll $i: $PROGRESS% - $STEP"
            
            if [ "$(echo $STATUS | jq -r '.status')" == "completed" ]; then
                echo ""
                echo "✅ Workflow completed!"
                echo $STATUS | jq '.outputs | {revenue: .estimated_revenue, platform: .platform, url: .published_url}'
                break
            fi
            
            sleep 2
        done
    else
        echo "❌ Failed to start workflow"
        echo $START_RESULT
    fi
    
    stop_adapter
else
    echo "⚠️  ChatDev Money not detected on port 8000"
    echo "   Skipping REAL mode test"
    echo ""
    echo "To test REAL mode:"
    echo "   1. cd /root/.openclaw/workspace/chatdev-money"
    echo "   2. python server_main.py"
    echo "   3. Re-run this test script"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "SUMMARY"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "The hybrid adapter supports both modes:"
echo ""
echo "MOCK Mode (default):"
echo "  USE_REAL_CHATDEV=false"
echo "  - Fast simulation for testing"
echo "  - No external dependencies"
echo "  - Predictable outputs"
echo ""
echo "REAL Mode:"
echo "  USE_REAL_CHATDEV=true"
echo "  - Connects to live ChatDev Money"
echo "  - Actual tool execution"
echo "  - Real API calls"
echo ""
echo "Toggle command:"
echo "  USE_REAL_CHATDEV=true python hybrid_adapter.py"
echo ""
