#!/usr/bin/env python3
"""
REAL Mode Integration Test for Guarded Adapter
Tests guarded adapter against REAL ChatDev Money service
"""

import requests
import sys
import time

ADAPTER_URL = "http://localhost:8003"
CHATDEV_URL = "http://localhost:6400"

def test_health_check():
    """Test 1: Health check with correlation ID"""
    print("\n▶ Test 1: Health check with correlation ID")
    
    response = requests.get(
        f"{ADAPTER_URL}/health",
        headers={"X-Correlation-Id": "test-real-001"}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "healthy" and data.get("engine_mode") == "REAL":
            print(f"  ✓ PASS: Health check returns healthy in REAL mode")
            print(f"    Engine: {data.get('engine_mode')}")
            print(f"    Correlation ID: {data.get('correlation_id')}")
            return True
    
    print(f"  ✗ FAIL: {response.text}")
    return False


def test_guarded_launch():
    """Test 2: Guarded workflow launch"""
    print("\n▶ Test 2: Guarded workflow launch")
    
    import uuid
    unique_room = f"test-room-{uuid.uuid4().hex[:8]}"
    
    response = requests.post(
        f"{ADAPTER_URL}/guarded/launch",
        headers={
            "Content-Type": "application/json",
            "X-Correlation-Id": "test-real-002"
        },
        json={
            "room_id": unique_room,
            "user_id": "test-user",
            "workflow_id": "content_arbitrage_v1",
            "subreddit": "sidehustle",
            "min_upvotes": 100
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "launched":
            print(f"  ✓ PASS: Workflow launched")
            print(f"    Run ID: {data.get('run_id')}")
            print(f"    Correlation ID: {data.get('correlation_id')}")
            print(f"    Engine Mode: {data.get('engine_mode')}")
            return data.get("run_id")
    
    print(f"  ✗ FAIL: {response.text}")
    return None


def test_status_polling(run_id):
    """Test 3: Status polling with audit trail"""
    print("\n▶ Test 3: Status polling with audit trail")
    
    max_attempts = 30
    for attempt in range(max_attempts):
        response = requests.get(
            f"{ADAPTER_URL}/guarded/status/{run_id}",
            headers={"X-Correlation-Id": f"test-real-003-{attempt}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            progress = data.get("progress", 0)
            event_count = data.get("event_count", 0)
            
            print(f"  Attempt {attempt + 1}: status={status}, progress={progress}%, events={event_count}")
            
            if status in ["completed", "failed"]:
                if status == "completed":
                    print(f"  ✓ PASS: Workflow completed")
                    print(f"    Final progress: {progress}%")
                    print(f"    Event count: {event_count}")
                    return True
                else:
                    print(f"  ✗ FAIL: Workflow failed")
                    return False
        
        time.sleep(2)
    
    print(f"  ✗ FAIL: Did not complete within timeout")
    return False


def test_audit_trail(run_id):
    """Test 4: Audit trail with correlation IDs"""
    print("\n▶ Test 4: Audit trail with correlation IDs")
    
    response = requests.get(
        f"{ADAPTER_URL}/guarded/audit/{run_id}",
        headers={"X-Correlation-Id": "test-real-004"}
    )
    
    if response.status_code == 200:
        data = response.json()
        event_count = data.get("event_count", 0)
        
        if event_count > 0:
            print(f"  ✓ PASS: Audit trail contains events")
            print(f"    Events recorded: {event_count}")
            
            # Show first few events
            events = data.get("events", [])
            print(f"    Sample events:")
            for event in events[:3]:
                print(f"      - {event.get('event_type')} ({event.get('correlation_id', 'N/A')[:8]})")
            
            return True
    
    print(f"  ✗ FAIL: {response.text}")
    return False


def test_fallback_toggle():
    """Test 5: Runtime engine toggle (fallback)"""
    print("\n▶ Test 5: Runtime engine toggle (fallback)")
    
    # Toggle to MOCK
    response = requests.post(
        f"{ADAPTER_URL}/guarded/toggle-engine?mode=MOCK",
        headers={"X-Correlation-Id": "test-real-005"}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("mode") == "MOCK":
            print(f"  ✓ PASS: Successfully toggled to MOCK mode")
            
            # Toggle back to REAL
            requests.post(
                f"{ADAPTER_URL}/guarded/toggle-engine?mode=REAL",
                headers={"X-Correlation-Id": "test-real-005b"}
            )
            print(f"    (Toggled back to REAL)")
            return True
    
    print(f"  ✗ FAIL: {response.text}")
    return False


def main():
    print("=" * 50)
    print("REAL Mode Integration Test")
    print("=" * 50)
    
    tests_passed = 0
    tests_failed = 0
    run_id = None
    
    # Test 1: Health Check
    if test_health_check():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 2: Guarded Launch
    run_id = test_guarded_launch()
    if run_id:
        tests_passed += 1
    else:
        tests_failed += 1
        print("\nAborting remaining tests (launch failed)")
        sys.exit(1)
    
    # Test 3: Status Polling
    if test_status_polling(run_id):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 4: Audit Trail
    if test_audit_trail(run_id):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 5: Fallback Toggle
    if test_fallback_toggle():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    
    if tests_failed == 0:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {tests_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
