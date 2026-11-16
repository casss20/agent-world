# PHASE 2: INTERFACE DESIGN
# AW_SYSTEM_WIDE_v2.0 — OOP Migration

**Date:** 2026-05-16  
**Status:** INTERFACE SPECIFICATIONS COMPLETE  
**Based on:** Phase 1 Reconnaissance findings

---

## 2.1 BACKEND CORE INTERFACES

### INTERFACE 1: BaseLLMProvider
**Location:** `core/interfaces/base_llm_provider.py`  
**Covers:** `agent_brain.py`, `design_providers.py`, `llm_provider.py`  
**Files Affected:** 3  
**Test Risk:** LOW (already partially abstracted in llm_provider.py)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional


class BaseLLMProvider(ABC):
    """
    Interface for all LLM providers.
    Swap providers by changing config — zero agent code changes needed.
    """

    def __init__(self):
        self.name: str = "undefined"
        self.model: str = "undefined"
        self.max_tokens: int = 4096
        self.temperature: float = 0.7

    @abstractmethod
    def initialize(self) -> bool:
        """Connect to LLM service. Return False if unavailable."""
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """Complete a conversation. Return the response text."""
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens as they arrive."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if LLM service is reachable and healthy."""
        pass

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
```

**Implementations:**
- `OpenAILLMProvider` — wraps existing OpenAI calls
- `AnthropicLLMProvider` — wraps existing Anthropic calls
- `OllamaLLMProvider` — free local models (new)
- `LiteLLMProvider` — wraps existing litellm calls

**Registry:** `core/providers/llm/llm_registry.py` — `get_llm_provider()` returns active provider based on `LLM_PROVIDER` env var.

---

### INTERFACE 2: BaseAgentBrain
**Location:** `core/interfaces/base_agent_brain.py`  
**Covers:** `agent_brain.py`  
**Files Affected:** 1 (+ 1 executor wrapper)  
**Test Risk:** MEDIUM (core agent logic — careful testing needed)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any


class BaseAgentBrain(ABC):
    """
    Interface for agent cognitive layer.
    Separates thinking/planning from execution.
    """

    @abstractmethod
    async def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process context and decide next action."""
        pass

    @abstractmethod
    async def plan(self, goal: str, constraints: List[str] = None) -> List[str]:
        """Break goal into ordered steps."""
        pass

    @abstractmethod
    async def reflect(self, result: Dict[str, Any]) -> str:
        """Evaluate result quality and generate reflection."""
        pass

    @abstractmethod
    async def decide(self, options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Choose best option from list."""
        pass

    @abstractmethod
    async def remember(self, key: str, value: Any) -> None:
        """Store to agent memory."""
        pass

    @abstractmethod
    async def recall(self, key: str) -> Any:
        """Retrieve from agent memory."""
        pass
```

**Implementations:**
- `LLMAgentBrain` — uses BaseLLMProvider for cognition
- `RuleBasedBrain` — deterministic logic for testing
- `HybridBrain` — LLM + rule fallback

---

### INTERFACE 3: BaseOrchestrator
**Location:** `core/interfaces/base_orchestrator.py`  
**Covers:** `orchestrator.py`, `services.py`, `services/orchestrator_service.py`  
**Files Affected:** 3  
**Test Risk:** MEDIUM (swarm logic — careful testing)

```python
from abc import ABC, abstractmethod
from typing import Dict, List


class BaseOrchestrator(ABC):
    """
    Interface for task orchestration and swarm management.
    """

    @abstractmethod
    async def decompose(self, task: str, context: Dict = None) -> List[Dict]:
        """Break complex task into parallel subtasks."""
        pass

    @abstractmethod
    async def spawn(self, subtasks: List[Dict], framework: str = "native") -> str:
        """Spawn agents for subtasks. Return execution ID."""
        pass

    @abstractmethod
    async def monitor(self, execution_id: str) -> Dict:
        """Get current status of execution."""
        pass

    @abstractmethod
    async def aggregate(self, execution_id: str) -> Dict:
        """Collect and combine all agent outputs."""
        pass

    @abstractmethod
    async def cancel(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        pass

    @abstractmethod
    async def get_metrics(self, execution_id: str) -> Dict:
        """Get performance metrics for execution."""
        pass
```

