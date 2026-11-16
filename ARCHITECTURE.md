# AgentWorld — Clean Architecture

> **Last updated:** 2026-05-15  
> **Branch:** `enterprise-architecture`  
> **Tests:** 78/78 passing  
> **Routes:** 193 registered

---

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  ┌──────────────┐ ┌─────────────┐ ┌──────────────────────┐  │
│  │ AgentChat    │ │ Dashboard   │ │ SwarmMonitor         │  │
│  │ (WebSocket)  │ │ (REST)      │ │ (REST + WS)          │  │
│  └──────┬───────┘ └──────┬──────┘ └──────────┬───────────┘  │
│  ┌──────┴───────┐ ┌──────┴──────┐ ┌────────────┴──────────┐  │
│  │ AgentDirectory│ │ Business    │ │ ProviderStatusPanel   │  │
│  │ (Role cards)  │ │ Workspace   │ │ (Health dashboard)    │  │
│  └───────────────┘ └─────────────┘ └─────────────────────┘  │
└────────────────────────────────────┬────────────────────────┘
                                     │ HTTP / WebSocket
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                   │
│                                                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│  │ /api/agents│ │ /api/orch..│ │ /api/plugins│ │ /api/cred..│  │
│  │ (chat)     │ │ (swarm)    │ │ (registry)  │ │ (secrets)  │  │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘  │
│  ┌─────┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐  │
│  │ /api/rooms │ │ /api/tasks │ │ /api/files │ │ /api/gov.. │  │
│  │ (channels) │ │ (queue)    │ │ (S3)       │ │ (audits)   │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘  │
│                                                              │
│  Auth: JWT + API Key + Ed25519 Challenge-Response             │
│  Middleware: CORSMiddleware + SecurityHeaders + RateLimit    │
│  Telemetry: OpenTelemetry (optional)                          │
└────────────────────────────────────┬────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                              │
│                                                              │
│  ┌────────────────────┐    ┌────────────────────┐            │
│  │ AgentChatService   │    │ SwarmOrchestrator  │            │
│  │ - chat()           │    │ - decompose_task() │            │
│  │ - assign_task()    │    │ - spawn_swarm()     │            │
│  │ - get_history()    │    │ - get_metrics()     │            │
│  └────────────────────┘    └────────────────────┘            │
│  ┌────────────────────┐    ┌────────────────────┐            │
│  │ CredentialManager  │    │ PluginLoader       │            │
│  │ - get/set/has()    │    │ - scan()            │            │
│  │ - validate()       │    │ - load_all()        │            │
│  └────────────────────┘    └────────────────────┘            │
│  ┌────────────────────┐    ┌────────────────────┐            │
│  │ TaskService        │    │ MessageService     │            │
│  │ - create/assign    │    │ - broadcast         │            │
│  │ - transition       │    │ - websocket        │            │
│  └────────────────────┘    └────────────────────┘            │
└────────────────────────────────────┬────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   PLUGIN / PROVIDER LAYER                    │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐  │
│  │ BaseProvider │  │ PluginRegistry│  │ PluginLoader        │  │
│  │ (ABC)       │  │ (singleton)   │  │ (importlib scanner)  │  │
│  └──────┬──────┘  └─────────────┘  └──────────────────────┘  │
│         │                                                    │
│  ┌──────┴──────┬──────────────┬──────────────┬─────────────┐  │
│  │ Image Gen   │ Video Gen    │ Communication│ Tools       │  │
│  │ • DALL-E    │ • Runway     │ • Slack      │ • (extensible)│  │
│  └─────────────└──────────────└──────────────└─────────────┘  │
│                                                              │
│  LEGACY: plugin_manager.py (still active, not replaced)      │
└────────────────────────────────────┬────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  WORKFLOW / ORCHESTRATION                      │
│                                                              │
│  ┌────────────────────┐    ┌────────────────────┐            │
│  │ WorkflowEngineNative│    │ Legacy PluginMgr   │            │
│  │ - execute_workflow()│    │ (from Ruflo)       │            │
│  │ - rollback()       │    │ - lifecycle hooks   │            │
│  │ - pause/resume     │    │ - dependency graph  │            │
│  └────────────────────┘    └────────────────────┘            │
│                                                              │
│  Features: nested workflows, state persistence, metrics    │
│  Dispatcher: orcestrator.py (agent dispatch)                 │
└────────────────────────────────────┬────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      ROLE-BASED AGENTS                       │
│                                                              │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌─────────────┐ ┌─────┐  │
│  │  CEO   │ │  COO   │ │ Developer│ │Content Dir. │ │ CRM │  │
│  │ Alex   │ │ Jordan │ │   Sam    │ │   Taylor    │ │Casey│  │
│  │ 👔     │ │ ⚙️     │ │   💻     │ │    🎨      │ │ 🤝  │  │
│  │ P: 10  │ │ P: 9   │ │   P: 8   │ │    P: 7    │ │ P: 7│  │
│  └────────┘ └────────┘ └──────────┘ └─────────────┘ └─────┘  │
│                                                              │
│  Registry: agents/roles/role_definitions.py                  │
│  Escalation: bidirectional (strategic → CEO, ops → COO)      │
└────────────────────────────────────┬────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE                           │
│                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐│
│  │   MCP Manager│ │  Redis Cache │ │   WebSocket Manager     ││
│  │  (servers)   │ │  (sessions)  │ │   (realtime broadcast)  ││
│  └─────────────┘ └─────────────┘ └────────────────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐│
│  │   Database   │ │   S3/Cloud  │ │   Prometheus Metrics    ││
│  │  (SQLAlchemy)│ │   (files)   │ │   (optional)           ││
│  └─────────────┘ └─────────────┘ └────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
agent-world/
├── backend/
│   ├── main.py                    # FastAPI app (193 routes)
│   ├── models.py                  # SQLAlchemy tables (+4 new)
│   ├── database.py                # Async session + init
│   ├── auth.py                    # JWT + API key + Ed25519
│   │
│   ├── agents/
│   │   └── roles/
│   │       └── role_definitions.py        # CEO, COO, Dev, etc.
│   │
│   ├── plugins/
│   │   ├── base/
│   │   │   ├── base_provider.py           # ABC
│   │   │   └── plugin_registry.py         # Singleton locator
│   │   ├── plugin_loader.py               # Dynamic scanner
│   │   └── providers/
│   │       ├── image_gen/
│   │       │   └── dalle_provider.py      # DALL-E 3
│   │       ├── video_gen/
│   │       │   └── runway_provider.py     # Runway ML
│   │       └── communication/
│   │           ├── slack_provider.py      # Slack
│   │           └── sendgrid_provider.py   # SendGrid
│   │
│   ├── services/
│   │   ├── agent_chat_service.py          # Chat + tasks
│   │   ├── orchestrator_service.py        # Swarm engine
│   │   └── credential_manager.py          # API key mgmt
│   │
│   ├── routes/
│   │   ├── agent_chat.py                  # Agent REST + WS
│   │   ├── orchestrator.py                # Swarm REST + WS
│   │   ├── plugin_registry.py             # Provider API
│   │   └── credentials.py                 # Secrets API
│   │
│   ├── infrastructure/
│   │   └── mcp/
│   │       └── mcp_manager.py             # MCP servers
│   │
│   ├── workflow_engine_native.py          # From Ruflo
│   ├── plugin_manager.py                 # Legacy (still active)
│   │
│   └── tests/
│       ├── test_infrastructure.py         # 10 tests
│       ├── test_advanced.py               # 10 tests
│       ├── test_plugin_workflow.py        # 19 tests
│       ├── test_plugin_system.py          # 20 tests
│       └── test_enterprise.py             # 19 tests
│
├── frontend-react/
│   └── src/
│       ├── components/
│       │   └── agents/
│       │       ├── AgentDashboard.jsx      # Agent directory
│       │       ├── AgentChatPanel.jsx      # Real-time chat
│       │       ├── SwarmMonitor.jsx        # Swarm tracking
│       │       ├── ProviderStatusPanel.jsx # Provider health
│       │       └── index.js               # Exports
│       └── App.jsx                         # Routing
│
└── ENTERPRISE_ARCHITECTURE.md            # This doc
```

---

## Data Flow Examples

### 1. Chat with an Agent

```
User ──POST /api/agents/ceo/chat──► AgentChatService.chat()
                                        │
                                        ▼
                              ┌─────────────────┐
                              │  AgentRole (CEO)│
                              │  - goal         │
                              │  - backstory    │
                              │  - allowed_tools│
                              └─────────────────┘
                                        │
                                        ▼
                              ┌─────────────────┐
                              │  Generate response│
                              │  (LLM placeholder)│
                              └─────────────────┘
                                        │
                                        ▼
                              ┌─────────────────┐
                              │  AgentConversation│
                              │  (DB persistence) │
                              └─────────────────┘
                                        │
                                        ▼
                                   Response JSON
