# AgentWorld v2.0 — Complete System Map

```
┌═══════════════════════════════════════════════════════════════════════════════════════┐
│                              YOU (Anthony) — TENANT                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│  │  DASHBOARD: All 5 Businesses, Budgets, Agents, Rooms, Revenue                  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │  │
│  │  │ 🥤BEV    │ │ 📱TIKTOK │ │ 🎬YOUTUBE│ │ 🎧SPOTIFY│ │ 💡SIDE   │               │  │
│  │  │ $247     │ │ $89      │ │ $156     │ │ $45      │ │ $500     │               │  │
│  │  │ 5 agents │ │ 3 agents │ │ 2 agents │ │ 2 agents │ │ 1 agent  │               │  │
│  │  │ 3 rooms  │ │ 4 rooms  │ │ 2 rooms  │ │ 2 rooms  │ │ 1 room   │               │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘               │  │
│  └─────────────────────────────────────────────────────────────────────────────────┘  │
└═══════════════════════════════════════════════════════════════════════════════════════┘
                                          │
                                          ▼
┌═══════════════════════════════════════════════════════════════════════════════════════┐
│                           FRONTEND — React (Week 10)                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│  │  BaseComponent  │  BaseService  │  BaseModel  │  AgentDashboard  │  ChatPanel   │  │
│  │  SwarmMonitor   │  ProviderPanel│  RoomView   │  RevenueChart    │  TaskBoard   │  │
│  └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                            │
│                                          ▼ HTTP/WebSocket                             │
└═══════════════════════════════════════════════════════════════════════════════════════┘
                                          │
                                          ▼
┌═══════════════════════════════════════════════════════════════════════════════════════┐
│                         API LAYER — FastAPI (207 Routes)                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│  │  BaseRouter ◄─── /api/agents  │  /api/rooms  │  /api/projects  │  /api/ledger   │  │
│  │  BaseRouter ◄─── /api/orchestrator  │  /api/billing  │  /api/governance         │  │
│  │  BaseMiddleware ◄── Auth  │  Rate Limit  │  CORS  │  Audit                     │  │
│  └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                            │
│                                          ▼ Dependency Injection (Registries)            │
└═══════════════════════════════════════════════════════════════════════════════════════┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              ▼                           ▼                           ▼
┌═══════════════════════┐ ┌═══════════════════════┐ ┌═══════════════════════┐
│   ORCHESTRATOR        │ │      GOVERNANCE       │ │      LEDGER           │
│   (Week 7)            │ │      (Week 6)         │ │      (Week 6)         │
│                       │ │                       │ │                       │
│  ┌─────────────────┐  │ │  ┌─────────────────┐  │ │  ┌─────────────────┐  │
│  │BaseOrchestrator │  │ │  │BaseGovernance   │  │ │  │BaseLedger       │  │
│  │  decompose()    │  │ │  │  approve()      │  │ │  │  record()       │  │
│  │  spawn()        │◄─┼─┼──│  audit()        │  │ │  │  balance()      │  │
│  │  monitor()      │  │ │  │  validate()     │  │ │  │  audit_trail()  │  │
│  │  cancel()       │  │ │  │  rollback()     │  │ │  │  approve()      │  │
│  └─────────────────┘  │ │  └─────────────────┘  │ │  └─────────────────┘  │
│           │           │ │           │           │ │           │           │
│  ┌─────────────────┐  │ │  ┌─────────────────┐  │ │  ┌─────────────────┐  │
│  │NativeOrchestrator│  │ │  │LocalGovernance  │  │ │  │LocalLedger      │  │
│  │  (task router)   │  │ │  │  (rules engine) │  │ │  │  (in-memory)    │  │
│  └─────────────────┘  │ │  └─────────────────┘  │ │  └─────────────────┘  │
│           │           │ │           │           │ │           │           │
│           ▼           │ │           ▼           │ │           ▼           │
│  ┌─────────────────┐  │ │  ┌─────────────────┐  │ │  ┌─────────────────┐  │
│  │  Task Queue     │  │ │  │  Kill Switch    │  │ │  │  Budget Alert   │  │
│  │  Priority Sort  │  │ │  │  Quarantine     │  │ │  │  Cost Report    │  │
│  │  Auto-routing   │  │ │  │  Compliance     │  │ │  │  Revenue Track  │  │
│  └─────────────────┘  │ │  └─────────────────┘  │ │  └─────────────────┘  │
└═══════════════════════┘ └═══════════════════════┘ └═══════════════════════┘
              │                           │                           │
              └───────────────────────────┼───────────────────────────┘
                                          ▼
┌═══════════════════════════════════════════════════════════════════════════════════════┐
│                         CORE AGENTS (The Swarm)                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │   CEO AGENT  │ │  CFO AGENT   │ │ MARKETING    │ │   SECURITY   │ │   CONTENT    ││
│  │   (Leader)   │ │  (Money)     │ │  (Growth)    │ │  (Guard)     │ │  (Create)    ││
│  │              │ │              │ │              │ │              │ │              ││
│  │ • Strategy   │ │ • Budget     │ │ • Ads        │ │ • Compliance │ │ • Write      ││
│  │ • Decide     │ │ • Track      │ │ • SEO        │ │ • Scan       │ │ • Video      ││
│  │ • Approve    │ │ • Forecast   │ │ • Social     │ │ • Block      │ │ • Research   ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘│
│           │                │               │               │               │          │
│           └────────────────┴───────────────┴───────────────┴───────────────┘          │
│                                          │                                            │
│                                          ▼ BaseAgentBrain                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│  │  think() → plan() → reflect() → decide() → remember() → recall()              │  │
│  │  Each agent has its own memory (room-scoped)                                     │  │
│  └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                            │
│                                          ▼ BaseLLMProvider (Week 1)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │  │
│  │   OpenAI     │ │  Anthropic   │ │   Ollama     │ │   Legacy     │              │  │
│  │  GPT-4o      │ │   Claude     │ │  (Free/Local)│ │  (Current)   │              │  │
│  │  $0.01/1K    │ │  $0.03/1K    │ │   $0.00      │ │  (Mixed)     │              │  │
│  │  Images      │ │  Code        │ │  Llama3      │ │  (Fallback)  │              │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘              │  │
│  get_llm_provider() → checks LLM_PROVIDER env → auto-fallback if one fails           │  │
└═══════════════════════════════════════════════════════════════════════════════════════┘
                                          │
                                          ▼
┌═══════════════════════════════════════════════════════════════════════════════════════┐
│                      PROJECT / ROOM ISOLATION (Database)                              │
│                                                                                       │
│   TENANT (You)                                                                        │
│      │                                                                                │
│      ├── PROJECT: "Beverage Co"  ←── project_id = "bev_001"                          │
│      │     │                                                                          │
│      │     ├── ROOM: "Flavor Lab"      (agents, tasks, messages scoped here)          │
│      │     ├── ROOM: "Supply Chain"    (completely separate data)                     │
│      │     └── ROOM: "Marketing"       (ledger tracks per-project)                     │
│      │                                                                                │
│      ├── PROJECT: "TikTok Empire"  ←── project_id = "tiktok_002"                       │
│      │     │                                                                          │
│      │     ├── ROOM: "Viral Factory"   (trend data isolated)                           │
│      │     ├── ROOM: "Content Calendar"                                                │
│      │     └── ROOM: "Analytics"                                                       │
│      │                                                                                │
│      ├── PROJECT: "YouTube"  ←── project_id = "yt_003"                                │
│      ├── PROJECT: "Spotify"  ←── project_id = "spotify_004"                           │
│      └── PROJECT: "Side Hustle"  ←── project_id = "side_005"                           │
│                                                                                       │
│   Query for TikTok:  WHERE project_id = "tiktok_002"  ←── NEVER sees Beverage data    │
│   Ledger for TikTok:  WHERE project_id = "tiktok_002"  ←── separate budget            │
│   Agents in TikTok:   WHERE room.project_id = "tiktok_002"  ←── scoped agents         │
│                                                                                       │
└═══════════════════════════════════════════════════════════════════════════════════════┘
                                          │
                                          ▼
┌═══════════════════════════════════════════════════════════════════════════════════════┐
│                         INFRASTRUCTURE (Providers via Registry)                       │
│                                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │  STORAGE     │  │   QUEUE      │  │   AUTH       │  │   CACHE      │  │   FILE   │ │
│  │              │  │              │  │              │  │              │  │          │ │
│  │ PostgreSQL   │  │ Memory       │  │ JWT          │  │ Memory       │  │ Local    │ │
│  │ SQLite       │  │ Redis        │  │ OAuth        │  │ Redis        │  │ S3       │ │
│  │ (Primary)    │  │ (Fallback)   │  │ (Primary)    │  │ (Dev)        │  │ (Dev)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  HTTP        │  │  MESSAGING    │  │  SELF-HEALING│  │   SCOUT      │              │
│  │              │  │              │  │              │  │              │              │
│  │ Httpx        │  │ WebSocket    │  │ Retry        │  │ Reddit       │              │
│  │ (Default)    │  │ (Default)    │  │ Circuit Break│  │ HackerNews   │              │
│  │              │  │              │  │ Recovery     │  │ ProductHunt  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                                       │
│  ALL providers swappable via env vars:                                                │
│  DB_PROVIDER=postgresql │ QUEUE_PROVIDER=memory │ AUTH_PROVIDER=jwt                  │
│                                                                                       │
└═══════════════════════════════════════════════════════════════════════════════════════┘
                                          │
                                          ▼
┌═══════════════════════════════════════════════════════════════════════════════════════┐
│                         EXTERNAL INTEGRATIONS                                         │
│                                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐│
│  │   TIKTOK     │  │   YOUTUBE    │  │   SPOTIFY    │  │   STRIPE     │  │  S3      ││
│  │   API        │  │   API        │  │   API        │  │   API        │  │  Cloud   ││
│  │              │  │              │  │              │  │              │  │          ││
│  │ Post videos  │  │ Upload shorts│  │ Distribute   │  │ Billing      │  │ Files    ││
│  │ Get analytics│  │ Monetization │  │ Podcasts     │  │ Subscriptions│  │ Images   ││
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘│
│                                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                                 │
│  │   OPENAI     │  │  ANTHROPIC   │  │   OLLAMA     │                                 │
│  │   API        │  │   API        │  │   (Local)    │                                 │
│  │              │  │              │  │              │                                 │
│  │ GPT-4o       │  │ Claude 3.5   │  │ Llama 3      │                                 │
│  │ DALL-E       │  │              │  │ Mistral      │                                 │
│  │ Embeddings   │  │              │  │ Free         │                                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                                 │
│                                                                                       │
└═══════════════════════════════════════════════════════════════════════════════════════┘
```

