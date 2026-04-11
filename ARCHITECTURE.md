# Multi-Agent Collaboration Platform
## Architecture Specification v1.0

---

## 1. Core Concept

**AgentVerse** — A shared-workspace platform where AI agents collaborate on projects through rooms, with full context sharing and real-time coordination.

### Mental Model
```
Tenant (Your Company)
  └── Project (Q4 Marketing Campaign)
        ├── Room: Strategy (PM + Researcher + Analyst)
        ├── Room: Creative (Designer + Copywriter + Reviewer)
        └── Room: Execution (Publisher + Scheduler + Monitor)
```

Each room is a **live workspace** where agents:
- Share context (briefs, research, assets)
- Broadcast updates to all participants
- Send DMs for private coordination
- Collaborate on tasks with clear ownership

---

## 2. Refined Database Schema (Production-Ready)

### Core Entities

```sql
-- Multi-tenancy foundation
create table tenants (
    id uuid primary key default gen_random_uuid(),
    name varchar(255) not null,
    slug varchar(255) unique not null, -- for subdomains
    plan varchar(50) default 'free', -- free, pro, enterprise
    config jsonb default '{}', -- feature flags, limits
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Projects are business units
create table projects (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id) on delete cascade,
    name varchar(255) not null,
    description text,
    type varchar(50), -- 'marketing', 'product', 'research', 'creative'
    status varchar(50) default 'active', -- active, archived, paused
    config jsonb default '{}', -- project-level settings
    created_by uuid, -- user_id when auth added
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Rooms are shared workspaces
create table rooms (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    name varchar(255) not null,
    description text,
    room_type varchar(50) default 'general', -- strategy, creative, execution, review
    
    -- Shared workspace state
    shared_context jsonb default '{}', -- current brief, trends, decisions
    artifact_urls text[] default '{}', -- files, designs, documents
    guidelines jsonb default '{}', -- room-specific rules
    
    -- Presence
    status varchar(50) default 'active', -- active, archived
    is_private boolean default false,
    
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Agent definitions (reusable across rooms)
create table agents (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id) on delete cascade,
    
    -- Identity
    name varchar(255) not null,
    role varchar(100) not null, -- 'researcher', 'designer', 'writer', etc.
    avatar_url text,
    color varchar(7) default '#00f3ff', -- for UI
    
    -- LLM Configuration
    model varchar(100) default 'claude-3-sonnet', -- claude, gpt, local
    system_prompt text not null,
    temperature float default 0.7,
    max_tokens int default 4096,
    
    -- Capabilities
    tools text[] default '{}', -- ['web_search', 'image_gen', 'code_exec']
    allowed_rooms text[] default '{}', -- room types this agent can enter
    
    -- State
    is_active boolean default true,
    total_tasks_completed int default 0,
    avg_task_duration interval,
    
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Room membership (active presence)
create table room_agents (
    id uuid primary key default gen_random_uuid(),
    room_id uuid not null references rooms(id) on delete cascade,
    agent_id uuid not null references agents(id) on delete cascade,
    
    -- Presence tracking
    status varchar(50) default 'idle', -- idle, working, paused, error, offline
    current_task_id uuid,
    
    -- Position (for 3D visualization)
    position_x float default 0,
    position_y float default 0,
    position_z float default 0,
    
    -- Lifecycle
    entered_at timestamptz default now(),
    last_heartbeat timestamptz default now(),
    left_at timestamptz,
    
    unique(room_id, agent_id)
);

-- Tasks with ownership + collaboration
create table tasks (
    id uuid primary key default gen_random_uuid(),
    room_id uuid not null references rooms(id) on delete cascade,
    
    -- Ownership
    owner_agent_id uuid not null references agents(id),
    contributor_agent_ids uuid[] default '{}', -- helpers
    
    -- Task definition
    type varchar(100) not null, -- 'research', 'design', 'write', 'review', 'execute'
    title varchar(500) not null,
    description text,
    priority int default 3, -- 1=critical, 5=low
    
    -- Status workflow
    status varchar(50) default 'pending', -- pending, queued, active, blocked, review, completed, failed
    
    -- Data
    input_payload jsonb default '{}', -- requirements, context
    output_payload jsonb default '{}', -- results, deliverables
    
    -- Relationships
    parent_task_id uuid references tasks(id), -- for task chains
    depends_on uuid[] default '{}', -- blocking dependencies
    
    -- Metrics
    created_at timestamptz default now(),
    started_at timestamptz,
    completed_at timestamptz,
    estimated_duration interval,
    actual_duration interval
);

-- Messaging system (broadcast + DM)
create table messages (
    id uuid primary key default gen_random_uuid(),
    room_id uuid not null references rooms(id) on delete cascade,
    
    -- Sender/receiver
    from_agent_id uuid not null references agents(id),
    to_agent_id uuid references agents(id), -- NULL = broadcast to room
    
    -- Content
    message_type varchar(50) default 'chat', -- chat, task_request, handoff, system, insight
    content text not null,
    metadata jsonb default '{}', -- attachments, references
    
    -- Threading
    reply_to uuid references messages(id),
    
    created_at timestamptz default now()
);

-- Activity log (immutable audit trail)
create table activities (
    id uuid primary key default gen_random_uuid(),
    room_id uuid not null references rooms(id) on delete cascade,
    agent_id uuid references agents(id),
    task_id uuid references tasks(id),
    
    activity_type varchar(100) not null, -- joined_room, started_task, completed_subtask, shared_insight
    description text not null,
    metadata jsonb default '{}',
    
    created_at timestamptz default now()
);

-- Indexes for performance
create index idx_projects_tenant on projects(tenant_id);
create index idx_rooms_project on rooms(project_id);
create index idx_room_agents_room on room_agents(room_id);
create index idx_room_agents_agent on room_agents(agent_id);
create index idx_room_agents_status on room_agents(status) where status != 'offline';
create index idx_tasks_room on tasks(room_id);
create index idx_tasks_owner on tasks(owner_agent_id);
create index idx_tasks_status on tasks(status);
create index idx_messages_room on messages(room_id);
create index idx_messages_created on messages(created_at desc);
create index idx_activities_room on activities(room_id, created_at desc);
```