**Implementations:**
- `NativeOrchestrator` — wraps existing orchestrator.py
- `CrewAIOrchestrator` — wraps CrewAI framework
- `LangGraphOrchestrator` — wraps LangGraph framework

---

### INTERFACE 4: BaseGovernance
**Location:** `core/interfaces/base_governance.py`  
**Covers:** `governance_init.py`, `approval_queue.py`, `audit_guardrails.py`, `governance_v2/`  
**Files Affected:** 12 (all governance files)  
**Test Risk:** MEDIUM (governance touches many flows)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseGovernance(ABC):
    """
    Interface for governance, approval gates, and audit logging.
    """

    @abstractmethod
    async def approve(self, action: Dict) -> bool:
        """Approve or reject an action. Return True if approved."""
        pass

    @abstractmethod
    async def audit(self, event: Dict) -> str:
        """Log an event to the audit trail. Return event ID."""
        pass

    @abstractmethod
    async def validate(self, input: Dict) -> bool:
        """Validate input against guardrails."""
        pass

    @abstractmethod
    async def rollback(self, action_id: str) -> bool:
        """Rollback a previously approved action."""
        pass

    @abstractmethod
    async def get_audit_trail(self, entity_id: str) -> List[Dict]:
        """Return full audit trail for an entity."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if governance layer is operational."""
        pass
```

**Implementations:**
- `LedgerGovernance` — wraps existing ledger + governance_init
- `LocalGovernance` — in-memory for testing
- `AuditOnlyGovernance` — audit without approval gates

---

### INTERFACE 5: BaseLedger
**Location:** `core/interfaces/base_ledger.py`  
**Covers:** `ledger_client.py`, `ledger_sovereign.py`, `ledger_router.py`, `ledger_routes.py`  
**Files Affected:** 4  
**Test Risk:** LOW (ledger is already somewhat isolated)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseLedger(ABC):
    """
    Interface for financial ledger operations.
    """

    @abstractmethod
    async def record(self, transaction: Dict) -> str:
        """Record transaction. Return transaction ID."""
        pass

    @abstractmethod
    async def query(self, filters: Dict) -> List[Dict]:
        """Query transactions."""
        pass

    @abstractmethod
    async def approve(self, transaction_id: str, approver_id: str) -> bool:
        """Approve a pending transaction."""
        pass

    @abstractmethod
    async def reject(self, transaction_id: str, reason: str) -> bool:
        """Reject a pending transaction."""
        pass

    @abstractmethod
    async def audit_trail(self, entity_id: str) -> List[Dict]:
        """Full ledger history for an entity."""
        pass

    @abstractmethod
    async def balance(self, account_id: str) -> float:
        """Current balance for an account."""
        pass
```

**Implementations:**
- `PostgreSQLLedger` — wraps existing ledger_client.py
- `SQLiteLedger` — lightweight local testing
- `MockLedger` — in-memory for tests

---

### INTERFACE 6: BaseScout
**Location:** `core/interfaces/base_scout.py`  
**Covers:** `multi_source_scout.py`, `channel_registry.py`  
**Files Affected:** 2  
**Test Risk:** LOW (isolated from core)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum


class SourceType(str, Enum):
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    PRODUCTHUNT = "producthunt"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