```

### 2. Spawn a Swarm

```
User ──POST /api/orchestrator/swarm/spawn──► SwarmOrchestrator.spawn_swarm()
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              ▼                                           ▼
                    decompose_task()                              create SwarmExecution
                    (low/medium/high)                              (DB record)
                              │                                           │
                              ▼                                           ▼
                    ┌─────────────────┐                          ┌─────────────────┐
                    │ Subtask list    │                          │ WorkflowDefinition│
                    │ - Research      │                          │ - Task[]         │
                    │ - Analysis      │                          │ - Parallel exec  │
                    │ - Draft         │                          └─────────────────┘
                    └─────────────────┘                                    │
                              │                                           ▼
                              │                                execute_workflow()
                              │                                (WorkflowEngineNative)
                              │                                           │
                              ▼                                           ▼
                    ┌─────────────────┐                          ┌─────────────────┐
                    │ Spawn agents    │                          │ Update SwarmExecution│
                    │ - CEO reviews   │                          │ - tasks_completed   │
                    │ - Dev implements│                          │ - status = done     │
                    └─────────────────┘                          └─────────────────┘
```

### 3. Load a Provider Plugin

```
App boot ──► PluginLoader.load_all_plugins()
                      │
                      ▼
            Scan plugins/providers/
            └── image_gen/
            │   └── dalle_provider.py ──► DalleProvider()
            └── video_gen/
            │   └── runway_provider.py ──► RunwayProvider()
            └── communication/
                ├── slack_provider.py ──► SlackProvider()
                └── sendgrid_provider.py ──► SendGridProvider()
                      │
                      ▼
            Register in PluginRegistry
            (name → instance mapping)
                      │
                      ▼
            Frontend GET /api/plugins/registry
            Returns: [{name, type, version, status, credentials}]
