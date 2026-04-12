#!/usr/bin/env python3
"""
FAST Load Test: 100 Concurrent Workflows — Quick Validation
Reduced hold times for rapid feedback (2-3 min total)
"""

import asyncio
import time
import statistics
import json
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import httpx

ADAPTER_URL = "http://localhost:8003"
CHATDEV_URL = "http://localhost:6400"

# FAST CONFIG - Reduced hold times
HOLD_TIME_PER_LEVEL = 30   # 30 seconds (was 300)
SOAK_TEST_DURATION = 60    # 1 minute (was 1800)
LOAD_LEVELS = [10, 25, 50, 100]  # Removed 150 for speed

# SLA Targets
SLA_P95_MS = 1000
SLA_P99_MS = 2000
SLA_ERROR_RATE = 0.01

@dataclass
class TestResult:
    workflow_id: str
    phase: str
    latency_ms: float
    error: bool
    error_message: Optional[str] = None

@dataclass
class PhaseSummary:
    phase: str
    n_workflows: int
    duration_seconds: float
    successful: int
    failed: int
    error_rate: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    throughput_per_sec: float

async def run_workflow(workflow_idx: int, phase: str, room_id: str) -> TestResult:
    start = time.time()
    workflow_id = f"{phase}-{workflow_idx}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{ADAPTER_URL}/guarded/launch",
                headers={"X-Correlation-Id": workflow_id},
                json={
                    "room_id": room_id,
                    "user_id": "load-test",
                    "workflow_id": "content_arbitrage_v1",
                    "subreddit": "sidehustle",
                    "min_upvotes": 100
                }
            )
            
            if response.status_code != 200:
                return TestResult(
                    workflow_id=workflow_id,
                    phase=phase,
                    latency_ms=(time.time() - start) * 1000,
                    error=True,
                    error_message=f"HTTP {response.status_code}"
                )
            
            result = response.json()
            run_id = result.get("run_id")
            
            if not run_id:
                return TestResult(
                    workflow_id=workflow_id,
                    phase=phase,
                    latency_ms=(time.time() - start) * 1000,
                    error=True,
                    error_message="No run_id"
                )
            
            # Quick status check
            await asyncio.sleep(0.5)
            status_resp = await client.get(
                f"{ADAPTER_URL}/guarded/status/{run_id}",
                headers={"X-Correlation-Id": workflow_id}
            )
            
            return TestResult(
                workflow_id=workflow_id,
                phase=phase,
                latency_ms=(time.time() - start) * 1000,
                error=False
            )
            
    except Exception as e:
        return TestResult(
            workflow_id=workflow_id,
            phase=phase,
            latency_ms=(time.time() - start) * 1000,
            error=True,
            error_message=str(e)[:100]
        )

async def run_phase(n_workflows: int, hold_time: int = 30) -> PhaseSummary:
    print(f"\n{'='*60}")
    print(f"PHASE: {n_workflows} workflows ({hold_time}s hold)")
    print(f"{'='*60}")
    
    phase_start = time.time()
    
    # Launch workflows
    tasks = []
    for i in range(n_workflows):
        room_id = f"load-{n_workflows}-{i}"
        task = run_workflow(i, f"phase_{n_workflows}", room_id)
        tasks.append(task)
        if i % 10 == 0:
            await asyncio.sleep(0.02)
    
    print(f"  Launching {n_workflows} workflows...")
    results = await asyncio.gather(*tasks)
    
    # Hold
    if hold_time > 0:
        print(f"  Holding {hold_time}s...", end="", flush=True)
        for i in range(hold_time):
            await asyncio.sleep(1)
            if i % 10 == 0:
                print(".", end="", flush=True)
        print()
    
    phase_duration = time.time() - phase_start
    
    # Calculate metrics
    successful = [r for r in results if not r.error]
    failed = [r for r in results if r.error]
    latencies = [r.latency_ms for r in successful]
    
    summary = PhaseSummary(
        phase=f"phase_{n_workflows}",
        n_workflows=n_workflows,
        duration_seconds=phase_duration,
        successful=len(successful),
        failed=len(failed),
        error_rate=len(failed) / n_workflows * 100 if n_workflows > 0 else 0,
        p50_ms=statistics.median(latencies) if latencies else 0,
        p95_ms=sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 20 else (max(latencies) if latencies else 0),
        p99_ms=sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) >= 100 else (max(latencies) if latencies else 0),
        throughput_per_sec=n_workflows / phase_duration if phase_duration > 0 else 0
    )
    
    print(f"  Results: {summary.successful}/{n_workflows} success")
    print(f"  Error rate: {summary.error_rate:.2f}%")
    print(f"  Latency: p50={summary.p50_ms:.0f}ms, p95={summary.p95_ms:.0f}ms, p99={summary.p99_ms:.0f}ms")
    print(f"  Throughput: {summary.throughput_per_sec:.1f}/sec")
    
    sla_pass = summary.p95_ms < SLA_P95_MS and summary.p99_ms < SLA_P99_MS and summary.error_rate < 1.0
    print(f"  SLA: {'✅ PASS' if sla_pass else '❌ FAIL'}")
    
    return summary

