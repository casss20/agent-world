# Agent World v2.0.0 🚀

**A business diagnosis and growth operating system powered by AI agents.**

Agent World identifies bottlenecks in growth, marketing, monetization, retention, or operations — then delivers tailored strategies and actionable next steps based on your business model, stage, and available resources.

[![GitHub](https://img.shields.io/badge/GitHub-casss20/agent--world-blue)](https://github.com/casss20/agent-world)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 What is Agent World?

Agent World answers three critical questions for any business:

1. **What is the business trying to achieve?**
2. **What is the main bottleneck right now?**
3. **What should be done next with current resources?**

**How it works:**
```
Business Context → Diagnostic Engine → Strategy Engine → Action Plan → Execution → Feedback Loop
```

**Key Capabilities:**
- 🔍 **Business Diagnosis**: Identify bottlenecks across acquisition, conversion, retention, monetization, and operations
- 🎯 **Strategy Engine**: Match constraints to highest-leverage interventions for your specific business model
- 🤖 **AI-Powered Planning**: Generate step-by-step action plans with measurable outcomes
- 📊 **KPI Tracking**: Monitor progress and validate strategy effectiveness
- 🛡️ **Governance Layer**: Human approval for high-impact decisions, full audit trail
- 🔌 **Multi-Platform**: Execute across Etsy, Shopify, TikTok, service businesses, and more
- ☁️ **Cloud Ready**: AWS/GCP/Azure deployment with auto-scaling

**Supported Business Models:**
- 🏪 **Etsy Print-on-Demand**: Listing quality, niche selection, CTR optimization, fulfillment
- 🛍️ **Shopify Brands**: Traffic quality, conversion rate, AOV, retention
- 📱 **TikTok Creators**: Audience growth, content consistency, monetization funnel
- 💼 **Service Businesses**: Lead flow, close rate, capacity planning, cash flow
- ⭐ **Personal Brands**: Audience trust, content engine, offer ladder, conversion path

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT WORLD v2 — DIAGNOSIS & GROWTH OS       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────┐   │
│  │   INTAKE    │────▶│  DIAGNOSTIC │────▶│    STRATEGY     │   │
│  │   (Wizard)  │     │    (Nova)   │     │    (Forge)      │   │
│  └─────────────┘     └─────────────┘     └─────────────────┘   │
│         │                   │                      │            │
│         ▼                   ▼                      ▼            │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────┐   │
│  │   Ledger    │     │  Bottleneck │     │  Action Plan    │   │
│  │   Shell     │◀────│   Analysis  │◀────│  Generation     │   │
│  │  (React)    │     │             │     │                 │   │
│  └─────────────┘     └─────────────┘     └─────────────────┘   │
│         │                                                      │
│         ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              EXECUTION LAYER (Channel Registry)          │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │  │
│  │  │  Etsy   │  │ Shopify │  │ TikTok  │  │   Generic   │ │  │
│  │  │   POD   │  │  Brand  │  │ Creator│  │   Webhook   │ │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────┘ │  │
│  └─────────────────────────────────────────────────────────┘  │
│         │                                                      │
│         ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              FEEDBACK LOOP & LEARNING                    │  │
│  │  Observe → Score → Review → Curate → Patch → Release    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Audit     │◀───│ PostgreSQL  │◀───│   Agent Templates   │ │
│  │   (Hash     │    │    +        │    │  (Nova/Forge/etc) │ │
│  │   Chain)    │    │   Redis     │    │                     │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
agent-world/
├── backend/                      # FastAPI backend
│   ├── main.py                   # Main FastAPI app
│   ├── agent_templates.py        # Pre-defined agent configurations (Nova/Forge/etc)
│   ├── channel_registry.py       # Platform adapters (Etsy, Shopify, etc)
│   ├── channel_routes.py         # Channel management API
│   ├── ledger_router.py          # Routes agent outputs to channels
│   ├── output_schema.py          # Standardized output types
│   ├── diagnostic_engine.py      # Bottleneck identification (NEW)
│   ├── strategy_engine.py        # Strategy recommendation (NEW)
│   ├── business_models/          # Business-specific logic (NEW)
│   │   ├── base.py               # Base business model class
│   │   ├── etsy_pod.py           # Etsy print-on-demand diagnostics
│   │   ├── shopify_brand.py      # Shopify brand diagnostics
│   │   ├── tiktok_account.py     # TikTok creator diagnostics
│   │   └── service_business.py   # Service business diagnostics
│   ├── governance_v2/            # Governance layer
│   │   ├── auth.py               # JWT + RBAC
│   │   ├── rate_limit.py         # Tiered rate limiting
│   │   ├── audit_models.py       # Immutable audit logs
│   │   └── routes.py             # 30+ API endpoints
│   ├── feedback_loop/            # Production improvement system
│   │   ├── tracing.py            # Trace collection
│   │   ├── eval_service.py       # Automated evaluation
│   │   ├── review_queue.py       # Human-in-the-loop
│   │   ├── dataset_builder.py    # Regression test generation
│   │   └── release_gate.py       # Quality thresholds
│   └── ... (80+ Python files)
│
├── frontend-react/               # Ledger Shell UI (React)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── BusinessIntakeWizard.jsx    # Onboarding flow (NEW)
│   │   │   ├── DiagnosticReport.jsx        # Bottleneck analysis (NEW)
│   │   │   ├── StrategyRecommendation.jsx    # Action plans (NEW)
│   │   │   ├── AgentTemplatesPage.jsx      # Spawn agents
│   │   │   └── ChannelsPage.jsx              # Connect platforms
│   │   ├── components/
│   │   │   ├── shell/            # CommandBar, ApprovalQueue
│   │   │   ├── audit/            # AuditLogViewer
│   │   │   └── governance/       # ApprovalGate
│   │   └── providers/            # LedgerProvider, etc.
│   └── ...
│
├── docs/                         # Architecture documentation
│   ├── FEEDBACK_LOOP.md          # Production improvement pipeline
│   ├── STRATEGIC_PIVOT.md        # Business diagnosis positioning
│   ├── SYSTEM_DESIGN_INTEGRATION.md
│   └── ...
│
├── k8s/                          # Kubernetes manifests
├── aws/                          # Terraform infrastructure
└── .github/workflows/            # CI/CD pipelines
```

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and enter
git clone https://github.com/casss20/agent-world.git
cd agent-world

# Configure
cp .env.prod.example .env.prod
# Edit .env.prod with your credentials

# Deploy
./scripts/deploy.sh docker
```

Services will be available at:
- API: http://localhost:8000
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

### Option 2: Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (React)
cd frontend-react
npm install
npm run dev

# Frontend (Vue)
cd frontend-vue
npm install
npm run dev
```

---

## 🧠 Core Workflow: Diagnose → Strategize → Execute → Learn

### 1. Intake (Gather Context)
User provides business information through wizard:
- **Business model**: Etsy POD, Shopify, TikTok, service business
- **Stage**: Ideation, traction, growth, optimization
- **Goals**: Revenue target, audience size, launch timeline
- **Resources**: Hours/week, budget, team size, skills
- **Current metrics**: Traffic, conversion, revenue (if available)

**Agent**: Ultron (orchestrator) collects and structures context

### 2. Diagnosis (Identify Bottlenecks)
Nova analyzes the business context and identifies constraints:
- **Etsy POD**: Listing quality, niche saturation, CTR, conversion, fulfillment
- **Shopify**: Traffic quality, conversion rate, AOV, retention, unit economics
- **TikTok**: Content consistency, engagement quality, audience growth, monetization
- **Service**: Lead flow, close rate, capacity, cash flow

**Output**: Ranked bottlenecks with severity and estimated impact

### 3. Strategy (Recommend Interventions)
Forge matches bottlenecks to best interventions given resources:
- Filters by time/budget/skill constraints
- Scores by expected impact / effort ratio
- Builds prioritized action plan

**Output**: Strategy recommendation with expected outcomes and measurement plan

### 4. Execution (Take Action)
Approved actions are executed through Channel Registry:
- **Etsy**: Create optimized listings, adjust pricing, update tags
- **Shopify**: Landing page tests, email campaigns, ad optimization
- **TikTok**: Content calendar, trend jacking, collaboration outreach
- **Service**: Lead gen content, proposal templates, capacity planning

**Human approval required for**: Publishing, pricing changes, customer communications

### 5. Feedback Loop (Validate & Improve)
System learns from outcomes:
- **Observe**: Track execution results, KPI changes
- **Score**: Automated evaluation of strategy effectiveness
- **Review**: Human review of ambiguous results
- **Curate**: Build dataset of successful vs failed strategies
- **Patch**: Update diagnostic logic and strategy recommendations
- **Release**: Deploy improved models with quality gates

---

## 🤖 Agent Templates

Pre-configured agents for business diagnosis and growth:

| Agent | Role | Autonomous Actions | Approval Required |
|-------|------|-------------------|-------------------|
| **Nova** | Diagnostic Engine | Research, data analysis, bottleneck identification | None (read-only) |
| **Forge** | Strategy & Planning | Build action plans, create checklists, generate copy | Publishing, pricing changes |
| **Pixel** | Creative Assets | Generate designs, thumbnails, visualizations | Final asset approval |
| **Cipher** | Communications | Inbox classification, draft replies | Sending messages |
| **Ultron** | Orchestrator | Route tasks, track state, escalate blockers | Bulk actions, cross-platform changes |

---

## 🔐 Security Features

### RBAC (Role-Based Access Control)

| Role | Permissions |
|------|-------------|
| `viewer` | Read logs, stats, health |
| `operator` | Register agents, submit tasks |
| `governor` | Execute actions, issue tokens |
| `admin` | Kill switches, degradation, exports |

### Rate Limiting (Tiered)

| Tier | Endpoints | Limit | Scope |
|------|-----------|-------|-------|
| Tier 1 | /execute, /token | 3/min | Per identity |
| Tier 2 | /agents/register | 5/min | Per IP |
| Tier 3 | Read endpoints | 60/min | Per IP |

### Immutable Audit Logs

- **Hash chaining**: SHA-256 chain for tamper detection
- **Database roles**: `audit_writer` (insert), `audit_reader` (select)
- **Integrity verification**: `/governance/v2/audit/integrity`
- **Retention**: 90 days hot, archive to cold storage

---

## 📊 API Endpoints

### Diagnostics & Strategy

```
POST /diagnostics/run                    # Run business diagnosis
GET  /diagnostics/{id}                   # Get diagnosis results
GET  /diagnostics/{id}/bottlenecks       # List identified bottlenecks

POST /strategy/generate                  # Generate strategy from diagnosis
GET  /strategy/{id}                      # Get strategy recommendation
POST /strategy/{id}/approve              # Approve strategy for execution

POST /business/intake                    # Submit business context
GET  /business/{id}/context              # Get stored context
```

### Agent Management

```
GET  /agents/templates                  # List agent templates
POST /agents/spawn                      # Spawn agent from template
GET  /agents/{id}/status                # Check agent status
POST /agents/{id}/tasks                 # Assign task to agent
```

### Channel Integration

```
GET  /channels                          # List connected channels
POST /channels/connect                  # Connect new channel
POST /channels/{id}/test              # Test connection
POST /channels/{id}/execute           # Execute approved action
```

### Governance v2

```
GET  /governance/v2/health/live      # Liveness probe
GET  /governance/v2/health/ready     # Readiness probe
GET  /governance/v2/health/deep      # Full status

POST /governance/v2/agents/register  # Register agent
POST /governance/v2/execute          # Execute action
GET  /governance/v2/audit/logs       # Query audit logs
GET  /governance/v2/audit/integrity  # Verify hash chain

POST /governance/v2/auth/login       # Get JWT token
```

### ChatDev Workflows

```
GET  /chatdev/workflows              # List workflows
GET  /chatdev/workflows/{id}         # Get workflow
POST /chatdev/workflows/{id}/run     # Run workflow
GET  /chatdev/workflows/{id}/status  # Check status
```

---

## ☁️ Cloud Deployment

### AWS (Terraform)

```bash
cd aws
terraform init
terraform apply
```

Creates:
- VPC with 3 AZs
- ECS Fargate (auto-scaling 2-10)
- RDS PostgreSQL Multi-AZ
- ElastiCache Redis
- Application Load Balancer

### GCP / Azure

```bash
./scripts/deploy.sh gcp
./scripts/deploy.sh azure
```

---

## 📈 Monitoring

### Health Checks

```bash
curl http://localhost:8000/governance/v2/health/live
curl http://localhost:8000/governance/v2/health/ready
curl http://localhost:8000/governance/v2/health/deep
```

### Prometheus Metrics

- Request rate, latency, errors
- Rate limit hits
- Authentication failures
- Agent registration count

### Grafana Dashboards

- System health
- Audit log statistics
- Revenue tracking
- Agent activity

---

## 🎯 Revenue Model

**Target:** $10,000/month

| Metric | Value |
|--------|-------|
| Monthly Revenue | $10,000 |
| Content Pieces/Month | 500 |
| Avg Revenue/Post | $20 |
| Scout Sources | 4 (Reddit, HN, PH, Twitter) |

**Infrastructure Cost:** ~$555/month (base), ~$2,200 (at scale)  
**Margin:** ~78% at target revenue

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |
| [RELEASE_v2.0.0.md](RELEASE_v2.0.0.md) | Release notes |
| [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) | Deployment guide |
| [PRODUCTION_READINESS_PLAN.md](PRODUCTION_READINESS_PLAN.md) | Security checklist |
| [LEDGER_INTEGRATION_ARCHITECTURE.md](LEDGER_INTEGRATION_ARCHITECTURE.md) | Governance design |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11 |
| Frontend (Governance) | React, Vite, Tailwind CSS |
| Frontend (Workflows) | Vue.js, VueFlow |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Auth | JWT, RBAC |
| Deployment | Docker, AWS ECS, Kubernetes |
| Monitoring | Prometheus, Grafana |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [ChatDev](https://github.com/OpenBMB/ChatDev) - Workflow engine
- [Camofox](https://github.com/jo-inc/camofox-browser) - Stealth browser
- [FastAPI](https://fastapi.tiangolo.com) - Web framework
- [VueFlow](https://vueflow.dev) - Workflow visualization

---

**Built with ❤️ by KC (Kimi Claw) for Anthony**  
**Mission: Build the definitive business diagnosis and growth operating system**