```

---

## Request Lifecycle

```
┌────────┐    ┌────────────┐    ┌──────────┐    ┌─────────┐    ┌────────┐
│ Client │───►│   CORS     │───►│  Auth    │───►│  Rate   │───►│ Route  │
│        │    │ Middleware │    │ Middleware│    │ Limiter │    │ Handler│
└────────┘    └────────────┘    └──────────┘    └─────────┘    └───┬────┘
                                                                    │
                                                                    ▼
                                                           ┌────────────┐
                                                           │   Service   │
                                                           │   Layer     │
                                                           └─────┬──────┘
                                                                 │
                                                                 ▼
                                                           ┌────────────┐
                                                           │   Database  │
                                                           │  (SQLite/   │
                                                           │   Postgres) │
                                                           └────────────┘
```

---

## Authentication Layers

| Layer | Mechanism | Use Case |
|-------|-----------|----------|
| 1 | JWT Bearer | User sessions |
| 2 | API Key + Secret | Service-to-service |
| 3 | Ed25519 Challenge-Response | Agent identities |
| 4 | RBAC Roles | Authorization |

---

## Plugin Architecture (Java-style → Python)

```
┌─────────────────────────────────────┐
│         BaseProvider (ABC)          │
│  - initialize(config)               │
│  - execute(params) → Result         │
│  - health_check() → bool            │
│  - get_capability() → Capability    │
│  - validate_parameters() → missing  │
└──────────────┬──────────────────────┘
               │ implements
       ┌───────┼───────┐
       ▼       ▼       ▼
┌────────┐ ┌────────┐ ┌────────┐
│ Dalle  │ │ Slack  │ │ Runway │
│Provider│ │Provider│ │Provider│
└────────┘ └────────┘ └────────┘
       │       │       │
       └───────┼───────┘
               ▼
     ┌─────────────────┐
     │  PluginRegistry  │
     │  (singleton)     │
     │  - register()    │
     │  - get_provider()│
     │  - health_check()│
     └─────────────────┘
```

---

## State Machines

### Task Lifecycle
```
pending ──► in_progress ──► completed
   │            │
   └────────────┴──► failed ──► retry ──► pending
```

### Swarm Lifecycle
```
spawning ──► in_progress ──► completed
   │              │
   └──────────────┴──► failed ──► rollback
```

### Provider Lifecycle
```
registered ──► initialized ──► active
   │              │
   └──────────────┴──► error ──► inactive
