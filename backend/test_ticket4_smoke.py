"""
Smoke Test - Ticket 4
Quick validation that deployment is working
"""

import httpx
import asyncio
import sys

BASE_URL = "http://localhost:8080"


async def run_smoke_tests():
    """Run smoke tests against deployment"""
    print("="*60)
    print("SMOKE TESTS - Ticket 4")
    print(f"Base URL: {BASE_URL}")
    print("="*60)
    
    passed = 0
    failed = 0
    
    async with httpx.AsyncClient() as client:
        # Test 1: Health endpoint
        print("\nTest 1: Health endpoint")
        try:
            resp = await client.get(f"{BASE_URL}/stateless/health", timeout=5.0)
            if resp.status_code == 200:
                print("   ✅ Health check passed")
                passed += 1
            else:
                print(f"   ❌ Health check failed: {resp.status_code}")
                failed += 1
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            failed += 1
        
        # Test 2: Metrics endpoint
        print("\nTest 2: Metrics endpoint")
        try:
            resp = await client.get("http://localhost:8004/metrics", timeout=5.0)
            if resp.status_code == 200:
                print("   ✅ Metrics endpoint accessible")
                passed += 1
            else:
                print(f"   ❌ Metrics failed: {resp.status_code}")
                failed += 1
        except Exception as e:
            print(f"   ❌ Metrics failed: {e}")
            failed += 1
        
        # Test 3: Workflow launch
        print("\nTest 3: Workflow launch")
        run_id = None
        try:
            resp = await client.post(
                f"{BASE_URL}/stateless/launch",
                json={
                    "room_id": "smoke_test",
                    "user_id": "smoke",
                    "workflow_id": "demo_simple_memory",
                    "task_prompt": "Smoke test"
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                run_id = data.get("run_id")
                print(f"   ✅ Workflow launched ({run_id[:20]}...)")
                passed += 1
            else:
                print(f"   ❌ Launch failed: {resp.status_code}")
                failed += 1
        except Exception as e:
            print(f"   ❌ Launch failed: {e}")
            failed += 1
        
        # Test 4: Status check
        if run_id:
            print("\nTest 4: Status check")
            try:
                resp = await client.get(
                    f"{BASE_URL}/stateless/status/{run_id}",
                    timeout=5.0
                )
                if resp.status_code == 200:
                    status = resp.json().get("status")
                    print(f"   ✅ Status check passed ({status})")
                    passed += 1
                else:
                    print(f"   ❌ Status failed: {resp.status_code}")
                    failed += 1
            except Exception as e:
                print(f"   ❌ Status failed: {e}")
                failed += 1
        
        # Test 5: Security headers
        print("\nTest 5: Security headers")
        try:
            resp = await client.get(f"{BASE_URL}/stateless/health")
            if "X-Content-Type-Options" in resp.headers:
                print("   ✅ Security headers present")
                passed += 1
            else:
                print("   ❌ Security headers missing")
                failed += 1
        except Exception as e:
            print(f"   ❌ Security headers check failed: {e}")
            failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("SMOKE TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All smoke tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed")
        return 1


if __name__ == "__main__":
    result = asyncio.run(run_smoke_tests())
    sys.exit(result)
