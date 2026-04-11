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

---

## Enhanced Requirements (Post-Research)

**Sources:** MLJAR Deployment Readiness Chain, RadView Load Testing Guide, Merge.dev Polling Best Practices

### Deployment Readiness Checklist (MLJAR)

Before claiming 100+ workflow readiness, verify all 7 gates:

| Gate | Requirement | Validation Method |
|------|-------------|-------------------|
| 1. Model Validation | Golden dataset outputs match ±1e-5 | Mock workflow deterministic output check |
| 2. API Contract | Valid/invalid/edge/concurrent requests handled | `test_api_contract.py` |
| 3. Load Testing | 5-min test at 2× expected peak (200 workflows), p99 within SLA, error rate <0.1% | `load_test_100.py` extended |
| 4. Rollback Plan | Rollback to previous version in <5 minutes, verified in staging | Document + test |
| 5. Monitoring | Dashboards: request rate, error rate, p50/p95/p99 latency, resource utilization | Grafana JSON |
| 6. Runbook | Deployment steps, expected logs, verification, known issues, escalation path | `RUNBOOK.md` |
| 7. Sign-off | Engineering + SRE + Product approval required | Checklist template |

**Current Gap:** Gates 3, 4, 5, 6, 7 not yet implemented.

### Load Testing Best Practices (RadView)

**Downtime Cost Context:**
- $300K-$5M per hour for enterprise outages
- 90% of mid/large enterprises affected
- False confidence from incomplete testing is worse than no testing

**Requirements for Valid Load Test:**

1. **Realistic Traffic Patterns** (Not Uniform Ramp)
   - Variable concurrent users (burst patterns)
   - Session duration distributions
   - Request mix variations
   - Geographic distribution simulation

2. **Acceptance Thresholds Defined Before Testing**
   - p99 latency SLA: 2000ms (warning), 5000ms (critical)
   - Error rate: <0.1% (pass), >1% (fail)
   - Memory growth: <10% over 30-min test
   - CPU: <70% sustained

3. **Dynamic Baselines**
   - Minimum 8-12 load test runs to establish baseline
   - 2 standard deviations from baseline = anomaly
   - AI-assisted anomaly detection for trend analysis

### Polling Optimization (Merge.dev)

**Current:** 5-second fixed polling intervals

**Optimized Approach:**

| Data Change Frequency | Polling Interval | Rationale |
|----------------------|------------------|-----------|
| Workflow status (fast) | 2s initial, 5s after 30s, 10s after 2min | Exponential backoff |
| Revenue tracking (slow) | 60s | Data changes infrequently |
| Health checks | 30s with 5s caching | Reduce redundant calls |

**Exponential Backoff on Errors:**
```python
# On 5xx errors: 1s → 2s → 4s → 8s → max 30s
# On 429 rate limit: respect Retry-After header
# On timeout: immediate retry once, then backoff
```

**Error Handling Workflow:**
1. Classify error (transient vs persistent)
2. Transient: exponential backoff retry
3. Persistent: circuit breaker open, fallback to mock
4. Alert on persistent errors after 3 failures

### Webhook vs Polling Decision Matrix

| Scenario | Recommendation | Implementation |
|----------|---------------|----------------|
| <50 workflows | Polling acceptable | Optimized intervals above |
| 50-200 workflows | Hybrid (poll short, webhook long) | Short poll for first 30s, then webhook |
| >200 workflows | Webhooks required | `/webhooks/chatdev/events` endpoint |
| Real-time requirements | Webhooks only | <100ms delivery target |

### CI/CD Integration (NIST DevOps Best Practices)

**Shift-Left Performance Testing:**
- Run micro-load test (50 concurrent) on every PR
- Block merge if p95 latency >20% baseline
- AI root-cause analysis on failure

**Pipeline Configuration:**
```yaml
performance_gate:
  trigger: merge_to_staging
  test: 5_min_2x_peak_load
  pass_criteria:
    - p99_latency < 2000ms
    - error_rate < 0.1%
    - memory_stable: true
  fail_action: block_promotion
  notify: performance_engineer
```

### Bottleneck Classification (Salesforce AI Analysis Pattern)

**Decision Matrix for Anomaly Classification:**

| Symptom Combination | Classification | Likely Fix |
|---------------------|----------------|------------|
| CPU >85% + p99 >800ms | Compute-bound | Scale horizontally, optimize code |
| DB query time >200ms for >5% requests | I/O-bound | Connection pooling, query optimization |
| Packet loss >0.1% under load | Network-bound | Check network config, reduce payload size |
| Thread pool exhaustion + 503 errors | Application-layer | Increase pool size, add queue |
| Memory growth >10% over 30min | Memory leak | Profile, fix leak, restart |
| SQLite queue depth >1000 | Database contention | Batch writes, add write replica |

### Predictive Capacity Planning

**AI Model Training Requirements:**
- 8-12 load test runs with varied traffic profiles
- 4-6 weeks production traffic data
- Include failure scenarios, not just happy-path

**Forecasting Outputs:**
- Nonlinear inflection points (e.g., "latency spikes at 650 concurrent users")
- Capacity ceiling predictions
- Time-to-SLA-breach estimates

