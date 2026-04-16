# Agent World + n8n Integration Architecture

## Overview

Agent World and n8n serve **complementary but different** purposes:

| Aspect | Agent World | n8n |
|--------|-------------|-----|
| **Primary Role** | Multi-agent orchestration with governance | General workflow automation |
| **Intelligence** | LLM-powered agents with reasoning | Rule-based node chains |
| **Governance** | Built-in approvals, audit, Ledger | Manual oversight, basic logging |
| **Use Case** | Complex business decisions, content creation | Data sync, notifications, ETL |
| **Scale** | Horizontal worker autoscaling (KEDA) | Single-node or queue-based |

## Integration Patterns

### Pattern 1: n8n as Trigger (Inbound)

```
n8n Workflow → Agent World API → Agent Execution
```

**Use Case:** Schedule-based or event-triggered agent runs

**Implementation:**
```javascript
// n8n HTTP Request node
{
  "method": "POST",
  "url": "https://agent-world.example.com/api/v1/rooms/{room_id}/tasks",
  "body": {
    "task_type": "scout_reddit",
    "payload": {
      "subreddit": "entrepreneur",
      "keywords": ["side hustle", "passive income"]
    }
  },
  "headers": {
    "Authorization": "Bearer {{$credentials.agentWorldApiKey}}"
  }
}
```

**When to Use:**
- Cron-based trend scouting (hourly/daily)
- Trigger agent from external events (new row in Airtable, email received)
- Low-code team members building triggers without coding

---

### Pattern 2: Agent World → n8n Webhook (Outbound)

```
Agent World Event → n8n Webhook → External Actions
```

**Use Case:** Agent decisions trigger non-agent workflows

**Implementation:**
```python
# In Agent World: promoter_executor.py
async def on_campaign_scaled(campaign):
    # n8n webhook for Slack notification + spreadsheet log
    await webhook_client.send("https://n8n.example.com/webhook/campaign-scaled", {
        "campaign_id": campaign.id,
        "roas": campaign.roas,
        "action": "scaled",
        "timestamp": datetime.utcnow().isoformat()
    })
```

**When to Use:**
- Send Slack/Discord notifications (n8n has better formatting options)
- Log to Google Sheets/Airtable (no-code friendly)
- Trigger Zapier-style integrations (5000+ apps)

---

### Pattern 3: Shared Task Queue (Hybrid)

```
Agent World                    n8n
   │                             │
   ├─ Complex: LLM reasoning ────┤ (skip, Agent World handles)
   │                             │
   ├─ Simple: API calls ─────────┤→ n8n nodes handle
   │                             │
   └─ Data sync ────────────────┤→ n8n nodes handle
```

**Architecture:**
- **Agent World handles:** LLM reasoning, multi-agent collaboration, approvals, audit
- **n8n handles:** Data transformation, API integrations, notifications, file operations

**Implementation via Redis Streams:**
```javascript
// n8n custom node polling Redis
{
  "redis_node": {
    "stream": "n8n-tasks",
    "consumer_group": "n8n-workers",
    "action": {
      "type": "http_request",
      "url": "{{ $json.target_url }}"
    }
  }
}
```

---

### Pattern 4: n8n as Fallback Handler

```
Agent World Task Failure → Dead Letter Queue → n8n Recovery Workflow
```

**Use Case:** Graceful degradation when agents fail

**Implementation:**
```python
# retry_controller.py
async def move_to_dlq(task):
    # Primary: Retry with exponential backoff
    if task.retry_count < 3:
        await reschedule(task)
    else:
        # Fallback: Send to n8n for human review
        await n8n_client.trigger("workflow/dlq-human-review", {
            "task_id": task.id,
            "payload": task.payload,
            "error": task.error_message,
            "suggested_action": "manual_fix_or_escalate"
        })
```

---

## Specific Integration Points

### 1. Revenue Tracking Sync

**n8n fetches from Agent World:**
```javascript
// n8n workflow: Hourly revenue sync
{
  "nodes": [
    {
      "type": "schedule",
      "interval": "1 hour"
    },
    {
      "type": "http_request",
      "url": "https://agent-world.example.com/revenue/summary?period=today",
      "method": "GET"
    },
    {
      "type": "google_sheets",
      "operation": "append",
      "sheet": "Daily P&L"
    },
    {
      "type": "slack",
      "channel": "#revenue-alerts",
      "condition": "{{ $json.roas < 1.0 }}"
    }
  ]
}
```

### 2. Content Publishing Pipeline

**Agent World → n8n → Multiple Channels:**
```
Pixel (Design) → Forge (Create) → n8n (Distribute)
                                      ├── Etsy listing
                                      ├── Shopify product
                                      ├── Email campaign
                                      └── Social media posts
```

**Why n8n here:** Better node library for specific platforms (Shopify, WooCommerce).