class BaseScout(ABC):
    """
    Interface for trend discovery across multiple sources.
    """

    @abstractmethod
    async def scrape(self, source: SourceType, query: str, limit: int = 20) -> List[Dict]:
        """Scrape a source for trending content."""
        pass

    @abstractmethod
    async def schedule(self, query: str, interval: int, source: SourceType) -> str:
        """Schedule recurring scrape. Return job ID."""
        pass

    @abstractmethod
    async def get_results(self, job_id: str) -> List[Dict]:
        """Get results for a scheduled job."""
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled scrape."""
        pass

    @abstractmethod
    async def health_check(self, source: SourceType) -> bool:
        """Check if a source is reachable."""
        pass
```

**Implementations:**
- `MultiSourceScout` — wraps existing multi_source_scout.py
- `RedditScout`, `HNScout`, `PHScout`, `TwitterScout` — individual source adapters

---

### INTERFACE 7: BaseSelfHealing
**Location:** `core/interfaces/base_self_healing.py`  
**Covers:** `self_healing.py`, `retry_guardrails.py`, `retry_controller.py`  
**Files Affected:** 3  
**Test Risk:** LOW (resilience logic is additive)

```python
from abc import ABC, abstractmethod
from typing import Callable, Any, Dict


class BaseSelfHealing(ABC):
    """
    Interface for resilience: retry, circuit breaker, recovery.
    """

    @abstractmethod
    async def retry(self, fn: Callable, max_attempts: int = 3, backoff: float = 1.0) -> Any:
        """Execute fn with retry logic."""
        pass

    @abstractmethod
    async def circuit_break(self, fn: Callable, failure_threshold: int = 5) -> Any:
        """Execute fn with circuit breaker."""
        pass

    @abstractmethod
    async def recover(self, failure: Dict[str, Any]) -> bool:
        """Attempt to recover from a known failure pattern."""
        pass

    @abstractmethod
    def get_health(self) -> Dict[str, Any]:
        """Get current resilience health metrics."""
        pass
```

**Implementations:**
- `DefaultSelfHealing` — wraps existing retry_controller.py
- `AggressiveHealing` — lower thresholds for critical paths
- `PassiveHealing` — logging only, no auto-recovery

---

## 2.2 INFRASTRUCTURE INTERFACES

### INTERFACE 8: BaseStorageProvider
**Location:** `infrastructure/interfaces/base_storage_provider.py`  
**Covers:** ALL direct SQLAlchemy calls in 17+ files  
**Files Affected:** 17  
**Test Risk:** HIGH (touches everything — careful migration)

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable


class BaseStorageProvider(ABC):
    """
    Interface for all database storage.
    Swap DB by changing config — no service code changes.
    """

    @abstractmethod
    async def execute(self, query: str, params: Dict = None) -> Any:
        """Execute raw query."""
        pass

    @abstractmethod
    async def find_one(self, table: str, filters: Dict) -> Optional[Dict]:
        """Find single record."""
        pass

    @abstractmethod
    async def find_many(
        self,
        table: str,
        filters: Dict = None,
        order_by: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Find multiple records."""
        pass

    @abstractmethod
    async def insert(self, table: str, data: Dict) -> str:
        """Insert record, return ID."""
        pass

    @abstractmethod
    async def update(self, table: str, id: str, data: Dict) -> bool:
        """Update record."""
        pass

    @abstractmethod
    async def delete(self, table: str, id: str) -> bool:
        """Delete record."""
        pass

    @abstractmethod
    async def transaction(self, operations: List[Callable]) -> bool:
        """Execute operations in a transaction."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check database connectivity."""
        pass
```

**Implementations:**
- `PostgreSQLProvider` — wraps existing SQLAlchemy async engine
- `SQLiteProvider` — lightweight local testing
- `MockStorageProvider` — in-memory for unit tests

---

### INTERFACE 9: BaseCacheProvider
**Location:** `infrastructure/interfaces/base_cache_provider.py`  
**Covers:** `shared_state.py`, `realtime_streaming.py`, `hardened_mutations.py`, `workflow_adapter.py`, `revenue_metrics.py`  
**Files Affected:** 5  
**Test Risk:** LOW (cache is additive, not critical path)

```python
from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseCacheProvider(ABC):
    """
    Interface for caching layer.
    """

    @abstractmethod
    async def get(self, key: str) -> Any:
        """Get value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value with TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check cache connectivity."""
        pass
```

**Implementations:**
- `RedisCacheProvider` — wraps existing redis calls
- `MemoryCacheProvider` — in-memory dict for testing
- `NullCacheProvider` — no-op for when cache unavailable

---

### INTERFACE 10: BaseQueueProvider
**Location:** `infrastructure/interfaces/base_queue_provider.py`  
**Covers:** `background_worker.py`, `retry_controller.py`, `hardened_mutations.py`  
**Files Affected:** 3  
**Test Risk:** MEDIUM (queue affects task processing)

```python
from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseQueueProvider(ABC):
    """
    Interface for task queuing.
    """

    @abstractmethod
    async def enqueue(self, task: Dict, priority: int = 0, queue_name: str = "default") -> str:
        """Add task to queue. Return task ID."""
        pass

    @abstractmethod
    async def dequeue(self, queue_name: str = "default") -> Optional[Dict]:
        """Get next task from queue."""
        pass

    @abstractmethod
    async def acknowledge(self, task_id: str) -> bool:
        """Mark task as successfully processed."""
        pass

    @abstractmethod
    async def dead_letter(self, task_id: str, reason: str) -> bool:
        """Move failed task to dead letter queue."""
        pass

    @abstractmethod
    async def queue_depth(self, queue_name: str = "default") -> int:
        """Return number of pending tasks."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check queue connectivity."""
        pass
