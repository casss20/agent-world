# Agent World: Production Feedback Loop

**Status**: Implementation Plan  
**Goal**: Closed-loop system for continuous improvement from production traces

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION FEEDBACK LOOP                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   OBSERVE    │───▶│    SCORE     │───▶│    REVIEW    │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                    │                     │
│         ▼                   ▼                    ▼                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   CURATE     │◀───│    PATCH     │◀───│   DATASET    │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                                                          │    │
│         └──────────────────────────────────────────────────────┬───┘    │
│                                                                ▼        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  REDEPLOY  ──▶  MEASURE  ──▶  COMPARE  ──▶  IMPROVE/ROLLBACK   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Telemetry Layer (OBSERVE)

### What to Capture

| Signal | Source | Storage | Retention |
|--------|--------|---------|-----------|
| User input | API request | PostgreSQL + S3 | 90 days |
| Selected engine/path | ExecutionEngine | PostgreSQL | 90 days |
| Tool calls | AgentWorker | OpenTelemetry traces | 30 days |
| Retries | RetryController | Redis + PostgreSQL | 30 days |
| Latency | Telemetry middleware | Prometheus | 15 days |
| Token usage | LLM providers | PostgreSQL | 90 days |
| Output | AgentWorker | PostgreSQL + S3 | 90 days |
| User correction | Frontend | PostgreSQL | 1 year |
| Thumbs up/down | Frontend | PostgreSQL | 1 year |
| Final outcome | Business logic | PostgreSQL | 1 year |

### Database Schema

```sql
-- Production traces table
CREATE TABLE production_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    room_id UUID REFERENCES rooms(id),
    task_id UUID REFERENCES task_queue(id),
    agent_id UUID REFERENCES agents(id),
    
    -- Input/Output
    user_input JSONB,
    system_prompt TEXT,
    tool_calls JSONB[],
    llm_output TEXT,
    final_output JSONB,
    
    -- Execution metadata
    engine_used VARCHAR(50), -- 'langgraph', 'crewai', 'legacy'
    execution_path JSONB,    -- Full routing decisions
    
    -- Performance
    latency_ms INTEGER,
    token_usage_input INTEGER,
    token_usage_output INTEGER,
    retry_count INTEGER DEFAULT 0,
    
    -- Feedback
    user_feedback VARCHAR(20), -- 'thumbs_up', 'thumbs_down', 'corrected', null
    user_correction TEXT,
    automated_score FLOAT,     -- 0.0 to 1.0
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Feedback events table (real-time)
CREATE TABLE feedback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID REFERENCES production_traces(id),
    event_type VARCHAR(50), -- 'tool_failure', 'fallback_triggered', 'policy_violation', etc.
    severity VARCHAR(20),   -- 'info', 'warning', 'error', 'critical'
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for queries
CREATE INDEX idx_traces_tenant_time ON production_traces(tenant_id, created_at);
CREATE INDEX idx_traces_engine ON production_traces(engine_used);
CREATE INDEX idx_traces_feedback ON production_traces(user_feedback) WHERE user_feedback IS NOT NULL;
CREATE INDEX idx_feedback_events_trace ON feedback_events(trace_id);
CREATE INDEX idx_feedback_events_type ON feedback_events(event_type, severity);
```

### Code Implementation