### 3. Approval Workflow Enhancement

**Agent World decision → n8n enrichment → Human approval:**
```javascript
// n8n workflow: Approval request
{
  "trigger": "webhook",
  "nodes": [
    {
      "type": "function",
      "code": "// Fetch additional context from external APIs"
    },
    {
      "type": "slack",
      "message": "🤖 Agent requests approval:\n{{ $json.proposal }}\n\n[Approve] [Reject] [Modify]"
    },
    {
      "type": "wait",
      "for": "button_click"
    },
    {
      "type": "http_request",
      "url": "https://agent-world.example.com/ledger/approvals/{{ $json.approval_id }}/resolve",
      "method": "POST",
      "body": {
        "decision": "{{ $json.button_value }}"
      }
    }
  ]
}
```

---

## Decision Matrix: Agent World vs n8n

| Task | Use Agent World | Use n8n |
|------|-----------------|---------|
| LLM content generation | ✅ Native | ❌ No reasoning |
| Multi-agent collaboration | ✅ Designed for this | ❌ No agent concept |
| Approval with audit trail | ✅ Ledger built-in | ⚠️ Manual logging |
| Scheduled API polling | ✅ Can do | ✅ Better at this |
| 50+ app integrations | ⚠️ Need custom adapters | ✅ 5000+ nodes |
| Complex conditional logic | ✅ Python code | ✅ Visual builder |
| Cost tracking per decision | ✅ Agent runtime | ❌ No granular cost |
| Failover/recovery | ✅ DLQ, retry logic | ⚠️ Basic retry |
| Non-technical users | ⚠️ JSON/YAML config | ✅ Drag-and-drop |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│  (React Dashboard — BusinessWorkspace, SetupWizard, etc)    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    AGENT WORLD API                          │
│  • Diagnostics (bottleneck detection)                       │
│  • Strategy generation                                      │
│  • Agent orchestration (LangGraph/CrewAI)                   │
│  • Ledger governance (approvals, audit)                     │
│  • Revenue tracking (ROAS calculation)                      │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │   Agent     │ │   Agent     │ │   Agent     │
    │   Workers   │ │   Runtime   │ │   Memory    │
    │  (Redis)    │ │ (LangGraph) │ │ (Ledger)    │
    └─────────────┘ └─────────────┘ └─────────────┘
                            │
                            ▼ (Webhooks for non-critical flows)
┌─────────────────────────────────────────────────────────────┐
│                      n8n WORKFLOWS                          │
│  • Data sync to Google Sheets/Airtable                      │
│  • Slack/Discord notifications                             │
│  • File operations (Google Drive, Dropbox)                │
│  • Email sequences (Mailchimp, ConvertKit)                │
│  • CRM updates (HubSpot, Salesforce)                        │
│  • Backup/archival workflows                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Priority

### Phase 1: Outbound Webhooks (Week 1)
Agent World → n8n for notifications
```python
# Add to config: webhook_endpoints = ["n8n", "internal"]
# Events: sale_made, campaign_scaled, approval_needed
```

### Phase 2: Inbound Triggers (Week 2)
n8n → Agent World for scheduled tasks
```javascript
// n8n node: "Agent World Trigger"
// Input: task_type, payload
// Output: task_id, status
```

### Phase 3: Shared Queue (Week 3-4)
Redis Streams bridge for bidirectional task passing

---

## Code Example: n8n-Compatible Webhook

```python
# backend/n8n_webhook_adapter.py
from fastapi import APIRouter, Request
from typing import Dict, Any

router = APIRouter(prefix="/n8n", tags=["n8n"])

@router.post("/events/{event_type}")
async def n8n_event_handler(event_type: str, request: Request):
    """
    Receive events from n8n and route to Agent World
    """
    payload = await request.json()
    
    handlers = {
        "scheduled_scout": handle_scheduled_scout,
        "external_approval": handle_external_approval,
        "data_sync_complete": handle_data_sync,
    }
    
    handler = handlers.get(event_type)
    if handler:
        return await handler(payload)
    
    return {"error": "Unknown event type"}

async def handle_scheduled_scout(payload: Dict):
    """Trigger Nova agent from n8n schedule"""
    from agent_runtime import enqueue_task
    
    task = await enqueue_task(
        task_type="scout_reddit",
        payload=payload,
        room_id=payload.get("room_id"),
        priority=5
    )
    
    return {"task_id": task.id, "status": "queued"}
```

---

## Summary

**Agent World** = Brain (reasoning, agents, governance)
**n8n** = Hands (integrations, notifications, data movement)

Use Agent World for anything requiring **judgment, creativity, or audit**. Use n8n for anything requiring **connecting to 3rd-party apps** or **non-technical user customization**.

The webhook bridge lets them work as a cohesive system: Agent World makes decisions, n8n executes the logistics.