```

---

## Testing Pyramid

```
        ┌─────────┐
        │  E2E    │  test_enterprise.py (19)
        │  Tests  │  - Full flows: chat → task → swarm
        ├─────────┤
        │ Service │  test_plugin_system.py (20)
        │ Tests   │  - Plugin loading, registry, roles
        ├─────────┤
        │ Engine  │  test_plugin_workflow.py (19)
        │ Tests   │  - Workflow execution, rollback
        ├─────────┤
        │ Infra   │  test_infrastructure.py (10)
        │ Tests   │  - DB, cache, websockets
        ├─────────┤
        │ Unit    │  test_advanced.py (10)
        │ Tests   │  - Cache, orchestrator, tasks
        └─────────┘
```

---

## Deployment View

```
┌─────────────────────────────────────────────────────────┐
│                     Docker / K8s                         │
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                 │
│  │   Frontend   │◄────►│   Backend    │                 │
│  │   (React)    │      │   (FastAPI)  │                 │
│  │   Port 3000  │      │   Port 8000  │                 │
│  └──────────────┘      └──────┬───────┘                 │
│                               │                         │
│                        ┌──────┴──────┐                   │
│                        │  Database   │                   │
│                        │ (PostgreSQL │                   │
│                        │  or SQLite) │                   │
│                        └─────────────┘                   │
│                                                          │
│  Optional:                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │    Redis     │  │   Prometheus │  │  Grafana     │   │
│  │   (cache)    │  │   (metrics)  │  │  (dashboard) │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  External APIs:                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  OpenAI  │ │  Runway  │ │  Slack   │ │ SendGrid │   │
│  │  (DALL-E)│ │  (video) │ │  (chat)  │ │  (email) │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| **BaseProvider ABC** | Java-style interface adapted for Python; agents call interface, never concrete class |
| **PluginRegistry singleton** | Service locator pattern; avoids dependency injection complexity |
| **PluginLoader category dirs** | `plugins/providers/<category>/<name>_provider.py` for clean organization |
| **Coexist with legacy** | `plugin_manager.py` still active; new system doesn't break old |
| **Feature branch workflow** | All new work on `enterprise-architecture`; `main` stays stable |
| **SQLite default** | Zero-config for dev; PostgreSQL for production |
| **Placeholder LLM responses** | Architecture ready; wire to GPT-4/Claude when ready |
| **Placeholder provider APIs** | Structure complete; add real HTTP calls with API keys |

---

## Quick Commands

```bash
# Run everything
cd agent-world/backend && python main.py

# Tests
cd agent-world/backend && pytest tests/ -v

# Database reset
cd agent-world/backend && python -c "from database import init_db; asyncio.run(init_db())"

# Chat with CEO
curl -X POST http://localhost:8000/api/agents/ceo/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-1", "message": "What is our strategy?"}'

# Spawn swarm
curl -X POST http://localhost:8000/api/orchestrator/swarm/spawn \
  -H "Content-Type: application/json" \
  -d '{"description": "Build a marketing campaign", "complexity": "high"}'

# Check providers
curl http://localhost:8000/api/plugins/registry

# Check credentials
curl http://localhost:8000/api/credentials/status
```

---

## Files Changed (Enterprise Architecture)

```
26 files changed, 3530 insertions(+)

New:
├── backend/agents/roles/role_definitions.py
├── backend/infrastructure/mcp/mcp_manager.py
├── backend/plugins/base/base_provider.py
├── backend/plugins/base/plugin_registry.py
├── backend/plugins/plugin_loader.py
├── backend/plugins/providers/image_gen/dalle_provider.py
├── backend/plugins/providers/video_gen/runway_provider.py
├── backend/plugins/providers/communication/slack_provider.py
├── backend/plugins/providers/communication/sendgrid_provider.py
├── backend/routes/agent_chat.py
├── backend/routes/credentials.py
├── backend/routes/orchestrator.py
├── backend/routes/plugin_registry.py
├── backend/services/agent_chat_service.py
├── backend/services/credential_manager.py
├── backend/services/orchestrator_service.py
├── backend/tests/test_enterprise.py
├── backend/tests/test_plugin_system.py
├── frontend-react/src/components/agents/AgentChatPanel.jsx
├── frontend-react/src/components/agents/AgentDashboard.jsx
├── frontend-react/src/components/agents/ProviderStatusPanel.jsx
├── frontend-react/src/components/agents/SwarmMonitor.jsx
└── frontend-react/src/components/agents/index.js

Modified:
├── backend/main.py           (+ routes wiring)
├── backend/models.py         (+ 4 tables)
└── frontend-react/src/App.jsx (+ new routes)
```

---

**Built:** 2026-05-15  
**Branch:** `enterprise-architecture`  
**Tests:** 78/78 passing  
**Routes:** 193 registered  
**Commit:** `eca1f94`
