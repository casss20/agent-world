# n8n Integration Setup

## Quick Start

### 1. Start n8n (if not running)

```bash
# Docker
ocker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# Or use n8n cloud (recommended for production)
# https://n8n.io/cloud
```

### 2. Import Agent World Workflow

1. Open n8n UI (http://localhost:5678)
2. Click "Add Workflow"
3. Click menu (⋯) → Import from File
4. Select `n8n/agent-world-events-workflow.json`

### 3. Configure Credentials

In n8n:
- **Slack credential** → Connect your workspace
- **Google Sheets credential** → OAuth with Google
- **Agent World credential** → Add custom credential:
  - Name: `Agent World API`
  - Secret: Same as `N8N_WEBHOOK_SECRET` in Agent World

### 4. Get Webhook URL

1. Open the imported workflow
2. Click "Agent World Webhook" node
3. Copy the **Webhook URL** (e.g., `https://n8n.example.com/webhook/agent-world-events`)

### 5. Register Webhook in Agent World

```bash
# Register the n8n endpoint
curl -X POST http://localhost:8000/n8n/webhooks/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "n8n-production",
    "url": "https://n8n.example.com/webhook/agent-world-events",
    "events": ["sale_made", "campaign_scaled", "campaign_paused", "approval_needed"],
    "secret": "your-webhook-secret-here",
    "retry_count": 3
  }'
```

Or use environment variable:
```bash
export N8N_WEBHOOK_PRODUCTION="https://n8n.example.com/webhook/agent-world-events|sale_made,campaign_scaled,campaign_paused|your-secret"
```

### 6. Test the Integration

```bash
# Send test event
curl -X POST http://localhost:8000/n8n/webhooks/test-broadcast \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "sale_made",
    "payload": {
      "order_id": "test-123",
      "channel": "etsy",
      "revenue": 29.99,
      "product_name": "Test Digital Planner"
    }
  }'
```

You should see:
- Slack notification in #revenue-alerts
- New row in Google Sheets "Revenue Log"

## Available Events

| Event | Description | Payload Fields |
|-------|-------------|----------------|
| `sale_made` | Merchant agent made sale | `order_id`, `channel`, `revenue`, `campaign_id`, `product_name` |
| `campaign_scaled` | Promoter scaled budget | `campaign_id`, `campaign_name`, `roas`, `new_budget`, `platform` |
| `campaign_paused` | Promoter paused underperformer | `campaign_id`, `campaign_name`, `roas`, `reason`, `platform` |
| `approval_needed` | Ledger approval required | `approval_id`, `action_type`, `description`, `estimated_cost`, `business_id` |
| `task_completed` | Any agent finished task | `task_id`, `task_type`, `agent_name`, `room_id`, `result_summary` |
| `diagnosis_complete` | Business diagnosis done | `diagnosis_id`, `health_score`, `top_bottleneck`, `recommended_strategy` |
| `*` | Subscribe to all events | - |

## Inbound: n8n → Agent World

n8n can trigger Agent World via the `/n8n/events/{type}` endpoint:

### Scheduled Scout (n8n Cron → Agent World)

```javascript
// n8n HTTP Request node
{
  "method": "POST",
  "url": "https://agent-world.example.com/n8n/events/scheduled_scout",
  "body": {
    "subreddit": "entrepreneur",
    "keywords": ["side hustle", "passive income"],
    "room_id": "scout-room-123",
    "priority": 5
  }
}
```

### User Approval (Slack Button → Agent World)

```javascript
// When user clicks Approve/Reject in Slack
{
  "method": "POST",
  "url": "https://agent-world.example.com/n8n/events/user_action",
  "body": {
    "action": "approve",  // or "reject"
    "approval_id": "{{ $json.approval_id }}",
    "user_id": "{{ $json.user.id }}"
  }
}
```

## Security

### Webhook Signature Verification

Agent World signs all outbound webhooks with HMAC-SHA256:

```python
import hmac
import hashlib

def verify_signature(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### IP Allowlist (Production)

Restrict n8n webhooks to Agent World IP:
```nginx
# nginx.conf
location /webhook/agent-world-events {
    allow 1.2.3.4;  # Agent World IP
    deny all;
    proxy_pass http://n8n:5678;
}
```

## Troubleshooting

**Events not arriving:**
```bash
# Check registered endpoints
curl http://localhost:8000/n8n/webhooks

# Test specific endpoint
curl -X POST http://localhost:8000/n8n/webhooks/n8n-production/test \
  -d '{"event_type": "sale_made", "payload": {"test": true}}'
```

**Signature verification failing:**
- Ensure `secret` matches between Agent World registration and n8n credential
- Check that n8n is using raw body (not parsed JSON) for signature verification

**Events sent but no action in n8n:**
- Check n8n execution logs (Settings → Executions)
- Ensure workflow is activated (toggle in top-right)
- Check that event_type matches the switch conditions