```python
# backend/feedback_loop/tracing.py
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

@dataclass
class ProductionTrace:
    """Complete trace of an agent execution"""
    tenant_id: str
    room_id: str
    task_id: str
    agent_id: str
    
    user_input: Dict[str, Any]
    system_prompt: str
    tool_calls: List[Dict]
    llm_output: str
    final_output: Dict[str, Any]
    
    engine_used: str
    execution_path: Dict[str, Any]
    
    latency_ms: int
    token_usage_input: int
    token_usage_output: int
    retry_count: int = 0
    
    user_feedback: Optional[str] = None
    user_correction: Optional[str] = None
    automated_score: Optional[float] = None

class TraceCollector:
    """Collect and store production traces"""
    
    def __init__(self, db_pool, redis_client):
        self.db = db_pool
        self.redis = redis_client
    
    async def start_trace(self, tenant_id: str, room_id: str, task_id: str) -> str:
        """Start a new trace, return trace_id"""
        trace_id = str(uuid.uuid4())
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO production_traces 
                (id, tenant_id, room_id, task_id, created_at)
                VALUES ($1, $2, $3, $4, NOW())
            """, trace_id, tenant_id, room_id, task_id)
        
        # Cache in Redis for quick updates during execution
        await self.redis.hset(f"trace:{trace_id}", mapping={
            "start_time": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "room_id": room_id
        })
        
        return trace_id
    
    async def record_tool_call(self, trace_id: str, tool_name: str, 
                               input_args: Dict, output: Any, latency_ms: int):
        """Record a tool call within a trace"""
        tool_call = {
            "tool": tool_name,
            "input": input_args,
            "output": output,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Append to Redis list
        await self.redis.lpush(f"trace:{trace_id}:tools", json.dumps(tool_call))
    
    async def complete_trace(self, trace_id: str, final_output: Dict[str, Any],
                            engine_used: str, execution_path: Dict,
                            token_usage: Dict[str, int], latency_ms: int):
        """Mark trace as complete and flush to database"""
        
        # Get all tool calls from Redis
        tool_calls_raw = await self.redis.lrange(f"trace:{trace_id}:tools", 0, -1)
        tool_calls = [json.loads(t) for t in tool_calls_raw]
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE production_traces
                SET final_output = $1,
                    engine_used = $2,
                    execution_path = $3,
                    tool_calls = $4,
                    token_usage_input = $5,
                    token_usage_output = $6,
                    latency_ms = $7,
                    completed_at = NOW()
                WHERE id = $8
            """, 
            json.dumps(final_output), engine_used, json.dumps(execution_path),
            [json.dumps(t) for t in tool_calls],
            token_usage.get('input', 0), token_usage.get('output', 0),
            latency_ms, trace_id)
        
        # Cleanup Redis
        await self.redis.delete(f"trace:{trace_id}", f"trace:{trace_id}:tools")
    
    async def record_user_feedback(self, trace_id: str, feedback: str, 
                                   correction: Optional[str] = None):
        """Record user feedback (thumbs up/down, correction)"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE production_traces
                SET user_feedback = $1, user_correction = $2
                WHERE id = $3
            """, feedback, correction, trace_id)
```

---

## 2. Eval Service (SCORE)

### Automated Evaluation Checks

