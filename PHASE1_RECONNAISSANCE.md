# PHASE 1: SYSTEM RECONNAISSANCE REPORT
# AW_SYSTEM_WIDE_v2.0 — OOP Migration

**Date:** 2026-05-16  
**Branch:** `enterprise-architecture`  
**Status:** RECONNAISSANCE COMPLETE  
**Tests:** 78/78 passing  
**Routes:** 207 operational

---

## 1.1 FULL CODEBASE INVENTORY

```
┌────────────────────────────────────────────────────────┐
│ LAYER              │ FILES  │ TESTS   │ STATUS         │
├────────────────────────────────────────────────────────┤
│ backend/*.py       │  182   │   —     │ Production     │
│ backend/tests/     │    6   │   78    │ Passing        │
│ test_* (legacy)    │   24   │   —     │ Disorganized   │
│ frontend-react/src │   49   │   —     │ Active         │
│ Config/docs        │   38   │   —     │ Documentation  │
│ TOTAL              │  299   │   78    │                │
└────────────────────────────────────────────────────────┘
```

### Backend Breakdown (182 Python files)

| Category | Files | Key Files |
|----------|-------|-----------|
| **Core Agents** | 5 | `agent_brain.py`, `agent_executor.py`, `agent_templates.py`, `auto_spawner.py`, `orchestrator.py` |
| **Enterprise (NEW)** | 26 | `plugins/`, `services/`, `agents/roles/`, `routes/` |
| **Governance** | 12 | `governance_init.py`, `approval_queue.py`, `audit_guardrails.py`, `governance_v2/` |
| **Ledger** | 4 | `ledger_client.py`, `ledger_sovereign.py`, `ledger_router.py`, `ledger_routes.py` |
| **Revenue** | 4 | `revenue_routes.py`, `revenue_metrics.py`, `revenue_models.py` |
| **Multi-Source** | 3 | `multi_source_scout.py`, `channel_registry.py`, `multica_client.py` |
| **Infrastructure** | 8 | `database.py`, `shared_state.py`, `websocket_manager.py`, `background_worker.py` |
| **Routes** | 24 | `main.py`, `spawn_routes.py`, `diagnostic_routes.py`, `routes/*.py` |
| **Tools** | 12 | `tools/http_tool.py`, `tools/email_tool.py`, `tools/stripe_tool.py`, `tools/github_tool.py` |
| **Adapters** | 8 | `chatdev_client.py`, `n8n_webhook_adapter.py`, `camofox_client.py`, `hybrid_adapter.py` |
| **Security** | 6 | `auth_middleware.py`, `security_middleware.py`, `security_headers.py`, `input_validation.py` |
| **Observability** | 6 | `metrics.py`, `telemetry.py`, `observability.py`, `logging_guardrails.py` |
| **Resilience** | 5 | `self_healing.py`, `retry_guardrails.py`, `retry_controller.py`, `hardened_mutations.py` |
| **Demos/Tests** | 38 | `demo_*.py`, `test_*.py`, `load_test_*.py` |
| **Models** | 4 | `models.py`, `models_workflow.py`, `revenue_models.py`, `business_models/` |
| **Business** | 5 | `business_config.py`, `growth_executor.py`, `merchant_executor.py`, `promoter_executor.py` |
| **Other** | 16 | `vector_memory.py`, `output_schema.py`, `lifecycle_manager.py`, `batched_audit_writer.py` |

### Frontend Breakdown (49 files)

| Category | Files |
|----------|-------|
| Components | 35+ in `components/` |
| Pages | 5 in `pages/` |
| Hooks | 3 in `hooks/` |
| Providers | 2 in `providers/` |
| Styles | `App.css`, `index.css`, `spawn.css` |
| Entry | `App.jsx`, `main.jsx` |

---

## 1.2 HARD-CODED DEPENDENCY AUDIT

### HIGH RISK — Direct External API Imports

