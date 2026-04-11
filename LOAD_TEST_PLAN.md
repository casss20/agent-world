# Load Testing Plan: 100+ Concurrent Workflows

**Objective:** Validate Week 1 scalability improvements under realistic concurrent load

**Status:** Planned, awaiting execution

---

## Test Scenarios

### Phase 1: Baseline (1-10 workflows)
**Purpose:** Establish baseline metrics before optimization

| Metric | Target | Measurement |
|--------|--------|-------------|
| Adapter P50 latency | <100ms | `metrics.get_summary()` |
| Adapter P99 latency | <500ms | `metrics.get_summary()` |
| CPU usage | <30% | `psutil` |
| Memory usage | <400MB | `psutil` |
| SQLite write time | <10ms/event | Custom timer |
| Concurrent polls | <5 active | Counter |

**Test:**
```python
async def test_baseline():
    for n in [1, 5, 10]:
        results = await run_concurrent_workflows(n)
        record_metrics(f"baseline_{n}", results)
```

### Phase 2: Stress Test (20-50 workflows)
**Purpose:** Find first breaking point

| Metric | Target | Fail Threshold |
|--------|--------|----------------|
| Adapter P99 latency | <1s | >2s |
| Error rate | <2% | >5% |
| Event loop lag | <100ms | >500ms |
| SQLite queue depth | <500 | >1000 |

**Test:**
- Ramp from 20 → 50 concurrent workflows over 10 minutes
- Monitor for latency spikes, errors, resource exhaustion
- Identify which component fails first

### Phase 3: Target Load (100 workflows)
**Purpose:** Validate 100+ claim

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Adapter P99 latency | <2s | Prometheus histogram |
| Workflow success rate | >95% | Success counter |
| System CPU | <70% | Node exporter |
| Memory | <2GB | Node exporter |
| Event loop lag | <500ms | `asyncio` monitor |
| No fallback activations | 0% | Fallback counter |

**Test:**
- Sustain 100 concurrent workflows for 30 minutes
- Gradual ramp (100 over 5 minutes)
- Measure steady-state performance

### Phase 4: Overload (150+ workflows)
**Purpose:** Find hard limits

| Observation | Expected |
|-------------|----------|
| Where does it break? | Adapter CPU or SQLite writes |
| Graceful degradation? | Circuit breakers activate |
| Recovery time? | <30s after load reduces |

---

## Test Script: `load_test_100.py`

