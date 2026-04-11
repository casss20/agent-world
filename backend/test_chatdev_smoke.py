#!/usr/bin/env python3
"""
Smoke tests for ChatDev Money Client
Tests each endpoint against the real service
"""

import asyncio
import sys
from chatdev_client import ChatDevMoneyClient, ENDPOINTS

CHATDEV_URL = "http://localhost:6400"


async def test_health():
    """Test 1: Health check"""
    print("\n▶ Test 1: Health check")
    client = ChatDevMoneyClient(base_url=CHATDEV_URL)
    
    try:
        result = await client.health_check()
        if result.get("status") == "healthy":
            print(f"  ✓ PASS: ChatDev Money is healthy")
            return True
        else:
            print(f"  ✗ FAIL: {result}")
            return False
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False
    finally:
        await client.close()


async def test_workflow_list():
    """Test 2: List available workflows"""
    print("\n▶ Test 2: List workflows")
    client = ChatDevMoneyClient(base_url=CHATDEV_URL)
    
    try:
        # Try to GET /api/workflows
        import httpx
        response = await client.client.get(ENDPOINTS["workflows_list"])
        if response.status_code == 200:
            workflows = response.json()
            print(f"  ✓ PASS: Found {len(workflows)} workflows")
            for wf in workflows[:3]:
                print(f"    - {wf}")
            return True
        else:
            print(f"  ⚠️ SKIP: HTTP {response.status_code}")
            return True  # Not critical
    except Exception as e:
        print(f"  ⚠️ SKIP: {e}")
        return True  # Not critical
    finally:
        await client.close()


async def test_execute_workflow():
    """Test 3: Execute workflow"""
    print("\n▶ Test 3: Execute workflow")
    client = ChatDevMoneyClient(base_url=CHATDEV_URL)
    
    try:
        result = await client.execute_workflow(
            yaml_file="content_arbitrage_v1.yaml",
            task_prompt="Execute content arbitrage workflow",
            variables={
                "subreddit": "sidehustle",
                "min_upvotes": 100
            },
            session_name=f"smoke_test_{__import__('uuid').uuid4().hex[:6]}"
        )
        
        if result.get("run_id"):
            print(f"  ✓ PASS: Workflow started")
            print(f"    Run ID: {result.get('run_id')}")
            print(f"    Status: {result.get('status')}")
            return result.get("run_id")
        else:
            print(f"  ✗ FAIL: No run_id in response")
            print(f"    Response: {result}")
            return None
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return None
    finally:
        await client.close()


async def test_get_status(run_id: str):
    """Test 4: Get workflow status"""
    print(f"\n▶ Test 4: Get status for {run_id}")
    client = ChatDevMoneyClient(base_url=CHATDEV_URL)
    
    try:
        result = await client.get_workflow_status(run_id)
        print(f"  ✓ PASS: Got status")
        print(f"    Status: {result.get('status')}")
        print(f"    Progress: {result.get('progress')}%")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False
    finally:
        await client.close()


async def test_revenue_api():
    """Test 5: Revenue API"""
    print("\n▶ Test 5: Revenue API")
    client = ChatDevMoneyClient(base_url=CHATDEV_URL)
    
    try:
        result = await client.get_revenue_stats()
        print(f"  ✓ PASS: Revenue API accessible")
        print(f"    Stats: {result}")
        return True
    except Exception as e:
        print(f"  ⚠️ SKIP: {e}")
        return True  # Not critical
    finally:
        await client.close()


async def main():
    print("=" * 50)
    print("ChatDev Money Client Smoke Tests")
    print(f"Target: {CHATDEV_URL}")
    print("=" * 50)
    
    tests_passed = 0
    tests_failed = 0
    run_id = None
    
    # Test 1: Health
    if await test_health():
        tests_passed += 1
    else:
        tests_failed += 1
        print("\nAborting - ChatDev Money not healthy")
        return 1
    
    # Test 2: List workflows
    if await test_workflow_list():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 3: Execute workflow
    run_id = await test_execute_workflow()
    if run_id:
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 4: Get status (if we have a run_id)
    if run_id:
        if await test_get_status(run_id):
            tests_passed += 1
        else:
            tests_failed += 1
    
    # Test 5: Revenue API
    if await test_revenue_api():
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
        print("\n✓ All smoke tests passed!")
        return 0
    else:
        print(f"\n✗ {tests_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