**Infrastructure Cost Optimization:**
- Target: 30-75% reduction in over-provisioned capacity
- Method: Predictive scaling vs buffer-based provisioning

### Updated Success Criteria (Stricter)

#### Week 1 Validated ONLY If:
- [ ] 8+ baseline runs completed
- [ ] 5-minute sustained test at 200 workflows (2× target)
- [ ] p99 latency <2000ms at 200 workflows
- [ ] Error rate <0.1% (not <5%)
- [ ] Memory stable (no growth >10% over 30min)
- [ ] Recovery <30s after overload
- [ ] Rollback procedure tested and documented
- [ ] All 7 MLJAR gates pass

#### Proceed to Phase 2 (Webhooks) If:
- [ ] p99 >500ms at 100 workflows (polling overhead confirmed)
- [ ] Adapter CPU >50% at 100 workflows
- [ ] Connection pool exhaustion observed

#### Skip to Phase 3 (Event Sourcing) If:
- [ ] SQLite bottleneck at <150 workflows
- [ ] PostgreSQL pool exhaustion
- [ ] Write latency >50ms sustained

### Risk-Weighted Coverage Strategy

**Don't test everything. Test what matters:**

| Priority | Endpoint/Flow | Coverage Level |
|----------|--------------|----------------|
| P0 | `/guarded/launch` | 100% - every test |
| P0 | `/guarded/status/{id}` | 100% - every test |
| P1 | `/guarded/cancel/{id}` | 20% - spot checks |
| P1 | `/guarded/audit/{id}` | 20% - spot checks |
| P2 | Revenue tracking | 10% - periodic |
| P2 | Health endpoints | 5% - smoke tests |

### Resource Checklist for Execution

**Before Running Load Test:**
- [ ] Dedicated test environment (not shared with dev)
- [ ] Monitoring stack: Prometheus + Grafana
- [ ] Log aggregation (centralized)
- [ ] Alert channels configured (Slack/PagerDuty)
- [ ] Rollback procedure documented and tested
- [ ] Runbook created
- [ ] Team on-call notified
- [ ] Database backups current

**During Test:**
- [ ] Real-time dashboard visible
- [ ] Log tail active
- [ ] Kill switch ready (`pkill -f load_test`)
- [ ] Resource metrics recording

**After Test:**
- [ ] Results archived with timestamp
- [ ] Anomaly report generated
- [ ] Bottleneck classification completed
- [ ] Fix tickets created
- [ ] Baseline updated if improved

### Go/No-Go Decision Framework

**GO Criteria (All Required):**
1. All P0 flows pass at 200 workflows
2. p99 latency <2000ms
3. Error rate <0.1%
4. No memory leaks detected
5. Rollback tested and <5 minutes
6. Monitoring dashboards confirmed working
7. Runbook reviewed and approved

**NO-GO Triggers (Any One):**
1. p99 latency >5000ms
2. Error rate >1%
3. Memory growth >20%
4. CPU saturation >90%
5. Database connection pool exhaustion
6. Circuit breakers firing consistently
7. Recovery time >60 seconds

**Conditional GO (With Mitigation):**
- p99 2000-5000ms: Optimize before claiming 100+ readiness
- Error rate 0.1-1%: Investigate root cause, retry test
- Recovery 30-60s: Acceptable with documented workaround

### Files to Create Before Production

1. `test_api_contract.py` - API contract verification
2. `RUNBOOK.md` - Deployment and incident response
3. `grafana-dashboard.json` - Monitoring dashboards
4. `alerts.yml` - AlertManager rules
5. `rollback_test.sh` - Automated rollback verification
6. `signoff_checklist.md` - Go/no-go sign-off template

---

## Summary: From Research to Practice

**What Changes Based on Research:**

| Aspect | Original Plan | Enhanced Plan |
|--------|--------------|---------------|
| Target load | 100 workflows | 200 workflows (2× peak) |
| Test duration | Spot checks | 5-minute sustained |
| Error threshold | <5% | <0.1% |
| Success criteria | 4 metrics | 7 MLJAR gates |
| Monitoring | Basic | Full Prometheus/Grafana |
| Rollback | Not mentioned | <5min, tested, documented |
| Baseline | Single run | 8-12 runs minimum |
| Bottleneck diag | Ad-hoc | Structured classification |

**Immediate Actions:**

1. Extend `load_test_100.py` to 200 workflows, 5-minute sustained
2. Add exponential backoff to polling logic
3. Create API contract test suite
4. Set up Prometheus + Grafana
5. Document rollback procedure
6. Create runbook template
7. Schedule formal load test session

**Research-Validated Assumptions:**
- ✅ Connection pooling reduces latency (industry standard)
- ✅ Batched writes reduce contention (documented pattern)
- ⚠️ Polling becomes bottleneck at ~100 workflows (theoretical, needs proof)
- ⚠️ Webhooks required for >200 workflows (common threshold)
- ⚠️ 8-12 runs needed for reliable baseline (AI training requirement)

**Key Insight:** Don't claim readiness without sustained load test, rollback verification, and monitoring in place. False confidence is worse than known gaps.
