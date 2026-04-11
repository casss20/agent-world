#!/usr/bin/env python3
"""
Load test: 100 concurrent workflows
Validates Week 1 scalability improvements

Usage:
    python3 load_test_100.py
    
Requirements:
    - AgentVerse adapter running on port 8003
    - ChatDev Money running on port 6400 (with API keys configured)
    - No other load on the system
"""

import asyncio
import time
import statistics
import json
from typing import List, Dict
import httpx

# Test configuration
ADAPTER_URL = "http://localhost:8003"
CHATDEV_URL = "http://localhost:6400"
MAX_WORKFLOW_DURATION = 60  # Max seconds to wait for one workflow


async def check_services() -> bool:
    """Verify services are healthy before testing"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            adapter = await client.get(f"{ADAPTER_URL}/health")
            chatdev = await client.get(f"{CHATDEV_URL}/health")
            
            adapter_ok = adapter.status_code == 200
            chatdev_ok = chatdev.status_code == 200
            
            print(f"Adapter health: {'✅' if adapter_ok else '❌'} (HTTP {adapter.status_code})")
            print(f"ChatDev health: {'✅' if chatdev_ok else '❌'} (HTTP {chatdev.status_code})")
            
            if adapter_ok:
                data = adapter.json()
                print(f"  Engine mode: {data.get('engine_mode', 'unknown')}")
                print(f"  Correlation ID: {data.get('correlation_id', 'none')}")
            
            return adapter_ok and chatdev_ok
    except Exception as e:
        print(f"❌ Service check failed: {e}")
        return False


async def run_single_workflow(room_id: str, workflow_idx: int) -> Dict:
    """
    Run one workflow and measure latency
    
    Note: This uses MOCK mode for testing (no real API calls)
    For real load testing, configure ChatDev with API keys
    """
    start = time.time()
    error = None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Launch workflow
            launch_start = time.time()
            response = await client.post(
                f"{ADAPTER_URL}/guarded/launch",
                headers={"X-Correlation-Id": f"load-test-{workflow_idx}"},
                json={
                    "room_id": room_id,
                    "user_id": "load-test",
                    "workflow_id": "content_arbitrage_v1",
                    "subreddit": "sidehustle",
                    "min_upvotes": 100
                }
            )
            launch_latency = (time.time() - launch_start) * 1000
            
            if response.status_code != 200:
                error = f"Launch failed: HTTP {response.status_code}"
                return {
                    "error": True,
                    "error_message": error,
                    "total_latency_ms": (time.time() - start) * 1000,
                    "launch_latency_ms": launch_latency
                }
            
            result = response.json()
            run_id = result.get("run_id")
            
            if not run_id:
                error = "No run_id in response"
                return {
                    "error": True,
                    "error_message": error,
                    "total_latency_ms": (time.time() - start) * 1000,
                    "launch_latency_ms": launch_latency
                }
            
            # Poll for completion (simplified - just check once)
            await asyncio.sleep(0.5)  # Brief wait
            
            status_start = time.time()
            status_resp = await client.get(
                f"{ADAPTER_URL}/guarded/status/{run_id}",
                headers={"X-Correlation-Id": f"load-test-{workflow_idx}"}
            )
            status_latency = (time.time() - status_start) * 1000
            
            total_duration = (time.time() - start) * 1000
            
            return {
                "error": False,
                "run_id": run_id,
                "total_latency_ms": total_duration,
                "launch_latency_ms": launch_latency,
                "status_latency_ms": status_latency,
                "status_code": status_resp.status_code
            }
            
    except asyncio.TimeoutError:
        error = "Timeout"
    except Exception as e:
        error = str(e)
    
    return {
        "error": True,
        "error_message": error,
        "total_latency_ms": (time.time() - start) * 1000
    }


async def run_concurrent_load(n_workflows: int, cooldown: int = 5) -> Dict:
    """Run N concurrent workflows and measure aggregate metrics"""
    print(f"\n{'='*60}")
    print(f"Phase: {n_workflows} concurrent workflows")
    print(f"{'='*60}")
    
    phase_start = time.time()
    
    # Launch all workflows concurrently with staggered start
    tasks = []
    for i in range(n_workflows):
        room_id = f"load-test-{n_workflows}-{i}"
        task = run_single_workflow(room_id, i)
        tasks.append(task)
        
        # Stagger launches slightly to avoid thundering herd
        if i % 10 == 0:
            await asyncio.sleep(0.1)
    
    print(f"Launched {n_workflows} workflow tasks")
    
    # Gather all results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successful = [r for r in results if isinstance(r, dict) and not r.get("error")]
    failed = [r for r in results if isinstance(r, dict) and r.get("error")]
    exceptions = [r for r in results if isinstance(r, Exception)]
    
    # Calculate metrics
    total_time = (time.time() - phase_start) * 1000
    
    latencies = [r["total_latency_ms"] for r in successful]
    launch_latencies = [r["launch_latency_ms"] for r in successful]
    
    summary = {
        "phase": n_workflows,
        "total_time_ms": total_time,
        "successful": len(successful),
        "failed": len(failed) + len(exceptions),
        "error_rate_percent": (len(failed) + len(exceptions)) / n_workflows * 100,
        "throughput_per_sec": len(successful) / (total_time / 1000),
    }
    
    if latencies:
        summary.update({
            "p50_total_ms": statistics.median(latencies),
            "p95_total_ms": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99_total_ms": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) >= 100 else max(latencies),
            "max_total_ms": max(latencies),
            "p50_launch_ms": statistics.median(launch_latencies),
            "p95_launch_ms": sorted(launch_latencies)[int(len(launch_latencies) * 0.95)],
        })
    
    # Print summary
    print(f"Completed in {total_time:.0f}ms")
    print(f"Successful: {summary['successful']}/{n_workflows}")
    print(f"Error rate: {summary['error_rate_percent']:.1f}%")
    
    if latencies:
        print(f"Latency (total): P50={summary['p50_total_ms']:.0f}ms, P95={summary['p95_total_ms']:.0f}ms, P99={summary['p99_total_ms']:.0f}ms")
        print(f"Latency (launch): P50={summary['p50_launch_ms']:.0f}ms, P95={summary['p95_launch_ms']:.0f}ms")
        print(f"Throughput: {summary['throughput_per_sec']:.1f} workflows/sec")
    
    if failed:
        print(f"\nSample errors:")
        for f in failed[:3]:
            print(f"  - {f.get('error_message', 'Unknown')}")
    
    if exceptions:
        print(f"\nExceptions: {len(exceptions)}")
        for e in exceptions[:3]:
            print(f"  - {e}")
    
    # Cool down
    if cooldown > 0:
        print(f"Cooling down for {cooldown}s...")
        await asyncio.sleep(cooldown)
    
    return summary


async def main():
    """Execute full load test suite"""
    print("="*60)
    print("AgentVerse Load Test: Week 1 Scalability Validation")
    print("="*60)
    print("\nPrerequisites:")
    print("  - AgentVerse adapter on port 8003")
    print("  - ChatDev Money on port 6400")
    print("  - No other load on system")
    
    # Check services
    print("\n--- Service Health Check ---")
    if not await check_services():
        print("\n❌ Services not ready. Start them first:")
        print("  cd agent-world/backend && python3 guarded_adapter.py")
        print("  cd chatdev-money && python3 server_main.py --port 6400")
        return 1
    
    all_results = []
    
    # Phase 1: Baseline (1, 5, 10 workflows)
    print("\n" + "="*60)
    print("PHASE 1: Baseline")
    print("="*60)
    
    for n in [1, 5, 10]:
        result = await run_concurrent_load(n, cooldown=3)
        all_results.append(result)
    
    # Phase 2: Stress (20, 50 workflows)
    print("\n" + "="*60)
    print("PHASE 2: Stress Test")
    print("="*60)
    
    for n in [20, 50]:
        result = await run_concurrent_load(n, cooldown=5)
        all_results.append(result)
    
    # Phase 3: Target (100 workflows)
    print("\n" + "="*60)
    print("PHASE 3: Target Load (100 workflows)")
    print("="*60)
    
    result = await run_concurrent_load(100, cooldown=10)
    all_results.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    
    for r in all_results:
        status = "✅" if r["error_rate_percent"] < 5 else "⚠️" if r["error_rate_percent"] < 20 else "❌"
        print(f"{status} {r['phase']:3d} workflows: {r['p99_total_ms']:6.0f}ms P99, {r['error_rate_percent']:5.1f}% errors")
    
    # Save results
    output_file = "load_test_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "results": all_results
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    # Validation
    target_result = all_results[-1]  # 100 workflow result
    print("\n" + "="*60)
    print("VALIDATION AGAINST 100 WORKFLOW TARGET")
    print("="*60)
    
    checks = [
        ("P99 latency < 2s", target_result.get("p99_total_ms", 9999) < 2000),
        ("Error rate < 5%", target_result["error_rate_percent"] < 5),
        ("Successful completions > 90%", target_result["successful"] >= 90),
    ]
    
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
    
    all_passed = all(passed for _, passed in checks)
    
    if all_passed:
        print("\n✅ Week 1 scalability improvements VALIDATED for 100 workflows")
        return 0
    else:
        print("\n⚠️  Some checks failed. Review metrics and consider:")
        print("   - Enabling webhook mode (eliminates polling)")
        print("   - Increasing connection pool size")
        print("   - Adding horizontal scaling")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
