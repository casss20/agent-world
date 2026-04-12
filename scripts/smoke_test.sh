#!/bin/bash
# Ticket 4: Smoke Tests
# Quick validation that deployment is working

set -e

BASE_URL="${1:-http://localhost:8080}"
FAILED=0
PASSED=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

log_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

echo "========================================"
echo "SMOKE TESTS"
echo "Base URL: $BASE_URL"
echo "========================================"

# Test 1: Health endpoint
echo ""
echo "Test 1: Health endpoint"
if curl -sf "$BASE_URL/stateless/health" > /dev/null 2>&1; then
    log_pass "Health check passed"
else
    log_fail "Health check failed"
fi

# Test 2: Metrics endpoint
echo ""
echo "Test 2: Metrics endpoint"
if curl -sf "$BASE_URL/metrics" > /dev/null 2>&1 || \
   curl -sf "http://localhost:8004/metrics" > /dev/null 2>&1; then
    log_pass "Metrics endpoint accessible"
else
    log_fail "Metrics endpoint failed"
fi

# Test 3: Workflow launch
echo ""
echo "Test 3: Workflow launch"
RUN_ID=$(curl -sf -X POST "$BASE_URL/stateless/launch" \
    -H "Content-Type: application/json" \
    -d '{
        "room_id": "smoke_test",
        "user_id": "smoke",
        "workflow_id": "demo_simple_memory",
        "task_prompt": "Smoke test workflow"
    }' 2>/dev/null | \
    python3 -c "import sys,json; print(json.load(sys.stdin).get('run_id',''))" 2>/dev/null || echo "")

if [ -n "$RUN_ID" ]; then
    log_pass "Workflow launched (run_id: ${RUN_ID:0:20}...)"
    
    # Test 4: Status check
    echo ""
    echo "Test 4: Status check"
    sleep 1
    STATUS=$(curl -sf "$BASE_URL/stateless/status/$RUN_ID" 2>/dev/null | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "error")
    
    if [ "$STATUS" != "error" ]; then
        log_pass "Status check passed (status: $STATUS)"
    else
        log_fail "Status check failed"
    fi
else
    log_fail "Workflow launch failed"
fi

# Test 5: Redis connectivity (if available)
echo ""
echo "Test 5: Redis connectivity"
if redis-cli ping > /dev/null 2>&1; then
    log_pass "Redis responding"
else
    log_info "Redis check skipped (not available)"
fi

# Test 6: Load balancer distribution
echo ""
echo "Test 6: Load balancer distribution"
INSTANCES=""
for i in {1..5}; do
    INSTANCE=$(curl -sf "$BASE_URL/stateless/health" 2>/dev/null | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('instance_id','unknown'))" 2>/dev/null || echo "error")
    INSTANCES="$INSTANCES $INSTANCE"
done

UNIQUE=$(echo "$INSTANCES" | tr ' ' '\n' | sort -u | wc -l)
if [ "$UNIQUE" -gt 1 ]; then
    log_pass "Load balancer distributing across $UNIQUE instances"
else
    log_info "Load balancer using single instance (may be expected)"
fi

# Test 7: Security headers
echo ""
echo "Test 7: Security headers"
HEADERS=$(curl -sI "$BASE_URL/stateless/health" 2>/dev/null)
if echo "$HEADERS" | grep -q "X-Content-Type-Options: nosniff"; then
    log_pass "Security headers present"
else
    log_fail "Security headers missing"
fi

# Summary
echo ""
echo "========================================"
echo "SMOKE TEST SUMMARY"
echo "========================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
