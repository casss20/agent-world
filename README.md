# Agent World v2.0.0 🚀

**A production-ready multi-agent "money room" platform for automated content arbitrage.**

Built with FastAPI, React, Vue.js, and integrated with ChatDev Money for workflow orchestration.

[![GitHub](https://img.shields.io/badge/GitHub-casss20/agent--world-blue)](https://github.com/casss20/agent-world)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 What is Agent World?

Agent World is a **governed multi-agent platform** that automates content arbitrage:

```
Reddit/HN/PH/Twitter → Scout Agent → Maker Agent → Merchant Agent → Revenue
```

**Key Capabilities:**
- 🔍 **Trend Discovery**: Multi-source scouting (Reddit, Hacker News, Product Hunt, Twitter)
- 🤖 **AI Content Creation**: Automated content generation with human oversight
- 📊 **Revenue Tracking**: End-to-end monetization pipeline
- 🛡️ **Governance Layer**: RBAC, rate limiting, immutable audit logs
- ☁️ **Cloud Ready**: AWS/GCP/Azure deployment with auto-scaling

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT WORLD v2                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Ledger    │───▶│ Governance  │───▶│   Agents    │         │
│  │   Shell     │    │     v2      │    │  (Scout/    │         │
│  │  (React)    │    │  (FastAPI)  │    │ Maker/etc)  │         │
│  └─────────────┘    └──────┬──────┘    └─────────────┘         │
│                            │                                    │
│  ┌─────────────┐    ┌─────┴──────┐    ┌─────────────┐         │
│  │   Audit     │◀───│ PostgreSQL │───▶│   ChatDev   │         │
│  │   (Hash     │    │    +       │    │   Money     │         │
│  │   Chain)    │    │   Redis    │    │  (Workflow) │         │
│  └─────────────┘    └────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
agent-world/
├── backend/                      # FastAPI backend
│   ├── main.py                   # Main FastAPI app
│   ├── main_v2.py                # Enhanced v2 app
│   ├── ledger_sovereign.py       # Governance engine
│   ├── chatdev_client.py         # ChatDev integration
│   ├── camofox_client.py         # Stealth browser client
│   ├── multica_client.py         # Multica integration
│   ├── governance_v2/            # Governance layer
│   │   ├── auth.py               # JWT + RBAC
│   │   ├── rate_limit.py         # Tiered rate limiting
│   │   ├── health.py             # K8s health probes
│   │   ├── audit_models.py       # Immutable audit logs
│   │   ├── audit_service.py      # Audit database service
│   │   ├── audit_routes.py       # Audit API endpoints
│   │   ├── phase1_core.py        # Capability issuer
│   │   ├── phase2_orchestration.py # Agent registry
│   │   ├── phase3_memory.py      # Event stream
│   │   ├── phase4_hardening.py   # Sandboxed executor
│   │   └── routes.py             # 30+ API endpoints
│   └── ... (65 Python files)
│
├── frontend-react/               # Ledger Shell UI (React)
│   ├── src/
│   │   ├── components/
│   │   │   ├── shell/            # CommandBar, ApprovalQueue
│   │   │   ├── audit/            # AuditLogViewer
│   │   │   └── governance/       # ApprovalGate
│   │   └── providers/            # LedgerProvider, etc.
│   └── ...
│
├── frontend-vue/                 # ChatDev Canvas (Vue.js)
│   ├── pages/                    # Workflow views
│   ├── components/               # VueFlow nodes
│   └── public/sprites/           # 144 agent avatars
│
├── aws/                          # Terraform infrastructure
│   ├── main.tf                   # ECS, RDS, ElastiCache
│   └── ecs-task-definition.json
│
├── k8s/                          # Kubernetes manifests
│   └── deployment.yaml
│
├── nginx/                        # Reverse proxy
│   └── nginx.conf
│
├── scripts/                      # Deployment scripts
│   └── deploy.sh
│
├── docker-compose.prod.yml       # Production Docker stack
├── backend/Dockerfile            # Container build
└── .github/workflows/            # CI/CD pipelines
    └── build-and-deploy.yml
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
**Mission: $10,000/month automated content arbitrage**