---

## Data Flow: Your Command "Make Money with a Story"

```
YOU ──► Dashboard ──► API
                          │
                          ▼
                   Orchestrator.decompose()
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        Governance    Ledger      Content Agent
        approve()    balance()    ──► Scout.scrape(REDDIT)
                          │           │
                          ▼           ▼
                     BUDGET OK    Brain.think()
                          │           │
                          ▼           ▼
                     Content Agent ──► LLM.complete()
                          │           │
                          ▼           ▼
                     Marketing Agent ──► Video Gen
                          │
                          ▼
                     Security Agent ──► Compliance Check
                          │
                          ▼
                     CRM Agent ──► TikTok API + YouTube API
                          │
                          ▼
                     Ledger ──► Record Cost (-$12.54)
                          │
                          ▼
                     YOU ◄── Dashboard: "Video Live, ROI 275%"
```

---

## Isolation: Why Your 5 Businesses Never Mix

```
┌─────────────────────────────────────────────────────────────┐
│  PROJECT: "Beverage Co" (project_id: bev_001)              │
│  ├── Room: "Flavor Lab"                                     │
│  │   ├── Agent: "Chemist" (only sees bev_001 data)         │
│  │   ├── Tasks: "Develop flavor #7"                        │
│  │   ├── Ledger: bev_001 account ($247)                   │
│  │   └── Messages: "Testing notes..."                      │
│  │                                                          │
│  └── Room: "Supply Chain"                                   │
│      ├── Agent: "Logistics" (only sees bev_001 data)        │
│      └── Tasks: "Source bottles"                            │
│                                                             │
│  SQL QUERY: SELECT * FROM tasks WHERE project_id = "bev_001"│
│  → NEVER returns TikTok tasks                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  PROJECT: "TikTok Empire" (project_id: tiktok_002)        │
│  ├── Room: "Viral Factory"                                  │
│  │   ├── Agent: "VideoEditor" (only sees tiktok_002 data) │
│  │   ├── Tasks: "Make trend video #3"                      │
│  │   ├── Ledger: tiktok_002 account ($89)                 │
│  │   └── Messages: "Hook idea..."                           │
│  │                                                          │
│  └── Room: "Trend Scout"                                  │
│      ├── Agent: "Scout" (only sees tiktok_002 data)        │
│      └── Tasks: "Find Reddit trends"                        │
│                                                             │
│  SQL QUERY: SELECT * FROM tasks WHERE project_id = "tiktok_002"│
│  → NEVER returns Beverage tasks                             │
└─────────────────────────────────────────────────────────────┘
```