```

**Implementations:**
- `RedisQueueProvider` — wraps Redis for queuing
- `PostgresQueueProvider` — uses PostgreSQL for queuing
- `MemoryQueueProvider` — in-memory for testing

---

### INTERFACE 11: BaseAuthProvider
**Location:** `infrastructure/interfaces/base_auth_provider.py`  
**Covers:** `auth_middleware.py`, `security_middleware.py`, all authenticated routes  
**Files Affected:** 25+ (every route that uses Depends)  
**Test Risk:** HIGH (auth touches every endpoint — most careful testing)

```python
from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseAuthProvider(ABC):
    """
    Interface for authentication and authorization.
    """

    @abstractmethod
    async def verify_token(self, token: str) -> Optional[Dict]:
        """Verify token. Return claims dict or None if invalid."""
        pass

    @abstractmethod
    async def create_token(self, user_id: str, claims: Dict = None, ttl: int = 3600) -> str:
        """Create new token for user."""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Invalidate a token."""
        pass

    @abstractmethod
    async def refresh_token(self, token: str) -> Optional[str]:
        """Create new token from existing valid token."""
        pass

    @abstractmethod
    async def hash_password(self, password: str) -> str:
        """Hash a password for storage."""
        pass

    @abstractmethod
    async def verify_password(self, password: str, hash: str) -> bool:
        """Verify a password against its hash."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check auth service health."""
        pass
```

**Implementations:**
- `JWTEd25519Provider` — wraps existing JWT + bcrypt + passlib
- `OAuth2Provider` — future OAuth2/OIDC support
- `MockAuthProvider` — bypass auth for testing

---

### INTERFACE 12: BaseFileProvider
**Location:** `infrastructure/interfaces/base_file_provider.py`  
**Covers:** `file_routes.py`  
**Files Affected:** 1  
**Test Risk:** LOW (isolated)

```python
from abc import ABC, abstractmethod
from typing import Optional


class BaseFileProvider(ABC):
    """
    Interface for file storage.
    """

    @abstractmethod
    async def upload(self, file: bytes, path: str, mime_type: str = None) -> str:
        """Upload file. Return URL or path."""
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download file. Return bytes."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete file."""
        pass

    @abstractmethod
    async def get_url(self, path: str, expiry: int = None) -> str:
        """Get signed URL for file."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check storage connectivity."""
        pass
```

**Implementations:**
- `S3FileProvider` — wraps existing boto3 calls
- `CloudinaryFileProvider` — wraps existing cloudinary calls
- `LocalFileProvider` — local filesystem for testing
- `MemoryFileProvider` — in-memory for unit tests

---

### INTERFACE 13: BaseMessagingProvider
**Location:** `infrastructure/interfaces/base_messaging_provider.py`  
**Covers:** `websocket_manager.py`, `realtime_streaming.py`, `routes/agent_chat.py`, `routes/orchestrator.py`  
**Files Affected:** 4  
**Test Risk:** LOW (messaging is additive)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Callable


class BaseMessagingProvider(ABC):
    """
    Interface for real-time messaging.
    """

    @abstractmethod
    async def send(self, channel: str, message: Dict) -> bool:
        """Send message to a channel."""
        pass

    @abstractmethod
    async def broadcast(self, channels: List[str], message: Dict) -> bool:
        """Broadcast message to multiple channels."""
        pass

    @abstractmethod
    async def subscribe(self, channel: str, handler: Callable) -> str:
        """Subscribe to a channel. Return subscription ID."""
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a channel."""
        pass

    @abstractmethod
    async def get_channel_members(self, channel: str) -> List[str]:
        """Get list of subscribers in channel."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check messaging connectivity."""
        pass
```