| # | File | Dependency | Line | Type | Risk |
|---|------|-----------|------|------|------|
| 1 | `design_providers.py:108` | `import openai` | LLM | 🔴 HIGH |
| 2 | `llm_provider.py:59` | `from openai import AsyncOpenAI` | LLM | 🔴 HIGH |
| 3 | `llm_provider.py:69` | `import anthropic` | LLM | 🔴 HIGH |
| 4 | `llm_provider.py:196` | `import litellm` | LLM | 🔴 HIGH |
| 5 | `file_routes.py:9` | `import boto3` | Storage | 🔴 HIGH |
| 6 | `file_routes.py:16-18` | `cloudinary` | Storage | 🔴 HIGH |
| 7 | `auto_spawner.py:20` | `sqlalchemy.create_engine` | DB | 🟡 MED |
| 8 | `spawn_routes.py:19` | `sqlalchemy.create_engine` | DB | 🟡 MED |
| 9 | `revenue_routes.py:11` | `sqlalchemy.func` | DB | 🟡 MED |
| 10 | `shared_state.py:9` | `import redis` | Cache | 🟡 MED |
| 11 | `realtime_streaming.py:16` | `redis.asyncio` | Cache | 🟡 MED |
| 12 | `hardened_mutations.py:21` | `import redis` | Cache | 🟡 MED |
| 13 | `workflow_adapter.py:15` | `redis.asyncio` | Cache | 🟡 MED |
| 14 | `revenue_metrics.py:13` | `aioredis` | Cache | 🟡 MED |
| 15 | `auth_middleware.py:13` | `import jwt` | Auth | 🟡 MED |
| 16 | `auth_middleware.py:14` | `passlib.CryptContext` | Auth | 🟡 MED |
| 17 | `security_middleware.py:12` | `import bcrypt` | Auth | 🟡 MED |
| 18 | `security_middleware.py:212` | `import jwt` | Auth | 🟡 MED |
| 19 | `chatdev_client.py:8` | `import httpx` | HTTP | 🟢 LOW |
| 20 | `camofox_client.py:6` | `import httpx` | HTTP | 🟢 LOW |
| 21 | `channel_registry.py:33` | `import httpx` | HTTP | 🟢 LOW |
| 22 | `tools/http_tool.py:7` | `import httpx` | HTTP | 🟢 LOW |
| 23 | `multica_client.py:6` | `import httpx` | HTTP | 🟢 LOW |
| 24 | `design_providers.py:191` | `import aiohttp` | HTTP | 🟢 LOW |

### MEDIUM RISK — Direct SQLAlchemy in Service Layer

| File | Lines | Issue |
|------|-------|-------|
| `services/agent_chat_service.py` | 11-12 | Direct SQLAlchemy imports |
| `services/crm_revenue_service.py` | 16-17 | Direct SQLAlchemy imports |
| `services/room_service.py` | 14-16 | Direct SQLAlchemy + selectinload |
| `services/orchestrator_service.py` | 14-15 | Direct SQLAlchemy imports |
| `services/message_service.py` | 13-15 | Direct SQLAlchemy + selectinload |
| `services/task_service.py` | 14-15 | Direct SQLAlchemy imports |
| `services.py` | 4-5 | Direct SQLAlchemy imports |
| `ledger_client.py` | 153,202,226 | Direct model imports (lazy) |
| `background_worker.py` | 18,148 | Direct model + session imports |
| `lifecycle_manager.py` | 17 | Direct model imports |
| `retry_controller.py` | 16 | Direct model imports |
| `hardened_mutations.py` | 25 | Direct model imports |

### LOW RISK — Config Direct Access (acceptable with interfaces)

| File | Count | Pattern |
|------|-------|---------|
| `database.py` | 6 | `os.getenv("DATABASE_URL", ...)` |
| `security_middleware.py` | 5 | `os.getenv("JWT_SECRET", ...)` |
| `pooled_chatdev_client.py` | 2 | `os.getenv("CHATDEV_API_URL", ...)` |
| `hybrid_adapter.py` | 3 | `os.getenv("CHATDEV_API_URL", ...)` |
| `stateless_adapter.py` | 3 | `os.getenv("USE_REAL_CHATDEV", ...)` |

### Files Already Using Interfaces (Good Examples)

| File | Interface Pattern |
|------|-------------------|
| `plugins/base/base_provider.py` | `BaseProvider(ABC)` — ✅ Template |
| `business_models/base.py` | `BusinessModel(ABC)`, `DiagnosticCheck(ABC)` — ✅ Template |
| `channel_registry.py` | `ChannelAdapter(ABC)` — ✅ Template |
| `design_providers.py` | `DesignProvider(ABC)` — ✅ Template |

---

## 1.3 DEPENDENCY GRAPH

### Who Depends on What (Top-Level Imports)