Every table has `project_id`. Every query is scoped. Every agent is bound to rooms in ONE project.

---

## The OOP Layer Cake

```
┌────────────────────────────────────────────┐
│  Layer 5: YOU (Dashboard + Commands)        │
│     React frontend, WebSocket real-time    │
├────────────────────────────────────────────┤
│  Layer 4: API (Routes + Middleware)         │
│     BaseRouter, BaseMiddleware, 207 routes │
├────────────────────────────────────────────┤
│  Layer 3: CORE (Brains + Orchestration)    │
│     BaseOrchestrator, BaseAgentBrain       │
│     BaseGovernance, BaseLedger             │
│     5 Role Agents (CEO, CFO, etc.)         │
├────────────────────────────────────────────┤
│  Layer 2: SERVICES (Business Logic)        │
│     RoomService, AgentChatService, etc.    │
│     Project-scoped, Room-scoped            │
├────────────────────────────────────────────┤
│  Layer 1: INFRASTRUCTURE (Providers)       │
│     BaseStorage, BaseQueue, BaseAuth         │
│     BaseCache, BaseFile, BaseHTTP          │
│     BaseMessaging, BaseSelfHealing         │
│     All swappable via registry             │
├────────────────────────────────────────────┤
│  Layer 0: EXTERNAL APIs                   │
│     OpenAI, TikTok, YouTube, Stripe, etc.  │
└────────────────────────────────────────────┘
```

---

## Key Numbers

| Metric | Value |
|--------|-------|
| **Interfaces** | 22 (all ABC) |
| **Implementations** | 15+ concrete providers |
| **Registries** | 5 (LLM, Storage, Queue, Auth, Cache) |
| **Tests** | 130/130 passing |
| **Routes** | 207 operational |
| **Role Agents** | 5 (CEO, CFO, Marketing, Security, Content) |
| **Projects** | Unlimited per tenant |
| **Rooms** | Unlimited per project |
| **Agents** | Unlimited per room |
| **Business Isolation** | 100% (project_id foreign key on every table) |

---

## Swapping Providers = One Line

```bash
# Switch LLM from OpenAI to local (free)
LLM_PROVIDER=ollama

# Switch database from PostgreSQL to SQLite
DB_PROVIDER=sqlite

# Switch queue from memory to Redis
QUEUE_PROVIDER=redis

# No code changes. No redeploy. Just restart.
```

---

**This is AgentWorld v2.0. One tenant. Five businesses. Infinite rooms. Zero mixing.**
