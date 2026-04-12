"""
Phase 4 Integration Tests
Test Camofox Browser and Multica integration
"""

import asyncio
import httpx
import sys


async def test_camofox_health():
    """Test Camofox browser health"""
    print("\n" + "="*60)
    print("Test: Camofox Health Check")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://localhost:9377/health")
            if resp.status_code == 200:
                print("✅ Camofox is healthy")
                return True
            else:
                print(f"❌ Camofox unhealthy: {resp.status_code}")
                return False
    except Exception as e:
        print(f"❌ Camofox connection failed: {e}")
        return False


async def test_multica_health():
    """Test Multica health"""
    print("\n" + "="*60)
    print("Test: Multica Health Check")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://localhost:8081/health")
            if resp.status_code == 200:
                print("✅ Multica is healthy")
                return True
            else:
                print(f"❌ Multica unhealthy: {resp.status_code}")
                return False
    except Exception as e:
        print(f"❌ Multica connection failed: {e}")
        return False


async def test_camofox_via_nginx():
    """Test Camofox routing through nginx"""
    print("\n" + "="*60)
    print("Test: Camofox via Nginx (port 8080)")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://localhost:8080/camofox/health")
            if resp.status_code == 200:
                print("✅ Camofox accessible via nginx /camofox/")
                return True
            else:
                print(f"❌ Nginx routing failed: {resp.status_code}")
                return False
    except Exception as e:
        print(f"❌ Nginx connection failed: {e}")
        return False


async def test_multica_via_nginx():
    """Test Multica routing through nginx"""
    print("\n" + "="*60)
    print("Test: Multica via Nginx (port 8080)")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://localhost:8080/multica/health")
            if resp.status_code == 200:
                print("✅ Multica accessible via nginx /multica/")
                return True
            else:
                print(f"❌ Nginx routing failed: {resp.status_code}")
                return False
    except Exception as e:
        print(f"❌ Nginx connection failed: {e}")
        return False


async def test_camofox_client():
    """Test Camofox Python client"""
    print("\n" + "="*60)
    print("Test: Camofox Client")
    print("="*60)
    
    try:
        from camofox_client import CamofoxClient
        
        client = CamofoxClient(base_url="http://localhost:9377")
        healthy = await client.health_check()
        
        if healthy:
            print("✅ CamofoxClient initialized and healthy")
            await client.close()
            return True
        else:
            print("❌ CamofoxClient health check failed")
            return False
            
    except Exception as e:
        print(f"❌ CamofoxClient test failed: {e}")
        return False


async def test_multica_client():
    """Test Multica Python client"""
    print("\n" + "="*60)
    print("Test: Multica Client")
    print("="*60)
    
    try:
        from multica_client import MulticaClient
        
        client = MulticaClient(base_url="http://localhost:8081")
        healthy = await client.health_check()
        
        if healthy:
            print("✅ MulticaClient initialized and healthy")
            await client.close()
            return True
        else:
            print("❌ MulticaClient health check failed")
            return False
            
    except Exception as e:
        print(f"❌ MulticaClient test failed: {e}")
        return False


async def test_adapter_still_works():
    """Verify adapter still functioning"""
    print("\n" + "="*60)
    print("Test: Adapter Health (Regression)")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://localhost:8080/stateless/health")
            if resp.status_code == 200:
                print("✅ Adapter still accessible via nginx")
                return True
            else:
                print(f"❌ Adapter failed: {resp.status_code}")
                return False
    except Exception as e:
        print(f"❌ Adapter test failed: {e}")
        return False


async def run_all_tests():
    """Run all Phase 4 integration tests"""
    print("\n" + "="*60)
    print("PHASE 4 INTEGRATION TESTS")
    print("Camofox Browser + Multica Orchestration")
    print("="*60)
    
    tests = [
        ("Camofox Health", test_camofox_health),
        ("Multica Health", test_multica_health),
        ("Camofox via Nginx", test_camofox_via_nginx),
        ("Multica via Nginx", test_multica_via_nginx),
        ("Camofox Client", test_camofox_client),
        ("Multica Client", test_multica_client),
        ("Adapter Regression", test_adapter_still_works),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            result = await test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("PHASE 4 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{len(tests)} passed")
    
    if failed == 0:
        print("\n🎉 All Phase 4 integration tests passed!")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(result)