```python
# backend/feedback_loop/eval_service.py
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
import asyncio

@dataclass
class EvalResult:
    check_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    details: Dict[str, Any]

class EvalService:
    """Automated evaluation of production traces"""
    
    def __init__(self):
        self.checks: List[Callable] = []
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default evaluation checks"""
        self.checks.extend([
            self._check_format_validity,
            self._check_latency_budget,
            self._check_tool_success,
            self._check_policy_compliance,
            self._check_token_efficiency,
        ])
    
    async def evaluate_trace(self, trace: ProductionTrace) -> List[EvalResult]:
        """Run all evaluation checks on a trace"""
        results = []
        
        for check in self.checks:
            try:
                result = await check(trace)
                results.append(result)
            except Exception as e:
                results.append(EvalResult(
                    check_name=check.__name__,
                    passed=False,
                    score=0.0,
                    details={"error": str(e)}
                ))
        
        return results
    
    async def _check_format_validity(self, trace: ProductionTrace) -> EvalResult:
        """Check if output matches expected schema"""
        # Implementation depends on task type
        expected_schema = self._get_schema_for_task(trace.task_id)
        
        is_valid = self._validate_schema(trace.final_output, expected_schema)
        
        return EvalResult(
            check_name="format_validity",
            passed=is_valid,
            score=1.0 if is_valid else 0.0,
            details={"schema": expected_schema}
        )
    
    async def _check_latency_budget(self, trace: ProductionTrace) -> EvalResult:
        """Check if latency is within budget"""
        budget_ms = self._get_latency_budget(trace.engine_used)
        
        passed = trace.latency_ms <= budget_ms
        score = max(0.0, 1.0 - (trace.latency_ms - budget_ms) / budget_ms)
        
        return EvalResult(
            check_name="latency_budget",
            passed=passed,
            score=score,
            details={
                "actual_ms": trace.latency_ms,
                "budget_ms": budget_ms
            }
        )
    
    async def _check_tool_success(self, trace: ProductionTrace) -> EvalResult:
        """Check if all tool calls succeeded"""
        total = len(trace.tool_calls)
        if total == 0:
            return EvalResult(
                check_name="tool_success",
                passed=True,
                score=1.0,
                details={"tool_count": 0}
            )
        
        successful = sum(1 for t in trace.tool_calls 
                        if not t.get('error'))
        
        score = successful / total
        
        return EvalResult(
            check_name="tool_success",
            passed=score >= 0.9,  # 90% threshold
            score=score,
            details={
                "total": total,
                "successful": successful
            }
        )
    
    async def _check_policy_compliance(self, trace: ProductionTrace) -> EvalResult:
        """Check for policy violations"""
        violations = []
        
        # Check for PII leaks
        if self._contains_pii(trace.llm_output):
            violations.append("potential_pii")
        
        # Check for disallowed content
        if self._contains_disallowed(trace.llm_output):
            violations.append("disallowed_content")
        
        # Check for jailbreak attempts in input
        if self._detect_jailbreak(trace.user_input):
            violations.append("jailbreak_attempt")
        
        passed = len(violations) == 0
        
        return EvalResult(
            check_name="policy_compliance",
            passed=passed,
            score=1.0 if passed else 0.0,
            details={"violations": violations}
        )
    
    async def _check_token_efficiency(self, trace: ProductionTrace) -> EvalResult:
        """Check token usage efficiency"""
        total_tokens = trace.token_usage_input + trace.token_usage_output
        
        # Define efficiency thresholds per engine
        thresholds = {
            'langgraph': 4000,
            'crewai': 3000,
            'legacy': 5000
        }
        
        budget = thresholds.get(trace.engine_used, 4000)
        
        score = max(0.0, 1.0 - (total_tokens - budget) / budget)
        
        return EvalResult(
            check_name="token_efficiency",
            passed=total_tokens <= budget,
            score=score,
            details={
                "total_tokens": total_tokens,
                "budget": budget
            }
        )
    
    def _get_schema_for_task(self, task_id: str) -> Dict:
        # Implementation: lookup expected schema
        pass
    
    def _validate_schema(self, output: Dict, schema: Dict) -> bool:
        # Implementation: JSON schema validation
        pass
    
    def _get_latency_budget(self, engine: str) -> int:
        budgets = {
            'langgraph': 60000,  # 60s
            'crewai': 60000,
            'legacy': 300000     # 5min
        }
        return budgets.get(engine, 60000)
    
    def _contains_pii(self, text: str) -> bool:
        # Implementation: regex patterns for PII
        import re
        patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        ]
        return any(re.search(p, text) for p in patterns)
    
    def _contains_disallowed(self, text: str) -> bool:
        # Implementation: content policy checks
        pass
    
    def _detect_jailbreak(self, user_input: Dict) -> bool:
        # Implementation: jailbreak pattern detection
        pass
```

---

## 3. Review Queue (REVIEW)

### Human-in-the-Loop Interface

