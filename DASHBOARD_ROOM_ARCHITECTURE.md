# Drag-and-Drop Workflow UI Architecture
## AgentVerse Dashboard Rooms Implementation Plan

**Date:** April 12, 2026  
**Based on:** Multi-business agent hierarchy specification  
**Target:** 8-room grid with drag-and-drop workflow canvas

---

## 1. Architecture Analysis

### Current State vs Target

| Component | Current (AgentVerse) | Target (Spec) | Gap |
|-----------|---------------------|---------------|-----|
| **Frontend** | Basic HTML/JS | React + DnD canvas | Large |
| **Room Model** | Room engine exists | Visual drag canvas | Medium |
| **Agents** | Scout/Maker/Merchant | +Affiliate, +Hierarchy | Medium |
| **Communication** | REST + WebSocket | Redis pub/sub + DnD | Small |
| **Dashboard** | Revenue metrics | Multi-room grid | Medium |

### Reuse vs Build Decision

| From ChatDev Analysis | Decision |
|-----------------------|----------|
| Fork ChatDev UI | ❌ No — build custom per spec |
| Use ChatDev nodes | ⚠️ Partial — adapt concepts |
| VueFlow library | ✅ Yes — use for canvas |
| Custom DnD | ✅ Yes — per spec |

**Verdict:** Build custom React-based UI per specification rather than forking ChatDev. Better alignment with multi-room, multi-business architecture.

---

## 2. Room Hierarchy Mapping

### Spec Hierarchy → AgentVerse Implementation

```
Human Owner
└── Global Chief of Staff Agent (NEW)
    ├── Global Analyst Agent (NEW)
    ├── Global Compliance Agent (NEW)
    ├── Global Reliability/Repair Agent (NEW)
    ├── Global Architect Agent (NEW)
    └── Business Lead Agent (per business) (NEW)
        ├── Scout (EXISTS)
        ├── Maker (EXISTS)
        ├── Merchant (EXISTS)
        ├── Affiliate Hunter (NEW - Ticket 3)
        ├── Social Media Manager (NEW)
        ├── Operations/Account Manager (NEW)
        └── Business Analyst (NEW)
```

### Room Structure (Per Spec)

| Room | Purpose | Agents | Status |
|------|---------|--------|--------|
| **Master HQ** | Global control | Chief of Staff, Analyst, Compliance, Reliability | NEW |
| **Business Room 1-8** | Per-business operations | Business Lead + specialists | ADAPT |
| **Shared Systems** | Infrastructure | Reliability, Architect | NEW |
| **Communications** | Agent discussions | All leads | NEW |
| **Audit/Memory** | Logging | Compliance, Analyst | NEW |

---

## 3. Implementation Components

### 3.1 Frontend (React + DnD)

**New Files Required:**

```
frontend/src/
├── components/
│   ├── rooms/
│   │   ├── RoomGrid.jsx           # 2x4 grid layout
│   │   ├── RoomCard.jsx           # Individual room container
│   │   ├── MasterHQ.jsx           # Global control room
│   │   └── BusinessRoom.jsx       # Business-specific room
│   ├── canvas/
│   │   ├── WorkflowCanvas.jsx     # DnD provider + canvas
│   │   ├── CanvasArea.jsx         # Drop target
│   │   ├── AgentNode.jsx          # Draggable agent node
│   │   └── ConnectionLine.jsx     # Edge between nodes
│   ├── sidebar/
│   │   ├── AgentSidebar.jsx       # Draggable agent palette
│   │   └── AgentItem.jsx          # Individual agent button
│   └── agents/
│       ├── ScoutConfig.jsx
│       ├── MakerConfig.jsx
│       ├── MerchantConfig.jsx
│       └── AffiliateConfig.jsx
├── hooks/
│   ├── useDragAndDrop.js
│   ├── useWorkflow.js
│   └── useAgentCommunication.js
├── store/
│   └── roomStore.js               # Zustand/Redux for room state
└── styles/
    └── cyber-theme.css
```

**Key Dependencies:**
```json
{
  "react-dnd": "^16.0.0",
  "react-dnd-html5-backend": "^16.0.0",
  "@vue-flow/core": "^1.30.0",     # Alternative to custom DnD
  "zustand": "^4.5.0",             # State management
  "socket.io-client": "^4.7.0"     # Real-time communication
}
```

### 3.2 Backend (FastAPI + Redis)

**New Files:**

```
backend/
├── rooms/
│   ├── room_manager.py            # Room lifecycle management
│   ├── room_models.py             # Room DB models
│   └── room_routes.py             # REST API for rooms
├── agents/
│   ├── agent_hierarchy.py         # Chief of Staff, Business Lead
│   ├── global_agents.py           # Analyst, Compliance, Reliability
│   └── business_agents.py         # Social, Ops, Analyst
├── communication/
│   ├── redis_pubsub.py            # Agent message bus
│   └── message_router.py          # Route messages between agents
├── workflow/
│   ├── drag_drop_workflow.py      # Canvas state management
│   └── workflow_persistence.py    # Save/load room workflows
└── hierarchy/
    ├── chief_of_staff.py          # Global coordinator
    └── business_lead.py           # Per-business coordinator
```

