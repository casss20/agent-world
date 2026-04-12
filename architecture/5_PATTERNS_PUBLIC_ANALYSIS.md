# 5 Architectural Patterns from Public Analysis
## Clean-Room Redesign for Ledger Governance

**Source:** Public analysis articles (sabrina.dev, Reddit discussions)  
**Method:** Pattern extraction → Abstract redesign → Ledger integration  
**Status:** No proprietary code accessed. High-level patterns only.

---

## Pattern 1: Autonomous Daemon Mode (KAIROS → Ledger Auto-Mode)

### Public Description
Autonomous background agent with scheduled tasks, webhooks, cron cycles, and memory consolidation.

### Original Design for Ledger

**Concept:** `AutoGovernor` — Ledger runs continuous background oversight

```
┌─────────────────────────────────────────┐
│         LEDGER AUTO-MODE                │
├─────────────────────────────────────────┤
│                                         │
│  Cron Schedules (every 5 min)          │
│       ↓                                 │
│  ┌──────────────┐                       │
│  │  Health      │  Check all 8         │
│  │   Monitor    │  businesses          │
│  └──────┬───────┘                       │
│         ↓                               │
│  ┌──────────────┐  Yes                │
│  │  Anomaly?    │ ─────→ Alert + Log  │
│  └──────┬───────┘                       │
│         │ No                            │
│         ↓                               │
│  ┌──────────────┐                       │
│  │  Opportunity │  Scan for            │
│  │    Scan      │  optimization        │
│  └──────┬───────┘                       │
│         ↓                               │
│  ┌──────────────┐  Yes                │
│  │  Actionable? │ ─────→ Queue for     │
│  └──────────────┘       approval       │
│                                         │
└─────────────────────────────────────────┘
```

**Ledger Integration:**
- AutoGovernor runs as scheduled job via existing cron system
- Checks business health, flags anomalies, suggests optimizations
- All actions queue for human approval (no autonomous execution)
- Logs everything to immutable audit trail

**Components:**
```typescript
interface AutoGovernor {
  schedules: CronSchedule[];
  healthChecks: BusinessHealthMonitor[];
  anomalyDetectors: AnomalyRule[];
  opportunityScanners: Scanner[];
  actionQueue: PendingAction[];
}
```

---

## Pattern 2: Background Memory Consolidation (/dream → Ledger /consolidate)

### Public Description
Background process that consolidates session memories when time gates pass and enough sessions accumulate.

### Original Design for Ledger

**Concept:** `MemoryConsolidator` — Compresses daily decisions into strategic memory

```
Trigger Conditions (AND):
├── Time: 24h since last consolidation
├── Volume: 5+ decisions since last run
└── Lock: Advisory file lock acquired

Process:
├── Read recent decisions from AUDIT.md
├── Extract patterns and lessons
├── Update strategic MEMORY.md
├── Prune ephemeral details
└── Log consolidation event
```

**Implementation:**
```typescript
interface ConsolidationGate {
  minHours: 24;
  minDecisions: 5;
  lockFile: string;  // mtime = lastConsolidatedAt
}

interface ConsolidationResult {
  decisionsProcessed: number;
  patternsExtracted: string[];
  memoryUpdated: boolean;
  timestamp: ISO8601;
}
```

**Ledger Integration:**
- Daily background job (already have cron system)
- Reads from `memory/YYYY-MM-DD.md` files
- Updates `MEMORY.md` with distilled learnings
- Uses file-based locking (mtime pattern) for coordination
- Runs only when enough activity warrants it

---

## Pattern 3: Time-Gated Execution (Triple Gate → Ledger Approval Gates)

### Public Description
Triple gate pattern: time check (cheapest) → volume check → lock acquisition.

### Original Design for Ledger

**Concept:** `ApprovalGating` — Multi-layer approval with cost-ordered checks

```
Request Action
    ↓
┌────────────────────────────────────────┐
│ Gate 1: Constitution Check (instant)   │
│ ── Is action constitutionally valid?   │
└────────────┬───────────────────────────┘
             │ Yes
             ↓
┌────────────────────────────────────────┐
│ Gate 2: Context Check (DB lookup)      │
│ ── Does user have permission?          │
│ ── Is business in allowed state?       │
└────────────┬───────────────────────────┘
             │ Yes
             ↓
┌────────────────────────────────────────┐
│ Gate 3: Distributed Lock (file/Redis)  │
│ ── Acquire execution lock              │
│ ── Prevent race conditions             │
└────────────┬───────────────────────────┘
             │ Success
             ↓
         EXECUTE
```

**Benefits:**
- Fail fast on cheap checks (constitution)
- Avoid expensive operations if not needed
- Lock only when execution is certain
- Rollback-friendly (each gate is reversible)

---

## Pattern 4: Mode-Based System Prompts (Undercover → Business Modes)

### Public Description
Context-aware mode switching that changes system behavior based on repository/environment.

### Original Design for Ledger

**Concept:** `BusinessContextEngine` — Ledger adapts tone/rules per business

```typescript
type BusinessMode = 
  | 'stealth'      // Operate quietly, minimal logs
  | 'verbose'      // Full transparency, detailed logging
  | 'aggressive'   // High-risk tolerance, fast execution
  | 'conservative'; // Max safety, double approvals

interface ModeConfig {
  mode: BusinessMode;
  rules: {
    autoApprove: boolean;
    logLevel: 'minimal' | 'standard' | 'verbose';
    escalationThreshold: number;
    notificationChannel: string;
  };
}
```

**Mode Examples:**

| Mode | Use Case | Behavior |
|------|----------|----------|
| `stealth` | Stealth businesses | Minimal logs, quiet execution |
| `verbose` | Public projects | Full audit, transparent decisions |
| `aggressive` | High-velocity testing | Fast approvals, higher risk tolerance |
| `conservative` | Financial/legal | Double approvals, max safety |