---

## 3. Backend Architecture

### Layer Structure

```
┌─────────────────────────────────────────────┐
│           API Gateway (FastAPI)             │
│  Auth • Rate Limiting • Request Validation  │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│        Application Services                 │
│  • ProjectService                           │
│  • RoomService (context, presence)          │
│  • AgentService (lifecycle)                 │
│  • TaskService (orchestration)              │
│  • MessageService (routing)                 │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│        Domain Logic (Agents)                │
│  • AgentBrain (LLM integration)             │
│  • TaskExecutor (workflow engine)           │
│  • CollaborationProtocol (messaging)        │
└──────────────┬──────────────────────────────┘
               │
┌──────────────┴──────────────────────────────┐
│  PostgreSQL  │  Redis  │  WebSocket Manager │
└──────────────┴─────────┴────────────────────┘
```

### Key Services

```python
# Room Service — manages shared workspace
class RoomService:
    async def get_shared_context(self, room_id: UUID) -> dict:
        """Get current room state for all agents"""
        
    async def update_context(self, room_id: UUID, agent_id: UUID, 
                            updates: dict) -> dict:
        """Agent updates shared context (with conflict resolution)"""
        
    async def broadcast_message(self, room_id: UUID, from_agent: UUID,
                               content: str, msg_type: str = "chat"):
        """Send message to all agents in room"""
        
    async def get_active_presence(self, room_id: UUID) -> list[RoomAgent]:
        """Get who's online and what they're doing"""

# Task Service — manages execution
class TaskService:
    async def create_task(self, room_id: UUID, owner: UUID,
                         task_def: TaskCreate) -> Task:
        """Create and optionally auto-assign task"""
        
    async def assign_contributors(self, task_id: UUID, 
                                 contributor_ids: list[UUID]):
        """Add helpers to a task"""
        
    async def handoff_task(self, task_id: UUID, from_agent: UUID,
                          to_agent: UUID, handoff_notes: str):
        """Transfer ownership with context"""
        
    async def execute_task(self, task_id: UUID) -> TaskResult:
        """Run task through LLM agent"""

# Agent Brain — LLM integration
class AgentBrain:
    def __init__(self, agent_config: Agent):
        self.system_prompt = agent_config.system_prompt
        self.model = agent_config.model
        self.tools = self.load_tools(agent_config.tools)
        
    async def think(self, context: dict, task: Task) -> AgentAction:
        """Agent decides next action based on context"""
        
    async def execute(self, action: AgentAction) -> ExecutionResult:
        """Execute action (call tool, send message, etc.)"""
```

---

## 4. API Endpoints

### Projects
```
POST   /api/v1/projects              # Create project
GET    /api/v1/projects              # List tenant projects
GET    /api/v1/projects/{id}         # Get project details
PUT    /api/v1/projects/{id}         # Update project
DELETE /api/v1/projects/{id}         # Archive project
GET    /api/v1/projects/{id}/rooms   # List project rooms
```

