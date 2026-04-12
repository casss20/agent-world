# Phase 4: Feature Expansion Integration Plan

**Goal:** Integrate camofox-browser (stealth browsing) and multica (agent orchestration) into AgentVerse platform.

## Components

### 1. Camofox Browser Integration
**Repo:** https://github.com/jo-inc/camofox-browser
**Purpose:** Anti-detection browser for agent web tasks

**Key Features:**
- C++ level anti-detection (bypasses Cloudflare, Google bot detection)
- Element refs (e1, e2, e3) for stable interaction
- Accessibility snapshots (90% smaller than raw HTML)
- Search macros (@google_search, @reddit_search, etc.)
- YouTube transcript extraction
- Session isolation per user
- Proxy + GeoIP support

**Integration Points:**
- Add to docker-compose as `camofox` service
- REST API on port 9377
- Agent workflows can call camofox for web tasks
- Content arbitrage Scout agent uses camofox for Reddit/data extraction

### 2. Multica Integration
**Repo:** https://github.com/multica-ai/multica
**Purpose:** Agent team orchestration (task delegation, Kanban, progress tracking)

**Key Features:**
- Agents as teammates (assign tasks like humans)
- Kanban board for task tracking
- Autonomous execution with WebSocket progress streaming
- Reusable skills that compound over time
- Multi-workspace support
- Works with Claude Code, Codex, OpenClaw, OpenCode

**Integration Points:**
- Add to docker-compose as `multica` service
- PostgreSQL database for task storage
- AgentVerse workflows can create tasks in Multica
- Scout/Maker/Merchant agents appear as Multica agents
- Task completion triggers workflow progression

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AgentVerse Platform                       │
├─────────────────────────────────────────────────────────────────┤
│  Nginx Load Balancer (8080)                                     │
│  ├─ /stateless/* → Adapter Instances (8004, 8005, 8006)        │
│  ├─ /metrics → Prometheus (9090)                               │
│  ├─ /camofox/* → Camofox Browser (9377)                        │
│  └─ /multica/* → Multica API (8081)                            │
├─────────────────────────────────────────────────────────────────┤
│  Services:                                                       │
│  ├─ adapter (3 instances) - Workflow execution                  │
│  ├─ camofox - Stealth browser server                            │
│  ├─ multica - Agent orchestration (Go backend)                  │
│  ├─ redis - Shared state                                        │
│  ├─ postgres - AgentVerse + Multica data                        │
│  ├─ prometheus - Metrics                                        │
│  └─ alertmanager - Alerts                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Step 1: Camofox Integration
1. Add camofox service to docker-compose.prod.yml
2. Configure nginx routing for /camofox/*
3. Create wrapper client in agent-world backend
4. Add camofox tools to workflow agents

### Step 2: Multica Integration
1. Add multica service to docker-compose.prod.yml
2. Configure nginx routing for /multica/*
3. Set up multica PostgreSQL schema
4. Create multica client in agent-world backend
5. Add task creation/completion hooks

### Step 3: Unified Workflow
1. Scout agent uses camofox to browse Reddit
2. Scout creates tasks in Multica for Maker
3. Maker picks up tasks from Multica board
4. Merchant tracks publishing in Multica
5. Revenue tracking updates Multica task status

## API Contracts

### Camofox API (from existing repo)
```
POST /tabs                    # Create tab
GET  /tabs/:id/snapshot       # Get accessibility snapshot
POST /tabs/:id/click          # Click element by ref
POST /tabs/:id/type           # Type text
POST /tabs/:id/navigate       # Navigate with macro
GET  /tabs/:id/screenshot     # Take screenshot
POST /youtube/transcript      # Extract captions
```

### Multica API (from existing repo)
```
POST /api/v1/issues           # Create issue/task
GET  /api/v1/issues           # List issues
GET  /api/v1/issues/:id       # Get issue details
POST /api/v1/issues/:id/assign # Assign to agent
POST /api/v1/issues/:id/status # Update status
GET  /api/v1/agents           # List agents
POST /api/v1/agents           # Create agent
```

## Environment Variables

### Camofox
```
CAMOFOX_PORT=9377
MAX_SESSIONS=50
SESSION_TIMEOUT_MS=1800000
PROXY_HOST=
PROXY_PORT=
PROXY_USERNAME=
PROXY_PASSWORD=
```

### Multica
```
MULTICA_PORT=8081
POSTGRES_USER=multica
POSTGRES_PASSWORD=multica
POSTGRES_DB=multica
JWT_SECRET=
```

## Testing Plan

1. **Camofox Tests:**
   - Create tab and navigate to Reddit
   - Extract accessibility snapshot
   - Click element by ref
   - Search macro execution
   - YouTube transcript extraction

2. **Multica Tests:**
   - Create agent via API
   - Create issue/task
   - Assign to agent
   - Update status
   - WebSocket progress streaming

3. **Integration Tests:**
   - Scout browses Reddit via camofox
   - Scout creates Multica task for Maker
   - Maker completes task, updates status
   - End-to-end workflow with both tools

## Success Criteria

- [ ] Camofox accessible at /camofox/* via nginx
- [ ] Multica accessible at /multica/* via nginx
- [ ] Scout agent can browse Reddit via camofox
- [ ] Maker agent can pick up tasks from Multica
- [ ] End-to-end workflow completes with both tools
- [ ] All tests passing