```
┌─────────────────────────────────────────────────────────────┐
│  MODELS (SQLAlchemy)                                        │
│  ├── 17 files import from models.py directly                 │
│  ├── services/* (6 files)                                    │
│  ├── ledger_client.py                                        │
│  ├── background_worker.py                                    │
│  ├── lifecycle_manager.py                                    │
│  ├── retry_controller.py                                     │
│  ├── hardened_mutations.py                                   │
│  └── file_routes.py, setup_wizard_routes.py                │
├─────────────────────────────────────────────────────────────┤
│  SERVICES                                                     │
│  ├── services.py imports models, database                    │
│  ├── No service layer abstraction — direct DB access         │
│  └── 6 new services in services/ use pattern (good)         │
├─────────────────────────────────────────────────────────────┤
│  ROUTES                                                       │
│  ├── 24 route files import models, services directly          │
│  ├── No BaseRouter interface                                 │
│  └── Each route file defines its own APIRouter              │
├─────────────────────────────────────────────────────────────┤
│  AUTH                                                         │
│  ├── auth_middleware.py — hard-coded JWT + passlib           │
│  ├── security_middleware.py — hard-coded bcrypt + jwt         │
│  ├── No BaseAuthProvider interface                           │
│  └── auth.py — minimal, almost empty                        │
├─────────────────────────────────────────────────────────────┤
│  LLM                                                          │
│  ├── llm_provider.py — swappable internally (good)         │
│  ├── design_providers.py — direct openai import              │
│  └── agent_brain.py — no imports visible (runtime?)          │
├─────────────────────────────────────────────────────────────┤
│  CACHE/QUEUE                                                  │
│  ├── shared_state.py — hard-coded redis                     │
│  ├── realtime_streaming.py — hard-coded redis               │
│  ├── hardened_mutations.py — hard-coded redis              │
│  ├── workflow_adapter.py — hard-coded redis                │
│  ├── background_worker.py — hard-coded DB queue            │
│  └── No BaseCacheProvider / BaseQueueProvider               │
├─────────────────────────────────────────────────────────────┤
│  STORAGE                                                      │
│  ├── file_routes.py — direct boto3 + cloudinary             │
│  ├── No BaseFileProvider / BaseStorageProvider              │
│  └── Upload logic mixed with route handlers                  │
├─────────────────────────────────────────────────────────────┤
│  ADAPTERS                                                     │
│  ├── chatdev_client.py — direct httpx                     │
│  ├── camofox_client.py — direct httpx                     │
│  ├── channel_registry.py — direct httpx                     │
│  ├── n8n_webhook_adapter.py — direct httpx + sqlalchemy   │
│  └── No BaseHTTPClient / BaseAdapter interface              │
├─────────────────────────────────────────────────────────────┤
│  WEBSOCKET                                                    │
│  ├── main.py — FastAPI WebSocket                            │
│  ├── websocket_manager.py — FastAPI WebSocket               │
│  ├── spawn_routes.py — FastAPI WebSocket                    │
│  ├── realtime_streaming.py — FastAPI WebSocket              │
│  ├── routes/agent_chat.py — FastAPI WebSocket             │
│  ├── routes/orchestrator.py — FastAPI WebSocket           │
│  └── No BaseMessagingProvider interface                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 1.4 FILES WITH NO TESTS (Untested Core Files)

| Priority | File | Why It Needs Tests |
|----------|------|-------------------|
| 🔴 HIGH | `agent_brain.py` | Core agent thinking logic |
| 🔴 HIGH | `agent_executor.py` | Task execution engine |
| 🔴 HIGH | `auth_middleware.py` | Auth layer — critical security |
| 🔴 HIGH | `ledger_client.py` | Financial ledger |
| 🔴 HIGH | `websocket_manager.py` | Real-time messaging |
| 🟡 MED | `auto_spawner.py` | Agent lifecycle |
| 🟡 MED | `background_worker.py` | Background processing |
| 🟡 MED | `self_healing.py` | Resilience logic |
| 🟡 MED | `retry_controller.py` | Retry/circuit breaker |
| 🟡 MED | `file_routes.py` | File upload/download |
| 🟢 LOW | `camofox_client.py` | External scraping |
| 🟢 LOW | `chatdev_client.py` | External ChatDev bridge |
| 🟢 LOW | `business_config.py` | Static config |
| 🟢 LOW | `demo_*.py` | Demo scripts (no tests needed) |

### Files with Tests (Existing)

| File | Tests | Status |
|------|-------|--------|
| `tests/test_infrastructure.py` | 10 | Passing |
| `tests/test_advanced.py` | 10 | Passing |
| `tests/test_plugin_workflow.py` | 19 | Passing |
| `tests/test_plugin_system.py` | 20 | Passing |
| `tests/test_enterprise.py` | 19 | Passing |
| Legacy `test_*.py` (24 files) | Unknown | Disorganized |

---

## 1.5 SUMMARY

```json
{
  "total_files": {
    "backend": 182,
    "frontend": 49,
    "tests": 30,
    "total": 299
  },
  "hard_coded_dependencies": {
    "high": 6,
    "medium": 12,
    "low": 24
  },
  "files_with_no_tests": 45,
  "files_already_using_interfaces": 4,
  "estimated_total_interfaces_needed": 22
}
```

### Critical Findings

1. **LLM is already partially abstracted** — `llm_provider.py` has a swappable pattern internally, but `design_providers.py` bypasses it with direct `import openai`
2. **Database is NOT abstracted** — SQLAlchemy imports scattered across 17+ files in service layer, route layer, and core
3. **Auth is NOT abstracted** — JWT + bcrypt + passlib hard-coded in middleware
4. **Cache is NOT abstracted** — Redis imports in 6 files with no interface
5. **Storage is NOT abstracted** — S3 + Cloudinary hard-coded in file routes
6. **Queue is NOT abstracted** — Background worker uses DB directly for queuing
7. **HTTP client is NOT abstracted** — `httpx` imported in 12 files for different external APIs
8. **WebSocket is NOT abstracted** — FastAPI WebSocket imported in 7 files
9. **Only the plugin system (NEW) is fully abstracted** — `BaseProvider(ABC)` is the gold standard
10. **The enterprise services (NEW) are mostly clean** — `services/*.py` use dependency injection pattern

---

**Next: Phase 2 — Interface Design**