### 3.3 Agent Hierarchy Implementation

**Global Chief of Staff Agent:**
```python
class ChiefOfStaffAgent:
    """
    Global coordinator across all 8 businesses.
    Routes work, consolidates reports, escalates to human.
    """
    
    def __init__(self):
        self.business_leads = {}  # 8 business leads
        self.global_analyst = GlobalAnalyst()
        self.global_compliance = GlobalCompliance()
        self.global_reliability = GlobalReliability()
    
    async def handle_command(self, command: str, context: dict):
        """
        Process human commands:
        - "Business 3: increase output by 20%"
        - "All businesses: pause paid actions"
        - "Global: show incidents and opportunities"
        """
        parsed = self._parse_command(command)
        
        if parsed["scope"] == "global":
            return await self._execute_global(parsed)
        elif parsed["scope"] == "business":
            lead = self.business_leads.get(parsed["business_id"])
            return await lead.execute(parsed)
    
    async def consolidate_reports(self) -> dict:
        """Daily summary for human owner"""
        reports = []
        for lead in self.business_leads.values():
            reports.append(await lead.get_status())
        
        return self.global_analyst.summarize(reports)
```

**Business Lead Agent (per business):**
```python
class BusinessLeadAgent:
    """
    Coordinates specialists within one business.
    """
    
    def __init__(self, business_id: str):
        self.business_id = business_id
        self.scout = ScoutAgent()
        self.maker = MakerAgent()
        self.merchant = MerchantAgent()
        self.affiliate = AffiliateHunterAgent()
        self.social = SocialMediaManager()
        self.ops = OperationsManager()
        self.analyst = BusinessAnalyst()
    
    async def coordinate_workflow(self, workflow_config: dict):
        """
        Execute drag-drop workflow:
        Scout → Maker → Merchant → Affiliate
        """
        # Get trends from Scout
        trends = await self.scout.discover()
        
        # Maker creates content
        content = await self.maker.create(trends[0])
        
        # Merchant publishes
        published = await self.merchant.publish(content)
        
        # Affiliate adds links
        monetized = await self.affiliate.enhance(published)
        
        return monetized
```

---

## 4. Database Schema Additions

### Room Model
```sql
CREATE TABLE rooms (
    id UUID PRIMARY KEY,
    business_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) CHECK (type IN ('master_hq', 'business', 'shared_systems', 'communications', 'audit')),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE room_workflows (
    id UUID PRIMARY KEY,
    room_id UUID REFERENCES rooms(id),
    workflow_data JSONB NOT NULL,  -- Canvas nodes + edges
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agent_communications (
    id UUID PRIMARY KEY,
    from_agent VARCHAR(255) NOT NULL,
    to_agent VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    room_id UUID REFERENCES rooms(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    message_type VARCHAR(50) CHECK (message_type IN ('command', 'response', 'alert', 'proposal'))
);
```

---

## 5. API Design

### Room Management
```python
# GET /api/rooms
# List all rooms for dashboard
{
  "rooms": [
    {"id": "room_1", "business_id": "biz_1", "name": "Arbitrage Pipeline", "type": "business"},
    {"id": "room_2", "business_id": "biz_1", "name": "Trend Analysis", "type": "business"},
    {"id": "room_master", "business_id": null, "name": "Master HQ", "type": "master_hq"}
  ]
}

# GET /api/rooms/{room_id}/workflow
# Get canvas state
{
  "nodes": [
    {"id": "node_1", "type": "scout", "position": {"x": 100, "y": 200}, "config": {"subreddit": "technology"}},
    {"id": "node_2", "type": "maker", "position": {"x": 300, "y": 200}, "config": {"template": "viral"}}
  ],
  "edges": [
    {"from": "node_1", "to": "node_2", "condition": "success"}
  ]
}

# POST /api/rooms/{room_id}/workflow
# Save canvas state
{
  "nodes": [...],
  "edges": [...]
}

# POST /api/rooms/{room_id}/execute
# Execute workflow from canvas
{
  "workflow_id": "room_1_workflow_v1"
}
```

### Agent Communication (Redis)
```python
# Channel: agent:messages:{room_id}
{
  "from": "scout_1",
  "to": "maker_1",
  "type": "handoff",
  "payload": {"trend": {...}},
  "timestamp": "2026-04-12T16:30:00Z"
}

# Channel: agent:alerts:global
{
  "severity": "high",
  "agent": "merchant_3",
  "message": "API rate limit exceeded",
  "room_id": "room_2",
  "action_required": true
}
```