```python
#!/usr/bin/env python3
"""
Load test: 100 concurrent workflows
Validates Week 1 scalability improvements
"""

import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
import httpx

# Test configuration
ADAPTER_URL = "http://localhost:8003"
CHATDEV_URL = "http://localhost:6400"

async def run_single_workflow(room_id: str) -> Dict:
    """Run one workflow and measure"""
    start = time.time()
    
    async with httpx.AsyncClient() as client:
        # Launch workflow
        response = await client.post(
            f"{ADAPTER_URL}/guarded/launch",
            json={
                "room_id": room_id,
                "user_id": "load-test",
                "workflow_id": "content_arbitrage_v1",
                "subreddit": "sidehustle",
                "min_upvotes": 100
            }
        )
        
        if response.status_code != 200:
            return {"error": True, "latency_ms": (time.time() - start) * 1000}
        
        result = response.json()
        run_id = result.get("run_id")
        
        # Poll for completion (max 60s)
        for _ in range(60):
            await asyncio.sleep(1)
            status_resp = await client.get(
                f"{ADAPTER_URL}/guarded/status/{run_id}"
            )
            if status_resp.status_code == 200:
                status = status_resp.json()
                if status.get("status") in ["completed", "failed"]:
                    break
        
        duration = (time.time() - start) * 1000
        return {
            "error": False,
            "latency_ms": duration,
            "run_id": run_id
        }

async def run_concurrent_load(n_workflows: int) -> Dict:
    """Run N concurrent workflows"""
    print(f"\n{'='*50}")
    print(f"Testing {n_workflows} concurrent workflows")
    print(f"{'='*50}")
    
    start = time.time()
    
    # Launch all workflows concurrently
    tasks = [
        run_single_workflow(f"load-test-{i}")
        for i in range(n_workflows)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analyze results
    latencies = [r["latency_ms"] for r in results if not r.get("error")]
    errors = sum(1 for r in results if r.get("error"))
    
    total_time = (time.time() - start) * 1000
    
    summary = {
        "n_workflows": n_workflows,
        "total_time_ms": total_time,
        "errors": errors,
        "error_rate": errors / n_workflows * 100,
        "p50_latency_ms": statistics.median(latencies) if latencies else 0,
        "p99_latency_ms": sorted(latencies)[int(len(latencies)*0.99)] if latencies else 0,
        "throughput_per_sec": n_workflows / (total_time / 1000)
    }
    
    print(f"Total time: {total_time:.0f}ms")
    print(f"Errors: {errors}/{n_workflows} ({summary['error_rate']:.1f}%)")
    print(f"P50 latency: {summary['p50_latency_ms']:.0f}ms")
    print(f"P99 latency: {summary['p99_latency_ms']:.0f}ms")
    print(f"Throughput: {summary['throughput_per_sec']:.1f} workflows/sec")
    
    return summary

async def main():
    """Run full load test suite"""
    print("="*50)
    print("AgentVerse Load Test: 100 Concurrent Workflows")
    print("="*50)
    
    # Check services are up
    async with httpx.AsyncClient() as client:
        adapter_health = await client.get(f"{ADAPTER_URL}/health")
        chatdev_health = await client.get(f"{CHATDEV_URL}/health")
        
        print(f"\nAdapter: {'✅' if adapter_health.status_code == 200 else '❌'}")
        print(f"ChatDev: {'✅' if chatdev_health.status_code == 200 else '❌'}")
    
    results = []
    
    # Phase 1: Baseline
    for n in [1, 5, 10]:
        result = await run_concurrent_load(n)
        results.append(result)
        await asyncio.sleep(5)  # Cool down
    
    # Phase 2: Stress
    for n in [20, 50]:
        result = await run_concurrent_load(n)
        results.append(result)
        await asyncio.sleep(10)  # Cool down
    
    # Phase 3: Target
    result = await run_concurrent_load(100)
    results.append(result)
    
    # Save results
    import json
    with open("load_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*50)
    print("Load test complete. Results saved to load_test_results.json")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Success Criteria

### Week 1 Improvements Validated If:
- [ ] 100 workflows complete with <5% error rate
- [ ] P99 latency <2s sustained
- [ ] No fallback activations triggered
- [ ] System recovers within 30s after overload

### Phase 2 (Webhooks) Needed If:
- [ ] P99 latency >500ms at 50 workflows
- [ ] Adapter CPU >70% at 100 workflows
- [ ] Event loop lag >100ms

### Phase 3 (Event Sourcing) Needed If:
- [ ] SQLite becomes bottleneck (writes >50ms)
- [ ] PostgreSQL connection pool exhaustion
- [ ] Redis memory >80%

---

## Execution Plan

1. **Set up monitoring:** Prometheus + Grafana for real-time metrics
2. **Run Phase 1:** Validate baseline (<10 workflows)
3. **Run Phase 2:** Find breaking point (20-50 workflows)
4. **Run Phase 3:** Target validation (100 workflows)
5. **Analyze:** Which metric fails first?
6. **Decide:** Proceed to Phase 2 (webhooks) or optimize further?

---

## Current Status

| Component | Theoretical | Tested | Status |
|-----------|-------------|--------|--------|
| Connection pooling | ✅ Should reduce latency | ❌ Not load tested | Pending |
| Batched writes | ✅ Should reduce DB pressure | ❌ Not load tested | Pending |
| Metrics collection | ✅ Working | ✅ Unit tested | Ready |
| **Overall** | Architecture correct | **Needs proof** | **Pending validation** |

**Next action:** Execute load test once OpenAI API credentials configured for ChatDev Money.