```python
# backend/feedback_loop/review_queue.py
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class ReviewStatus(Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"

@dataclass
class ReviewItem:
    id: str
    trace_id: str
    status: ReviewStatus
    priority: int  # 1-5, higher = more urgent
    reason: str    # Why it needs review
    assigned_to: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None

class ReviewQueue:
    """Queue for human review of ambiguous or high-risk cases"""
    
    def __init__(self, db_pool, redis_client):
        self.db = db_pool
        self.redis = redis_client
    
    async def add_to_queue(self, trace_id: str, reason: str, 
                          priority: int = 3) -> str:
        """Add a trace to the review queue"""
        
        item_id = str(uuid.uuid4())
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO review_queue 
                (id, trace_id, status, priority, reason, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
            """, item_id, trace_id, ReviewStatus.PENDING.value, priority, reason)
        
        # Publish notification for real-time updates
        await self.redis.publish("review_queue:new", json.dumps({
            "id": item_id,
            "trace_id": trace_id,
            "reason": reason,
            "priority": priority
        }))
        
        return item_id
    
    async def get_pending_items(self, limit: int = 20) -> List[ReviewItem]:
        """Get items pending review, sorted by priority"""
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT rq.*, pt.user_input, pt.final_output, pt.engine_used
                FROM review_queue rq
                JOIN production_traces pt ON rq.trace_id = pt.id
                WHERE rq.status = 'pending'
                ORDER BY rq.priority DESC, rq.created_at ASC
                LIMIT $1
            """, limit)
        
        return [self._row_to_item(row) for row in rows]
    
    async def claim_item(self, item_id: str, reviewer_id: str) -> bool:
        """Claim an item for review"""
        
        async with self.db.acquire() as conn:
            result = await conn.execute("""
                UPDATE review_queue
                SET status = 'in_review',
                    assigned_to = $1
                WHERE id = $2 AND status = 'pending'
            """, reviewer_id, item_id)
            
            return result == "UPDATE 1"
    
    async def submit_review(self, item_id: str, reviewer_id: str,
                           decision: ReviewStatus, notes: str,
                           corrected_output: Optional[Dict] = None):
        """Submit review decision"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE review_queue
                SET status = $1,
                    reviewer_notes = $2,
                    reviewed_at = NOW()
                WHERE id = $3
            """, decision.value, notes, item_id)
            
            # If there's a correction, update the trace
            if corrected_output:
                await conn.execute("""
                    UPDATE production_traces
                    SET user_correction = $1,
                        final_output = $2
                    WHERE id = (SELECT trace_id FROM review_queue WHERE id = $3)
                """, notes, json.dumps(corrected_output), item_id)
            
            # If rejected/escalated, trigger dataset builder
            if decision in (ReviewStatus.REJECTED, ReviewStatus.ESCALATED):
                await self._flag_for_dataset(item_id)
    
    async def _flag_for_dataset(self, item_id: str):
        """Flag this item for inclusion in training dataset"""
        await self.redis.sadd("dataset:candidates", item_id)
```

### Database Schema

```sql
-- Review queue table
CREATE TABLE review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID REFERENCES production_traces(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 3,
    reason TEXT NOT NULL,
    assigned_to VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewer_notes TEXT,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_review', 'approved', 'rejected', 'escalated'))
);

CREATE INDEX idx_review_queue_status ON review_queue(status, priority DESC, created_at);
CREATE INDEX idx_review_queue_assigned ON review_queue(assigned_to) WHERE status = 'in_review';
```

---

## 4. Dataset Builder (CURATE)

### Regression Test Generation

```python
# backend/feedback_loop/dataset_builder.py
from typing import List, Dict, Any
import json
from datetime import datetime

class DatasetBuilder:
    """Build datasets from production failures for regression testing"""
    
    def __init__(self, db_pool, storage_client):
        self.db = db_pool
        self.storage = storage_client  # S3 or similar
    
    async def build_regression_suite(self, since: datetime) -> str:
        """Build regression test suite from recent failures"""
        
        suite_id = str(uuid.uuid4())
        
        # Collect failed traces
        async with self.db.acquire() as conn:
            failed_traces = await conn.fetch("""
                SELECT pt.*, rq.reviewer_notes
                FROM production_traces pt
                JOIN review_queue rq ON pt.id = rq.trace_id
                WHERE rq.status = 'rejected'
                  AND pt.created_at > $1
            """, since)
        
        # Build test cases
        test_cases = []
        for trace in failed_traces:
            test_case = {
                "id": str(uuid.uuid4()),
                "trace_id": str(trace['id']),
                "input": trace['user_input'],
                "expected_behavior": self._infer_expected(trace),
                "failure_mode": trace['reviewer_notes'],
                "created_at": datetime.utcnow().isoformat()
            }
            test_cases.append(test_case)
        
        # Store in S3
        suite_data = {
            "id": suite_id,
            "created_at": datetime.utcnow().isoformat(),
            "test_count": len(test_cases),
            "tests": test_cases
        }
        
        await self.storage.upload(
            bucket="agent-world-regression",
            key=f"suites/{suite_id}.json",
            data=json.dumps(suite_data).encode()
        )
        
        return suite_id
    
    async def build_gold_dataset(self) -> str:
        """Build gold-standard dataset from approved traces"""
        
        dataset_id = str(uuid.uuid4())
        
        async with self.db.acquire() as conn:
            gold_traces = await conn.fetch("""
                SELECT pt.*
                FROM production_traces pt
                JOIN review_queue rq ON pt.id = rq.trace_id
                WHERE rq.status = 'approved'
                  AND pt.user_feedback = 'thumbs_up'
                ORDER BY pt.created_at DESC
                LIMIT 1000
            """)
        
        # Build examples
        examples = []
        for trace in gold_traces:
            example = {
                "input": trace['user_input'],
                "output": trace['final_output'],
                "metadata": {
                    "engine": trace['engine_used'],
                    "latency_ms": trace['latency_ms'],
                    "token_usage": {
                        "input": trace['token_usage_input'],
                        "output": trace['token_usage_output']
                    }
                }
            }
            examples.append(example)
        
        # Store
        dataset = {
            "id": dataset_id,
            "created_at": datetime.utcnow().isoformat(),
            "example_count": len(examples),
            "examples": examples
        }
        
        await self.storage.upload(
            bucket="agent-world-datasets",
            key=f"gold/{dataset_id}.json",
            data=json.dumps(dataset).encode()
        )
        
        return dataset_id
    
    def _infer_expected(self, trace) -> Dict[str, Any]:
        """Infer expected behavior from failure analysis"""
        # Implementation: analyze the trace and reviewer notes
        # to determine what correct behavior should look like
        pass
```