**Implementations:**
- `WebSocketProvider` — wraps existing FastAPI WebSocket
- `SSEProvider` — Server-Sent Events alternative
- `RedisPubSubProvider` — Redis pub/sub backend

---

### INTERFACE 14: BaseHTTPClient
**Location:** `infrastructure/interfaces/base_http_client.py`  
**Covers:** `chatdev_client.py`, `camofox_client.py`, `channel_registry.py`, `tools/http_tool.py`, `n8n_webhook_adapter.py`, `multica_client.py`  
**Files Affected:** 6  
**Test Risk:** LOW (external adapters)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseHTTPClient(ABC):
    """
    Interface for HTTP client operations.
    Centralizes retry, timeout, auth header management.
    """

    @abstractmethod
    async def get(self, url: str, headers: Dict = None, params: Dict = None, timeout: int = 30) -> Dict:
        """HTTP GET."""
        pass

    @abstractmethod
    async def post(self, url: str, body: Any = None, headers: Dict = None, timeout: int = 30) -> Dict:
        """HTTP POST."""
        pass

    @abstractmethod
    async def put(self, url: str, body: Any = None, headers: Dict = None, timeout: int = 30) -> Dict:
        """HTTP PUT."""
        pass

    @abstractmethod
    async def delete(self, url: str, headers: Dict = None, timeout: int = 30) -> Dict:
        """HTTP DELETE."""
        pass

    @abstractmethod
    async def stream(self, url: str, headers: Dict = None) -> Any:
        """HTTP streaming response."""
        pass

    @abstractmethod
    async def health_check(self, url: str) -> bool:
        """Check if endpoint is reachable."""
        pass
```

**Implementations:**
- `HttpxClient` — wraps httpx
- `AiohttpClient` — wraps aiohttp
- `MockHTTPClient` — returns fake responses for testing

---

## 2.3 API GATEWAY INTERFACES

### INTERFACE 15: BaseRouter
**Location:** `api/interfaces/base_router.py`  
**Covers:** All 24 route files  
**Files Affected:** 24  
**Test Risk:** LOW (structural, no behavior change)

```python
from abc import ABC, abstractmethod
from fastapi import FastAPI, APIRouter
from typing import List


class BaseRouter(ABC):
    """
    Interface for all API route modules.
    Standardizes route registration across the system.
    """

    def __init__(self):
        self.router = APIRouter()

    @abstractmethod
    def get_prefix(self) -> str:
        """Return route prefix e.g. '/api/agents'"""
        pass

    @abstractmethod
    def get_tags(self) -> List[str]:
        """Return OpenAPI tags e.g. ['agents']"""
        pass

    @abstractmethod
    def register_routes(self) -> None:
        """Define all routes on self.router"""
        pass

    def mount(self, app: FastAPI) -> None:
        self.register_routes()
        app.include_router(
            self.router,
            prefix=self.get_prefix(),
            tags=self.get_tags()
        )
```

**Implementations:**
- Every existing route module refactored to extend BaseRouter
- New routes automatically follow pattern

---

### INTERFACE 16: BaseMiddleware
**Location:** `api/interfaces/base_middleware.py`  
**Covers:** `auth_middleware.py`, `security_middleware.py`, `security_headers.py`, `input_validation.py`  
**Files Affected:** 4  
**Test Risk:** MEDIUM (middleware runs on every request)

```python
from abc import ABC, abstractmethod
from fastapi import Request, Response
from typing import Callable


class BaseMiddleware(ABC):
    """
    Interface for all FastAPI middleware.
    """

    @abstractmethod
    async def process_request(self, request: Request) -> Request:
        """Process incoming request. Raise HTTPException to block."""
        pass

    @abstractmethod
    async def process_response(self, response: Response) -> Response:
        """Process outgoing response."""
        pass

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        request = await self.process_request(request)
        response = await call_next(request)
        response = await self.process_response(response)
        return response
