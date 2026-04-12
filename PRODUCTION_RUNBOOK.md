

---

## Phase 4: Feature Expansion

### Camofox Browser Integration

**Purpose:** Anti-detection browser for agent web tasks

**Services:**
- `camofox` — Browser server on port 9377
- `nginx` — Routes /camofox/* to camofox

**Environment Variables:**
```bash
PROXY_HOST=
PROXY_PORT=
PROXY_USERNAME=
PROXY_PASSWORD=
CAMOFOX_API_KEY=
```

**Usage:**
```python
from camofox_client import CamofoxClient

client = CamofoxClient(base_url="http://localhost:9377")
tab = await client.create_tab(user_id="agent1", url="https://reddit.com")
snapshot = await client.get_snapshot(tab.id, user_id="agent1")
```

### Multica Integration

**Purpose:** Agent team orchestration (task delegation, Kanban)

**Services:**
- `multica-postgres` — Task database on port 5433
- `multica` — API server on port 8081
- `nginx` — Routes /multica/* to multica

**Environment Variables:**
```bash
MULTICA_POSTGRES_USER=multica
MULTICA_POSTGRES_PASSWORD=
MULTICA_JWT_SECRET=
```

**Usage:**
```python
from multica_client import MulticaClient

client = MulticaClient(base_url="http://localhost:8081")
issue = await client.create_issue(
    title="Create content",
    assignee_id=agent_id
)
```

### Testing

```bash
# Phase 4 integration tests
python3 backend/test_phase4_integration.py
```