---

## 6. Implementation Phases

### Phase 1: Single Room Canvas (2-3 days)
**Goal:** Basic drag-drop workflow in one room

**Tasks:**
1. Setup React project with DnD dependencies
2. Create `WorkflowCanvas` component with drag-drop provider
3. Implement `AgentSidebar` with Scout/Maker/Merchant/ Affiliate
4. Create `AgentNode` component with config panel
5. Add connection lines between nodes
6. Save/load workflow to backend

**Validation:**
- Can drag Scout → Maker → Merchant onto canvas
- Can connect nodes with edges
- Workflow saves and loads

### Phase 2: Multi-Room Grid (1-2 days)
**Goal:** 2x4 grid layout with 8 business rooms

**Tasks:**
1. Create `RoomGrid` component (CSS Grid 2x4)
2. Implement `RoomCard` container
3. Add room switching/navigation
4. Room-specific workflow persistence
5. Mini preview thumbnails per room

**Validation:**
- 8 rooms visible in grid
- Each room has independent canvas
- Switching rooms loads correct workflow

### Phase 3: Agent Hierarchy (2-3 days)
**Goal:** Chief of Staff + Business Lead coordination

**Tasks:**
1. Implement `ChiefOfStaffAgent` backend
2. Create `BusinessLeadAgent` per room
3. Add global command interface
4. Implement report consolidation
5. Create approval workflow gates

**Validation:**
- Can send global command: "Business 3: increase output 20%"
- Chief of Staff routes to correct Business Lead
- Reports consolidate at global level

### Phase 4: Auto-Repair Agent (1-2 days)
**Goal:** Self-healing system with Reliability agent

**Tasks:**
1. Implement `ReliabilityAgent` with health monitoring
2. Add auto-repair playbooks (restart, retry, reroute)
3. Create incident detection
4. Add human escalation for high-risk repairs
5. Repair logs in Audit room

**Validation:**
- Failed workflow auto-retries
- Stuck agent gets restarted
- Human notified for approval-required repairs

### Phase 5: Communications Room (1 day)
**Goal:** Structured agent discussions

**Tasks:**
1. Create Communications room UI
2. Implement message threading
3. Add proposal/approval workflow
4. Escalation queue
5. Postmortem documentation

**Validation:**
- Agents can submit proposals
- Approval/rejection flow works
- Discussion history preserved

---

## 7. Integration with Existing AgentVerse

### Reuse Existing Components

| Existing Component | Reuse In | Notes |
|-------------------|----------|-------|
| `stateless_adapter.py` | Workflow execution | Call via API from canvas |
| `multi_source_scout.py` | Scout agent | Integrate as node backend |
| `revenue_models.py` | Dashboard metrics | Display in room panels |
| `camofox_client.py` | Scout browsing | Use for trend discovery |
| `multica_client.py` | Task orchestration | Use for agent coordination |
| Redis shared state | Agent communication | Pub/sub for messages |

### Migration Path

1. **Keep current system running** (Phases 1-4 run parallel)
2. **Build new UI alongside** (separate route `/dashboard/v2`)
3. **Gradual cutover** per room/business
4. **Legacy fallback** until fully validated

---

## 8. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| React rewrite scope | High | Use VueFlow library to reduce custom DnD code |
| Agent communication complexity | Medium | Start with direct messaging, add hierarchy later |
| Room state synchronization | Medium | Use Redis for shared state, optimistic UI updates |
| Performance with 8 rooms | Medium | Lazy load canvases, virtualize off-screen rooms |
| Backward compatibility | Low | Keep existing API, new UI is additive |

---

## 9. Recommended Tech Stack

| Layer | Technology | Reason |
|-------|------------|--------|
| **Frontend** | React 18 + Vite | Modern, fast dev, DnD ecosystem |
| **Canvas** | @vue-flow/core | Proven workflow library (used by ChatDev) |
| **State** | Zustand | Simple, effective for room state |
| **Styling** | Tailwind + Cyber theme | Rapid UI, matches spec |
| **Backend** | FastAPI (existing) | Keep current stack |
| **Communication** | Redis pub/sub + Socket.io | Real-time agent messages |
| **Database** | PostgreSQL (existing) | Add room tables |

---

## 10. Next Steps

1. **Decision:** Proceed with custom React UI or fork ChatDev?
   - **Recommendation:** Custom UI per this spec (better fit for multi-room)

2. **Phase 1 kickoff:** Setup React project with VueFlow
   - Create repo/branch for new UI
   - Install dependencies
   - Build basic canvas

3. **Parallel work:** Begin Chief of Staff agent backend
   - Implement hierarchy
   - Add Redis pub/sub
   - Business Lead scaffolding

**Estimated Timeline:** 7-10 days for full implementation

**Confidence:** 80% — Well-specified architecture, clear implementation path