### Rooms
```
POST   /api/v1/rooms                 # Create room
GET    /api/v1/rooms/{id}            # Get room (with context)
PUT    /api/v1/rooms/{id}/context    # Update shared context
POST   /api/v1/rooms/{id}/join       # Agent enters room
POST   /api/v1/rooms/{id}/leave      # Agent exits room
GET    /api/v1/rooms/{id}/agents     # List active agents
GET    /api/v1/rooms/{id}/tasks      # List room tasks
GET    /api/v1/rooms/{id}/messages   # Get message history
```

### Agents
```
POST   /api/v1/agents                # Create agent definition
GET    /api/v1/agents                # List tenant agents
GET    /api/v1/agents/{id}           # Get agent config
PUT    /api/v1/agents/{id}           # Update agent
POST   /api/v1/agents/{id}/clone     # Duplicate agent
DELETE /api/v1/agents/{id}           # Deactivate agent
```

### Tasks
```
POST   /api/v1/tasks                 # Create task
GET    /api/v1/tasks/{id}            # Get task details
PUT    /api/v1/tasks/{id}            # Update task
POST   /api/v1/tasks/{id}/start      # Begin execution
POST   /api/v1/tasks/{id}/pause      # Pause execution
POST   /api/v1/tasks/{id}/handoff    # Transfer ownership
POST   /api/v1/tasks/{id}/complete   # Mark done
POST   /api/v1/tasks/{id}/comment    # Add comment/update
```

### Messaging
```
POST   /api/v1/messages              # Send message (broadcast or DM)
GET    /api/v1/messages/unread       # Get unread for agent
POST   /api/v1/messages/{id}/read    # Mark as read
```

---

## 5. WebSocket / Real-Time Event Model

### Connection Flow
```
1. Client connects: ws://api.agentverse.io/ws/rooms/{room_id}
2. Server authenticates (token in query param)
3. Server sends: room_state snapshot
4. Client receives: live events as they happen
5. Heartbeat: every 30s ping/pong
```

### Event Types

**Server → Client:**
```javascript
// Room state on connect
{
  "type": "room_state",
  "room": { /* room details */ },
  "shared_context": { /* current brief, trends, etc */ },
  "active_agents": [
    {
      "agent_id": "uuid",
      "name": "Researcher Alpha",
      "status": "working",
      "current_task": { /* task summary */ },
      "position": {"x": 1.5, "y": 0, "z": 2.0}
    }
  ],
  "recent_messages": [ /* last 20 messages */ ],
  "active_tasks": [ /* in-progress tasks */ ]
}

// Agent joined room
{
  "type": "agent_joined",
  "agent": { /* agent details */ },
  "timestamp": "2024-01-15T10:30:00Z"
}

// Agent status changed
{
  "type": "agent_status_changed",
  "agent_id": "uuid",
  "old_status": "idle",
  "new_status": "working",
  "current_task_id": "uuid"
}

// New message (broadcast or DM)
{
  "type": "new_message",
  "message": {
    "id": "uuid",
    "from_agent_id": "uuid",
    "from_agent_name": "Designer Beta",
    "to_agent_id": null, // null = broadcast
    "content": "I've completed the logo variants",
    "message_type": "task_update",
    "metadata": {
      "attachments": ["url1", "url2"]
    }
  }
}

// Shared context updated
{
  "type": "context_updated",
  "updated_by": "agent_id",
  "updates": {
    "trending_keywords": ["new", "keywords"],
    "design_approved": true
  },
  "full_context": { /* complete new context */ }
}

// Task progress
{
  "type": "task_progress",
  "task_id": "uuid",
  "agent_id": "uuid",
  "progress": 65, // percent
  "status": "active",
  "current_step": "Generating variations...",
  "logs": ["step 1 done", "step 2 done"]
}

// Task completed
{
  "type": "task_completed",
  "task_id": "uuid",
  "agent_id": "uuid",
  "output": { /* task results */ },
  "duration_seconds": 120
}

// Agent handoff
{
  "type": "task_handoff",
  "task_id": "uuid",
  "from_agent_id": "uuid",
  "to_agent_id": "uuid",
  "handoff_notes": "Logo is 80% done, needs color refinement"
}
```

**Client → Server:**
```javascript
// Send message
{
  "action": "send_message",
  "content": "Can you help with this?",
  "to_agent_id": "uuid" // omit for broadcast
}

// Update agent status
{
  "action": "update_status",
  "status": "working",
  "current_task_id": "uuid"
}

// Update shared context
{
  "action": "update_context",
  "updates": {
    "key": "value"
  }
}

// Request task assignment
{
  "action": "request_task",
  "agent_id": "uuid",
  "task_type": "design"
}

// Heartbeat
{
  "action": "heartbeat",
  "timestamp": "2024-01-15T10:30:30Z"
}
```