---

## 5. Release Gate (REDEPLOY)

### Quality Gate Implementation

```python
# backend/feedback_loop/release_gate.py
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class QualityMetrics:
    task_success_rate: float
    fallback_rate: float
    tool_success_rate: float
    latency_p95: float
    latency_p99: float
    retry_count_avg: float
    human_correction_rate: float
    policy_violation_count: int

class ReleaseGate:
    """Gate deployments based on quality metrics"""
    
    def __init__(self, db_pool, metrics_client):
        self.db = db_pool
        self.metrics = metrics_client
        self.thresholds = {
            'task_success_rate': 0.95,
            'fallback_rate': 0.10,  # Max 10%
            'tool_success_rate': 0.90,
            'latency_p95': 60000,   # 60s
            'latency_p99': 120000,  # 120s
            'retry_count_avg': 2.0,
            'human_correction_rate': 0.05,  # Max 5%
            'policy_violation_count': 0,    # Zero tolerance
        }
    
    async def check_release_readiness(self, version: str, 
                                     window_hours: int = 24) -> Dict[str, Any]:
        """Check if a version meets quality thresholds for release"""
        
        # Collect metrics for this version
        metrics = await self._collect_metrics(version, window_hours)
        
        # Check each threshold
        checks = {}
        all_passed = True
        
        for metric_name, threshold in self.thresholds.items():
            actual = getattr(metrics, metric_name)
            
            # For rates that should be LOW, check actual <= threshold
            # For rates that should be HIGH, check actual >= threshold
            if metric_name in ['task_success_rate', 'tool_success_rate']:
                passed = actual >= threshold
            else:
                passed = actual <= threshold
            
            checks[metric_name] = {
                'actual': actual,
                'threshold': threshold,
                'passed': passed
            }
            
            if not passed:
                all_passed = False
        
        return {
            'version': version,
            'window_hours': window_hours,
            'all_passed': all_passed,
            'checks': checks,
            'recommendation': 'proceed' if all_passed else 'rollback'
        }
    
    async def _collect_metrics(self, version: str, window_hours: int) -> QualityMetrics:
        """Collect quality metrics for a version"""
        
        async with self.db.acquire() as conn:
            # Task success rate
            success_rate = await conn.fetchval("""
                SELECT COALESCE(
                    COUNT(*) FILTER (WHERE automated_score >= 0.9)::float / NULLIF(COUNT(*), 0),
                    0
                )
                FROM production_traces
                WHERE created_at > NOW() - INTERVAL '%s hours'
            """, window_hours)
            
            # Fallback rate
            fallback_rate = await conn.fetchval("""
                SELECT COALESCE(
                    COUNT(*) FILTER (WHERE engine_used = 'legacy')::float / NULLIF(COUNT(*), 0),
                    0
                )
                FROM production_traces
                WHERE created_at > NOW() - INTERVAL '%s hours'
            """, window_hours)
            
            # More metrics...
            
        return QualityMetrics(
            task_success_rate=success_rate,
            fallback_rate=fallback_rate,
            tool_success_rate=0.0,  # TODO
            latency_p95=0.0,        # TODO
            latency_p99=0.0,        # TODO
            retry_count_avg=0.0,    # TODO
            human_correction_rate=0.0,  # TODO
            policy_violation_count=0    # TODO
        )
    
    async def compare_versions(self, baseline: str, candidate: str) -> Dict[str, Any]:
        """Compare two versions to detect regression"""
        
        baseline_metrics = await self._collect_metrics(baseline, 24)
        candidate_metrics = await self._collect_metrics(candidate, 24)
        
        comparison = {}
        
        for field in QualityMetrics.__dataclass_fields__:
            baseline_val = getattr(baseline_metrics, field)
            candidate_val = getattr(candidate_metrics, field)
            
            if baseline_val > 0:
                change_pct = (candidate_val - baseline_val) / baseline_val * 100
            else:
                change_pct = 0 if candidate_val == 0 else 100
            
            comparison[field] = {
                'baseline': baseline_val,
                'candidate': candidate_val,
                'change_pct': change_pct,
                'regression': abs(change_pct) > 10  # 10% threshold
            }
        
        return {
            'baseline': baseline,
            'candidate': candidate,
            'comparison': comparison,
            'has_regression': any(c['regression'] for c in comparison.values())
        }
```