async def main():
    print("="*60)
    print("AgentVerse FAST Load Test (2-3 minutes)")
    print("="*60)
    print(f"Target: 100 workflows | SLA: p95<{SLA_P95_MS}ms, p99<{SLA_P99_MS}ms")
    
    # Check services
    async with httpx.AsyncClient() as client:
        adapter = await client.get(f"{ADAPTER_URL}/health")
        chatdev = await client.get(f"{CHATDEV_URL}/health")
        print(f"\nAdapter: {'✅' if adapter.status_code == 200 else '❌'}")
        print(f"ChatDev: {'✅' if chatdev.status_code == 200 else '❌'}")
        if adapter.status_code == 200:
            data = adapter.json()
            print(f"  Mode: {data.get('engine_mode', 'unknown')}")
    
    summaries = []
    
    # Stepwise load
    for level in LOAD_LEVELS:
        summary = await run_phase(level, hold_time=HOLD_TIME_PER_LEVEL)
        summaries.append(summary)
        await asyncio.sleep(2)
    
    # Generate report
    target = summaries[-1]  # 100 workflow result
    
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": "MOCK",
        "target_workflows": 100,
        "phase_results": [asdict(s) for s in summaries],
        "final_assessment": {
            "p95_ms": target.p95_ms,
            "p99_ms": target.p99_ms,
            "error_rate": target.error_rate,
            "p95_within_sla": target.p95_ms < SLA_P95_MS,
            "p99_within_sla": target.p99_ms < SLA_P99_MS,
            "error_within_sla": target.error_rate < 1.0,
        }
    }
    
    with open("load_test_fast_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Final verdict
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    p95_ok = target.p95_ms < SLA_P95_MS
    p99_ok = target.p99_ms < SLA_P99_MS
    error_ok = target.error_rate < 1.0
    
    print(f"\n100 Workflows:")
    print(f"  p95 latency: {target.p95_ms:.0f}ms {'✅' if p95_ok else '❌'}")
    print(f"  p99 latency: {target.p99_ms:.0f}ms {'✅' if p99_ok else '❌'}")
    print(f"  Error rate: {target.error_rate:.2f}% {'✅' if error_ok else '❌'}")
    print(f"  Throughput: {target.throughput_per_sec:.1f}/sec")
    
    if p95_ok and p99_ok and error_ok:
        print("\n✅ PASS: System handles 100 concurrent workflows")
        print("   with acceptable latency and error rate.")
        print("   Note: MOCK mode - real LLM execution not tested.")
        return 0
    else:
        print("\n❌ FAIL: Bottlenecks detected.")
        if not p95_ok:
            print(f"   - p95 latency {target.p95_ms:.0f}ms exceeds {SLA_P95_MS}ms")
        if not p99_ok:
            print(f"   - p99 latency {target.p99_ms:.0f}ms exceeds {SLA_P99_MS}ms")
        if not error_ok:
            print(f"   - Error rate {target.error_rate:.2f}% exceeds 1%")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