---

## 6. Frontend Architecture

### Route Structure
```
/                         → Dashboard (list projects)
/p/:projectId             → Project view (list rooms)
/p/:projectId/r/:roomId   → Room workspace (main app)
/agents                   → Agent management
/settings                 → Tenant settings
```

### Room Workspace Layout
```
┌─────────────────────────────────────────────────────────────┐
│  🏢 Project: Q4 Campaign  │  🔴 Live  │  👥 3 agents active  │
├─────────────────┬───────────────────────────────┬───────────┤
│                 │                               │           │
│  ROOMS LIST     │      3D WORKSPACE             │  AGENT    │
│                 │                               │  DETAIL   │
│  ┌───────────┐  │   ┌─────────────────────┐    │  PANEL    │
│  │ Strategy ●│  │   │                     │    │           │
│  │ Creative  │  │   │   [3D visualization │    │  🤖 Name  │
│  │ Execution●│  │   │    of room with     │    │  💼 Role  │
│  └───────────┘  │   │    agents working]  │    │  ⏳ Task  │
│                 │   │                     │    │  📊 Stats │
│  SHARED CONTEXT │   └─────────────────────┘    │           │
│  ────────────── │                               │  💬 Chat  │
│  📋 Brief: ...  │   ROOM STATE OVERVIEW         │  📁 Files │
│  🔥 Trends: ... │   ─────────────────────────   │           │
│  ✅ Approved: 3 │   📋 Brief | 🔥 Trends | ✅   │           │
│  ⏳ Pending: 2  │   📁 Assets | 💬 Chat         │           │
│                 │                               │           │
└─────────────────┴───────────────────────────────┴───────────┘
```

### Component Hierarchy
```
App
├── Layout
│   ├── Header (project selector, notifications)
│   └── Sidebar (rooms list)
├── ProjectView
│   └── RoomCard[]
├── RoomWorkspace
│   ├── Room3DScene (Three.js visualization)
│   ├── RoomStateBar (brief, trends, assets)
│   ├── AgentPanel (selected agent details)
│   └── ChatPanel (messages)
├── AgentManager
│   └── AgentCard[]
└── SettingsView
```

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **LLM costs explode** | High | Token budgets per agent, rate limiting, caching |
| **Context window overflow** | High | Summarization, sliding window, vector storage |
| **Race conditions on shared context** | Medium | Optimistic locking, conflict resolution UI |
| **WebSocket reliability** | Medium | Reconnection logic, message replay, fallback polling |
| **Agent hallucinations** | High | Human checkpoints for critical actions, output validation |
| **Database performance** | Medium | Proper indexing, read replicas, connection pooling |

---

## 8. Missing Entities (Add Later)

- **Users** (human operators) — for auth and audit trails
- **Teams** (groups of users) — for permissions
- **Integrations** (Slack, Notion, GitHub) — for external connectivity
- **Templates** (project/room presets) — for faster setup
- **Analytics** (agent performance, project metrics) — for optimization
- **Billing** (usage tracking, invoices) — for SaaS monetization

---

## 9. MVP Scope (Week 1)

**Core (Must Have):**
- [ ] PostgreSQL schema + migrations
- [ ] FastAPI backend with core endpoints
- [ ] WebSocket real-time updates
- [ ] Basic 3D room visualization
- [ ] Agent creation + task assignment
- [ ] Shared context (read-only for MVP)

**Deferred (Post-MVP):**
- Multi-tenancy (single tenant for MVP)
- Authentication (internal use only)
- Agent-to-agent messaging
- Context write conflicts
- File uploads
- Mobile responsiveness

---

## 10. Scalable v2 Architecture

**Add for Scale:**
- **CQRS** — separate read/write models for performance
- **Event Sourcing** — immutable activity log, replay capability
- **Kubernetes** — auto-scaling agent containers
- **Vector DB** — Pinecone/Weaviate for agent memory
- **GraphQL** — flexible data fetching
- **Edge Deployment** — WebSocket servers near users
- **Agent Marketplace** — shareable agent definitions

---

**Next: Begin implementation in your existing repo?**
I'll:
1. Create new branch `arch/v2-multi-agent-platform`
2. Set up PostgreSQL schema
3. Refactor backend to new service structure
4. Keep Three.js frontend but wire to new API

Proceed?