```

**Implementations:**
- `AuthMiddleware` — wraps existing auth_middleware.py
- `SecurityHeadersMiddleware` — wraps existing security_headers.py
- `RateLimitMiddleware` — wraps existing rate_limiter.py
- `ValidationMiddleware` — wraps existing input_validation.py

---

## 2.4 DATABASE LAYER INTERFACES

### INTERFACE 17: BaseModel
**Location:** `database/interfaces/base_model.py`  
**Covers:** All SQLAlchemy models in `models.py`, `revenue_models.py`  
**Files Affected:** 2  
**Test Risk:** LOW (additive, doesn't break existing)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseModel(ABC):
    """
    Interface for all data models.
    Ensures consistent serialization/deserialization.
    """

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize model to dictionary."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """Deserialize model from dictionary."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate model fields. Return True if valid."""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.to_dict()}>"
```

---

### INTERFACE 18: BaseRepository
**Location:** `database/interfaces/base_repository.py`  
**Covers:** All direct DB query logic in services  
**Files Affected:** 6 service files  
**Test Risk:** MEDIUM (repository pattern requires service refactoring)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class BaseRepository(ABC):
    """
    Interface for all data repositories.
    Centralizes query logic, enables testing with mocks.
    """

    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    async def find_many(
        self,
        filters: Dict = None,
        order_by: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        pass

    @abstractmethod
    async def save(self, data: Dict) -> Dict:
        pass

    @abstractmethod
    async def update(self, id: str, data: Dict) -> Optional[Dict]:
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass

    @abstractmethod
    async def count(self, filters: Dict = None) -> int:
        pass
```

**Implementations:**
- `AgentRepository`, `TaskRepository`, `LedgerRepository`, `ConversationRepository`, `SwarmRepository`

---

## 2.5 FRONTEND INTERFACES

### INTERFACE 19: BaseComponent (React)
**Location:** `frontend-react/src/base/BaseComponent.jsx`  
**Covers:** All React components  
**Files Affected:** 35+ components  
**Test Risk:** LOW (frontend is additive)

```jsx
import React, { Component } from 'react';
import PropTypes from 'prop-types';

/**
 * BaseComponent — all React components extend this.
 * Provides: error boundary, loading state, empty state,
 * standard event handlers, and logging.
 */
class BaseComponent extends Component {
    constructor(props) {
        super(props);
        this.state = {
            loading: false,
            error: null,
            empty: false
        };
    }

    componentDidCatch(error, errorInfo) {
        console.error(`[${this.constructor.name}] Error:`, error, errorInfo);
        this.setState({ error: error.message });
    }

    setLoading(loading) { this.setState({ loading }); }
    setError(error) { this.setState({ error: error?.message || error }); }
    clearError() { this.setState({ error: null }); }

    renderLoading() { return <div className="loading">Loading...</div>; }
    renderError() {
        return (
            <div className="error">
                Error: {this.state.error}
                <button onClick={() => this.clearError()}>Dismiss</button>
            </div>
        );
    }
    renderEmpty() { return <div className="empty">No data available.</div>; }

    render() {
        if (this.state.loading) return this.renderLoading();
        if (this.state.error) return this.renderError();
        if (this.state.empty) return this.renderEmpty();
        return this.renderContent();
    }

    renderContent() {
        throw new Error(`${this.constructor.name} must implement renderContent()`);
    }
}

BaseComponent.propTypes = {
    className: PropTypes.string,
    style: PropTypes.object
};

export default BaseComponent;
```

---

### INTERFACE 20: BaseService (React)
**Location:** `frontend-react/src/services/BaseService.js`  
**Covers:** All API service modules  
**Files Affected:** All services  
**Test Risk:** LOW (frontend is additive)

```javascript
/**
 * BaseService — all API services extend this.
 * Provides: error handling, auth headers, loading states,
 * WebSocket management, retry logic.
 */
class BaseService {
    constructor(basePath) {
        this.basePath = basePath;
        this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    }

    getHeaders() {
        const token = localStorage.getItem('auth_token');
        return {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        };
    }

    async get(endpoint, params = {}) {
        const url = new URL(`${this.baseURL}${this.basePath}${endpoint}`);
        Object.keys(params).forEach(k => url.searchParams.append(k, params[k]));
        const response = await fetch(url.toString(), {
            method: 'GET',
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    async post(endpoint, body = {}) {
        const response = await fetch(
            `${this.baseURL}${this.basePath}${endpoint}`,
            { method: 'POST', headers: this.getHeaders(), body: JSON.stringify(body) }
        );
        return this.handleResponse(response);
    }

    async put(endpoint, body = {}) {
        const response = await fetch(
            `${this.baseURL}${this.basePath}${endpoint}`,
            { method: 'PUT', headers: this.getHeaders(), body: JSON.stringify(body) }
        );
        return this.handleResponse(response);
    }

    async delete(endpoint) {
        const response = await fetch(
            `${this.baseURL}${this.basePath}${endpoint}`,
            { method: 'DELETE', headers: this.getHeaders() }
        );
        return this.handleResponse(response);
    }

    handleResponse(response) {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    }
}

export default BaseService;
```

---

## 2.6 TEST LAYER INTERFACES

### INTERFACE 21: BaseTestCase
**Location:** `tests/base/base_test_case.py`  
**Covers:** All test files  
**Files Affected:** 30 test files  
**Test Risk:** LOW (test infrastructure)

```python
import pytest
from typing import Dict, Any


class BaseTestCase:
    """Base class for all tests. Provides common utilities."""

    def setup_method(self):
        """Run before each test."""
        pass

    def teardown_method(self):
        """Run after each test."""
        pass

    def assert_response_ok(self, response, expected_keys: list = None):
        assert response.status_code == 200
        if expected_keys:
            data = response.json()
            for key in expected_keys:
                assert key in data

    def assert_model_valid(self, model, expected: Dict[str, Any]):
        for key, value in expected.items():
            assert getattr(model, key) == value


class UnitTestCase(BaseTestCase):
    """No external dependencies. All mocked."""
    pass


class IntegrationTestCase(BaseTestCase):
    """Real database. External APIs mocked."""
    pass


class E2ETestCase(BaseTestCase):
    """Full stack — real DB + real APIs."""
    pass
```

---

### INTERFACE 22: BaseMock
**Location:** `tests/mocks/base_mock.py`  
**Covers:** All test mocks  
**Files Affected:** All tests  
**Test Risk:** LOW (test infrastructure)

```python
from abc import ABC, abstractmethod


class BaseMock(ABC):
    """Base class for all test mocks."""

    @abstractmethod
    def setup_mock(self) -> None:
        """Initialize mock state."""
        pass

    @abstractmethod
    def reset_mock(self) -> None:
        """Reset mock to initial state."""
        pass

    @abstractmethod
    def assert_called_with(self, *args, **kwargs) -> None:
        """Verify mock was called with expected args."""
        pass
```

**Implementations:**
- `LLMMock` — fake LLM responses
- `DatabaseMock` — in-memory DB
- `ProviderMock` — fake external APIs
- `AuthMock` — bypass auth in tests
- `CacheMock` — in-memory cache
- `QueueMock` — in-memory queue

---

## 2.7 PHASE 2 SUMMARY

```json
{
  "interfaces_designed": 22,
  "implementations_needed": 42,
  "files_to_modify": 86,
  "files_to_create": 64,
  "estimated_total_hours": 160,
  "risk_assessment": {
    "high_risk": [
      "BaseStorageProvider (17 files affected)",
      "BaseAuthProvider (25+ routes affected)",
      "BaseAgentBrain (core agent logic)"
    ],
    "medium_risk": [
      "BaseOrchestrator (swarm logic)",
      "BaseGovernance (approval flows)",
      "BaseQueueProvider (task processing)",
      "BaseRepository (service refactoring)"
    ],
    "low_risk": [
      "BaseLLMProvider (already partially done)",
      "BaseCacheProvider (additive)",
      "BaseFileProvider (isolated)",
      "BaseScout (isolated)",
      "BaseSelfHealing (additive)",
      "BaseMessagingProvider (additive)",
      "BaseHTTPClient (isolated)",
      "BaseRouter (structural)",
      "BaseMiddleware (structural)",
      "BaseModel (additive)",
      "BaseComponent (frontend)",
      "BaseService (frontend)",
      "BaseTestCase (test infra)",
      "BaseMock (test infra)"
    ]
  }
}
```

---

**Next: Phase 3 — Go/No-Go Decision**