**Ledger Integration:**
- Each business gets a mode in `WORLD.md`
- Mode affects approval thresholds
- Mode affects logging verbosity
- Mode can be switched per business context

---

## Pattern 5: Feature Flag Gating (Daemon flags → Ledger Capability Flags)

### Public Description
Major features (daemon mode, autonomous actions) sit behind feature flags.

### Original Design for Ledger

**Concept:** `CapabilityFlags` — Gradual rollout with kill switches

```yaml
# capability_flags.yaml
ledger_capabilities:
  auto_governor:
    enabled: true
    rollout_percentage: 100
    allowed_businesses: [1,2,3,4,5,6,7,8]
    
  memory_consolidation:
    enabled: true
    rollout_percentage: 100
    
  autonomous_repair:
    enabled: false        # Kill switch ready
    rollout_percentage: 0
    allowed_businesses: [] # No businesses yet
    
  cross_business_memory:
    enabled: true
    rollout_percentage: 50
    allowed_businesses: [1,2] # A/B test on 2 businesses
```

**Runtime Check:**
```typescript
function canUseCapability(
  capability: string,
  businessId: string,
  flags: CapabilityFlags
): boolean {
  const flag = flags[capability];
  if (!flag.enabled) return false;
  if (!flag.allowed_businesses.includes(businessId)) return false;
  if (Math.random() * 100 > flag.rollout_percentage) return false;
  return true;
}
```

**Ledger Integration:**
- Flags stored in `SYSTEM_INDEX.md`
- Hot-reloadable without restart
- Emergency kill switch for any capability
- A/B testing support per business

---

## React Integration: Approval Gates (Pattern 3)

### Component: `ApprovalGate`

```jsx
// components/governance/ApprovalGate.jsx
import { useLedger } from '../../providers/LedgerProvider';

export function ApprovalGate({ 
  children, 
  action,
  resource,
  fallback = null 
}) {
  const { checkPermission, requestApproval } = useLedger();
  const [status, setStatus] = useState('checking'); // checking | approved | pending | denied
  
  useEffect(() => {
    async function validate() {
      // Gate 1: Constitution (instant)
      const permitted = checkPermission(action, resource);
      
      if (!permitted) {
        setStatus('denied');
        return;
      }
      
      // Gate 2: Context (async check)
      const contextCheck = await validateContext(action, resource);
      
      if (contextCheck.requiresApproval) {
        setStatus('pending');
        await requestApproval(action, contextCheck.reason);
        return;
      }
      
      setStatus('approved');
    }
    
    validate();
  }, [action, resource]);
  
  if (status === 'checking') {
    return <GateLoader />;
  }
  
  if (status === 'denied') {
    return fallback || <GateDenied action={action} />;
  }
  
  if (status === 'pending') {
    return <GatePending action={action} />;
  }
  
  return children;
}

// Usage in business workspace
function DeleteWorkflowButton({ workflowId }) {
  return (
    <ApprovalGate 
      action="delete" 
      resource={`workflow:${workflowId}`}
      fallback={<Button disabled>Delete (Requires Approval)</Button>}
    >
      <Button variant="danger" onClick={handleDelete}>
        Delete Workflow
      </Button>
    </ApprovalGate>
  );
}
```

### Component: `GateStatus`

```jsx
// Shows current gate status for debugging
export function GateStatus({ action, resource }) {
  const { checkPermission } = useLedger();
  const [gates, setGates] = useState([]);
  
  useEffect(() => {
    // Run through all gates and capture results
    const results = [
      { name: 'Constitution', status: checkGate1(action) },
      { name: 'Context', status: checkGate2(action, resource) },
      { name: 'Lock', status: checkGate3(action) },
    ];
    setGates(results);
  }, [action, resource]);
  
  return (
    <div className="gate-status">
      {gates.map(gate => (
        <div key={gate.name} className={`gate ${gate.status}`}>
          <span className="gate-name">{gate.name}</span>
          <span className="gate-indicator">
            {gate.status === 'pass' ? '✓' : 
             gate.status === 'fail' ? '✗' : '⏳'}
          </span>
        </div>
      ))}
    </div>
  );
}
```

---

## Implementation Priority

| Pattern | Effort | Impact | Priority |
|---------|--------|--------|----------|
| Approval Gates (3) | Low | High | **Week 1** |
| Capability Flags (5) | Low | High | **Week 1** |
| Memory Consolidation (2) | Medium | Medium | Week 2 |
| AutoGovernor (1) | Medium | High | Week 2 |
| Business Modes (4) | Low | Medium | Week 3 |

---

## Clean-Room Compliance

| Requirement | Status |
|-------------|--------|
| Source | Public blog post analysis only |
| Proprietary code accessed | ❌ None |
| Implementation details copied | ❌ None |
| High-level patterns extracted | ✅ Yes |
| Original redesign | ✅ All 5 patterns redesigned |
| Specific to Ledger platform | ✅ Tailored to your system |

---

## Summary

**Extracted from public analysis:**
1. Daemon mode → `AutoGovernor` for background oversight
2. Memory consolidation → `MemoryConsolidator` for daily distillation
3. Triple gating → `ApprovalGates` for cost-ordered permission checks
4. Mode switching → `BusinessContextEngine` for per-business behavior
5. Feature flags → `CapabilityFlags` for safe rollout

**React Integration:**
- `ApprovalGate` component wraps any action with 3-layer validation
- `GateStatus` shows real-time gate progress
- Integrates with existing `LedgerProvider`

All designs are original implementations inspired by public architectural discussions, not proprietary code.
