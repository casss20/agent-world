#!/bin/bash
# Real Mode Integration Test for Guarded Adapter
# Tests guarded adapter against REAL ChatDev Money service

set -e

echo "=========================================="
echo "REAL Mode Integration Test"
echo "=========================================="
echo ""

ADAPTER_URL="http://localhost:8003"
CHATDEV_URL="http://localhost:6400"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
TESTS_PASSED=0
TESTS_FAILED=0
CORR_ID=""
RUN_ID=""

test_start() {
    echo -e "${YELLOW}▶ $1${NC}"
}

test_pass() {
    echo -e "${GREEN}✓ PASS: $1${NC}"
    ((TESTS_PASSED++))
}

test_fail() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    echo "  Error: $2"
    ((TESTS_FAILED++))
}

# Test 1: Health Check
test_start "Test 1: Health check with correlation ID"
HEALTH=$(curl -s -H "X-Correlation-Id: test-real-001" "$ADAPTER_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    ENGINE_MODE=$(echo "$HEALTH" | grep -o '"engine_mode":"[^"]*"' | cut -d'"' -f4)
    if [ "$ENGINE_MODE" = "REAL" ]; then
        test_pass "Health check returns healthy in REAL mode"
        echo "  Engine: $ENGINE_MODE"
    else
        test_fail "Health check" "Engine mode is $ENGINE_MODE, expected REAL"
    fi
else
    test_fail "Health check" "$HEALTH"
fi

echo ""

# Test 2: Guarded Launch
test_start "Test 2: Guarded workflow launch"
LAUNCH_RESPONSE=$(curl -s -X POST "$ADAPTER_URL/guarded/launch" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-Id: test-real-002" \
    -d '{
        "room_id": "test-room-001",
        "user_id": "test-user",
        "workflow_id": "content_arbitrage_v1",
        "subreddit": "sidehustle",
        "min_upvotes": 100
    }')

if echo "$LAUNCH_RESPONSE" | grep -q '"status":"launched"'; then
    RUN_ID=$(echo "$LAUNCH_RESPONSE" | grep -o '"run_id":"[^"]*"' | cut -d'"' -f4)
    CORR_ID=$(echo "$LAUNCH_RESPONSE" | grep -o '"correlation_id":"[^"]*"' | cut -d'"' -f4)
    test_pass "Workflow launched"
    echo "  Run ID: $RUN_ID"
    echo "  Correlation ID: $CORR_ID"
else
    test_fail "Workflow launch" "$LAUNCH_RESPONSE"
    exit 1
fi

echo ""

# Test 3: Status Polling with correlation tracking
test_start "Test 3: Status polling with audit trail"
ATTEMPTS=0
MAX_ATTEMPTS=30
COMPLETED=false

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    STATUS=$(curl -s "$ADAPTER_URL/guarded/status/$RUN_ID" \
        -H "X-Correlation-Id: test-real-003")
    
    STATUS_VALUE=$(echo "$STATUS" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    PROGRESS=$(echo "$STATUS" | grep -o '"progress":[0-9]*' | cut -d':' -f2)
    EVENT_COUNT=$(echo "$STATUS" | grep -o '"event_count":[0-9]*' | cut -d':' -f2)
    
    echo "  Attempt $((ATTEMPTS+1)): status=$STATUS_VALUE, progress=$PROGRESS%, events=$EVENT_COUNT"
    
    if [ "$STATUS_VALUE" = "completed" ] || [ "$STATUS_VALUE" = "failed" ]; then
        COMPLETED=true
        break
    fi
    
    sleep 2
    ((ATTEMPTS++))
done

if [ "$COMPLETED" = true ] && [ "$STATUS_VALUE" = "completed" ]; then
    test_pass "Workflow completed through polling"
    echo "  Final progress: $PROGRESS%"
    echo "  Event count: $EVENT_COUNT"
else
    test_fail "Status polling" "Did not complete within timeout"
fi

echo ""

# Test 4: Audit Trail Verification
test_start "Test 4: Audit trail with correlation IDs"
AUDIT=$(curl -s "$ADAPTER_URL/guarded/audit/$RUN_ID" \
    -H "X-Correlation-Id: test-real-004")

if echo "$AUDIT" | grep -q "run"; then
    EVENT_COUNT=$(echo "$AUDIT" | grep -o '"event_count":[0-9]*' | cut -d':' -f2)
    if [ "$EVENT_COUNT" -gt 0 ]; then
        test_pass "Audit trail contains events"
        echo "  Events recorded: $EVENT_COUNT"
    else
        test_fail "Audit trail" "No events recorded"
    fi
else
    test_fail "Audit trail" "Audit not found"
fi

echo ""

# Test 5: Fallback to Mock Mode
test_start "Test 5: Runtime engine toggle (fallback)"
TOGGLE=$(curl -s -X POST "$ADAPTER_URL/guarded/toggle-engine?mode=MOCK" \
    -H "X-Correlation-Id: test-real-005")

if echo "$TOGGLE" | grep -q '"mode":"MOCK"'; then
    test_pass "Successfully toggled to MOCK mode"
    
    # Toggle back to REAL
    curl -s -X POST "$ADAPTER_URL/guarded/toggle-engine?mode=REAL" \
        -H "X-Correlation-Id: test-real-005b" > /dev/null
    echo "  (Toggled back to REAL)"
else
    test_fail "Engine toggle" "$TOGGLE"
fi

echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