---

## 6. Integration Points

### Wiring into ExecutionEngine

```python
# In execution_engine.py, add trace collection

async def execute_task(self, task_id: str, task_type: str, 
                      payload: Dict[str, Any], room_id: str, 
                      tenant_id: str, legacy_executor: Optional[Callable] = None):
    
    # Start trace
    trace_id = await self.trace_collector.start_trace(
        tenant_id=tenant_id,
        room_id=room_id,
        task_id=task_id
    )
    
    start_time = time.time()
    
    try:
        # ... existing routing logic ...
        
        # Complete trace
        await self.trace_collector.complete_trace(
            trace_id=trace_id,
            final_output=result,
            engine_used=engine_used,
            execution_path=execution_path,
            token_usage=token_usage,
            latency_ms=int((time.time() - start_time) * 1000)
        )
        
        # Run automated evals
        trace = await self.trace_collector.get_trace(trace_id)
        eval_results = await self.eval_service.evaluate_trace(trace)
        
        # Route to review queue if needed
        failed_checks = [r for r in eval_results if not r.passed]
        if failed_checks:
            priority = 5 if any(r.check_name == 'policy_compliance' 
                              for r in failed_checks) else 3
            
            await self.review_queue.add_to_queue(
                trace_id=trace_id,
                reason=f"Failed checks: {[r.check_name for r in failed_checks]}",
                priority=priority
            )
        
        return result
        
    except Exception as e:
        # Record failure
        await self.trace_collector.record_failure(trace_id, str(e))
        raise
```

### Frontend Feedback UI

```jsx
// Feedback buttons in RoomStream
function MessageFeedback({ traceId }) {
  const submitFeedback = async (type) => {
    await fetch(`/api/v1/feedback/${traceId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback: type })
    });
  };
  
  return (
    <div className="flex gap-2 mt-2">
      <button onClick={() => submitFeedback('thumbs_up')}>
        👍 Helpful
      </button>
      <button onClick={() => submitFeedback('thumbs_down')}>
        👎 Not Helpful
      </button>
    </div>
  );
}
```

---

## First Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Task success rate | >95% | <90% |
| Fallback rate | <10% | >15% |
| Tool success rate | >90% | <85% |
| Latency P95 | <60s | >90s |
| Latency P99 | <120s | >180s |
| Retry count avg | <2 | >3 |
| Human correction rate | <5% | >10% |
| Policy violation count | 0 | >0 |

---

## Routing Logic for Failures

```
IF run fails:
  ├─ Model issue? → Tune prompt, switch model, add examples
  ├─ Routing issue? → Adjust ExecutionEngine thresholds
  ├─ Tool issue? → Fix tool implementation, add retries
  ├─ Data issue? → Update training data, fix data pipeline
  ├─ Policy issue? → Strengthen guardrails, add checks
  └─ UX issue? → Improve interface, add clarifications
```

---

## Implementation Order

1. **Week 1**: Telemetry layer (tracing, storage)
2. **Week 2**: Eval service (automated checks)
3. **Week 3**: Review queue (human-in-the-loop)
4. **Week 4**: Dataset builder (regression tests)
5. **Week 5**: Release gate (quality thresholds)
6. **Week 6**: Full integration and testing

This creates a closed loop where production traces feed improvement work, and improvement work is validated by fresh production data.
