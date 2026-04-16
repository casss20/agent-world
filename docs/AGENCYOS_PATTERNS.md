# Directus AgencyOS Patterns for Agent World

## What Directus AgencyOS Is

A **complete agency operating system** built on:
- **Nuxt 3** (frontend + client portal)
- **Directus** (backend CMS + database + APIs)

Not just AI agents — it's the **operational infrastructure** that makes an agency run.

---

## Core Operational Components (Patterns to Pull)

### 1. CRM / Project Tracker

**What AgencyOS Includes:**
- Organizations and contacts
- Sales pipeline and activities
- Dynamic project proposal builder
- Project and task management
- Customizable project templates
- Invoicing and expense tracking
- Dashboards without code
- Directus Flows for automation

**Agent World Equivalent:**

| AgencyOS | Agent World |
|----------|-------------|
| Organizations | **Business** (tenant-scoped) |
| Contacts | **Stakeholders** (user roles) |
| Sales pipeline | **Strategy pipeline** (intake → diagnosis → strategy → execution) |
| Proposals | **Strategy recommendations** (deliverable with steps, cost, impact) |
| Projects | **Agent rooms** (collaborative workspaces) |
| Tasks | **Task queue** (with retry, DLQ, approval gates) |
| Invoicing | **Revenue tracking** (sales, ad spend, ROAS) |
| Expense tracking | **Budget snapshots** (daily/monthly spend) |
| Dashboards | **GlobalHQ + BusinessWorkspace** (role-based views) |
| Directus Flows | **n8n integration + Ledger governance** (automated workflows) |

**Implementation Status:**
- ✅ Business model (tenant isolation)
- ✅ Task queue with retry/DLQ
- ✅ Revenue tracking (hybrid approach)
- ✅ Budget snapshots (daily/monthly)
- ✅ GlobalHQ + BusinessWorkspace views
- ✅ n8n integration for automation
- ⚠️ Proposal builder (StrategyRecommendation UI needs polish)
- ⚠️ Stakeholder management (basic RBAC, needs expansion)

---

### 2. Client Portal

**What AgencyOS Includes:**
- Private authenticated portal
- Clients view projects, tasks, files
- Clients pay invoices through Stripe
- Assign tasks to clients (part of templates)

**Agent World Equivalent:**

| AgencyOS | Agent World |
|----------|-------------|
| Client portal | **BusinessWorkspace** (authenticated, scoped) |
| View projects | **Room view** (see active agents, tasks, progress) |
| View tasks | **Task board** (pending, in-progress, completed) |
| View files | **Asset library** (designs, content, exports) |
| Pay invoices | **Revenue dashboard** (view earnings, connect Stripe) |
| Assign tasks | **Approval queue** (human tasks with context) |

**Implementation Status:**
- ✅ BusinessWorkspace (React UI)
- ✅ Room view with agent activity
- ✅ Task status tracking
- ✅ Approval queue with context
- ⚠️ Asset library (basic, needs design file management)
- ⚠️ Stripe Connect (revenue tracking shows data, not integrated payments)

---

### 3. Template System

**What AgencyOS Includes:**
- Project templates (reusable starting points)
- Customizable without rebuilding
- Apply template → customize → execute

**Agent World Equivalent:**

| AgencyOS | Agent World |
|----------|-------------|
| Project templates | **Business model templates** (TikTok, YouTube, Etsy, etc.) |
| Reusable | **Diagnostic checks + strategies** (per model, per stage) |
| Customizable | **BusinessContext** (adapts to your specific metrics) |
| Apply template | **Select model → run diagnosis → get strategy** |

**Implementation Status:**
- ✅ 3 business model templates (TikTok, YouTube, Etsy)
- ✅ Diagnostic check framework (extensible)
- ✅ Strategy generation per model
- ⚠️ More models needed (Shopify, Services, Digital Products)

**Pattern to Enhance:**
```python
# Current: Static model definition
class TikTokUGCModel(BusinessModel):
    checks = [ContentQualityCheck, NicheSaturationCheck, ...]

# Enhanced: Template with parameters
class TikTokUGCModel(BusinessModel):
    base_checks = [...]
    
    def customize_for_stage(self, stage: BusinessStage):
        if stage == "startup":
            return base_checks + [FollowerGrowthCheck]
        elif stage == "growth":
            return base_checks + [MonetizationCheck]
        elif stage == "scale":
            return base_checks + [TeamEfficiencyCheck]
```

---

### 4. Composable Architecture

**What AgencyOS Includes:**
- Headless CMS (Directus) separates content from presentation
- Nuxt frontend consumes APIs
- Extensible without rebuilding core

**Agent World Equivalent:**

| AgencyOS Pattern | Agent World Implementation |
|------------------|---------------------------|
| Headless CMS | **FastAPI backend** (business logic, agents, governance) |
| Frontend | **React frontend** (Ledger Shell UI) |
| API layer | **REST + WebSocket APIs** (stateless, tenant-scoped) |
| Extensible | **Plugin architecture** (business models, tools, channels) |

**Status:**
- ✅ Clean separation (backend/frontend)
- ✅ API-first design
- ✅ Business models as plugins
- ✅ MCP tools as plugins
- ⚠️ Channel integrations (Etsy, Shopify partial)

---

### 5. Role-Based Structure

**What AgencyOS Includes:**
- Admin users
- Client users (portal access)
- Role-based permissions

**Agent World Equivalent:**

| AgencyOS | Agent World |
|----------|-------------|
| Admin | **Tenant owner** (full access, set budgets, approve strategies) |
| Client | **Business operator** (view workspace, approve tasks, see revenue) |
| Roles | **RBAC** (Ledger: governor, operator, viewer) |

**Implementation Status:**
- ✅ JWT authentication
- ✅ Tenant isolation (3-layer defense)
- ✅ Ledger RBAC (governor, operator roles)
- ✅ PostgreSQL RLS
- ⚠️ Role management UI (needs admin panel)

---

## Patterns to Implement (Priority)

### High Priority (Next Sprint)

1. **Enhanced Proposal Builder**
   - Strategy recommendation as polished proposal
   - Cost breakdown, timeline, expected impact
   - Client approval workflow
   - One-click approve → activate agents

2. **Asset Library**
   - Design file management (thumbnails, mockups, exports)
   - Version control for assets
   - Search, filter, organize
   - Direct download/share

3. **Task Assignment to Humans**
   - Agent creates task → routes to human
   - Human completes → agent continues
   - Context preserved across handoff

### Medium Priority (Next Month)

4. **More Business Model Templates**
   - Shopify Dropship
   - Freelance Services
   - Digital Products/Courses
   - SaaS/Apps

5. **Dashboard Builder**
   - Customizable widgets
   - Drag-drop layout
   - Save/share dashboards
   - Role-based default views

6. **Stripe Integration**
   - Connect Stripe account
   - Show real revenue (not just tracked)
   - Payout management
   - Tax reporting helpers

### Lower Priority (Future)

7. **White-Label Client Portal**
   - Custom branding
   - Domain mapping
   - Branded emails

8. **Mobile App**
   - iOS/Android apps
   - Push notifications
   - Quick approvals

---

## Directus AgencyOS → Agent World Mapping

```
AgencyOS (Nuxt + Directus)
├── Website (marketing)
├── CRM (organizations, contacts)
├── Project Tracker (projects, tasks, proposals)
├── Client Portal (authenticated views)
└── Invoicing (Stripe)

Agent World (React + FastAPI)
├── Landing Page (marketing) ✅
├── Business Management (tenant isolation) ✅
├── Strategy Pipeline (intake → diagnosis → strategy → execution) ✅
├── BusinessWorkspace (authenticated, role-based) ✅
├── Revenue Tracking (hybrid internal + external) ✅
└── Ledger Governance (budgets, approvals, audit) ✅
```

**Key Difference:**
- AgencyOS = Agency management + client collaboration
- Agent World = **Business diagnosis + AI execution** with governance

**Overlap:**
- Both have operational infrastructure (CRM, tasks, dashboards)
- Both have role-based access
- Both have template systems

---

## What Makes Agent World Different (From AgencyOS)

| AgencyOS | Agent World |
|----------|-------------|
| For **digital agencies** | For **any business model** (TikTok, Etsy, YouTube, services) |
| **Manual** project management | **AI-driven** diagnosis and execution |
| **Human** does the work | **8 agents** do the work, human approves |
| **Client** collaboration focus | **Growth** execution focus |
| **Template** → customize manually | **Diagnosis** → activate agents automatically |
| Project tracking | **Bottleneck detection** + strategy generation |

---

## Implementation Plan

### Phase 1: Proposal Builder (This Week)

```javascript
// StrategyRecommendation.jsx enhancement
<ProposalCard>
  <Header>
    <Title>30-Day Growth Sprint</Title>
    <Badge color="green">Expected: +5,500 followers</Badge>
  </Header>
  
  <CostBreakdown>
    <LineItem>Your time: 30 min/day × 30 days</LineItem>
    <LineItem>Tool costs: $0 (free tier)</LineItem>
    <LineItem>Total investment: ~15 hours</LineItem>
    <Total>Expected return: $200-500/month</Total>
  </CostBreakdown>
  
  <Timeline>
    <Week>Week 1: Setup + batch content</Week>
    <Week>Week 2-3: Post daily + test hooks</Week>
    <Week>Week 4: Analyze + optimize</Week>
  </Timeline>
  
  <AgentsAssigned>
    <AgentBadge icon="📈" name="Nova" task="Trend research" />
    <AgentBadge icon="🎨" name="Pixel" task="Thumbnails" />
    <AgentBadge icon="✍️" name="Forge" task="Scripts" />
  </AgentsAssigned>
  
  <Actions>
    <Button variant="primary">👍 Approve & Activate</Button>
    <Button variant="secondary">✏️ Modify</Button>
    <Button variant="ghost">👎 Decline</Button>
  </Actions>
</ProposalCard>
```

### Phase 2: Asset Library (Next Week)

```python
# Asset management endpoints
POST /assets/upload
GET /assets?type=thumbnail&status=approved
GET /assets/{id}/versions
POST /assets/{id}/approve  # Ledger approval for use
```

### Phase 3: Human Task Assignment (Following Week)

```python
# Agent creates human task
task = {
    "type": "human_review",
    "context": "Thumbnail generated, needs your brand check",
    "agent": "Pixel",
    "preview_url": "...",
    "options": ["approve", "request_changes", "reject"],
    "blocking": True  # Agent waits for human
}

# Human completes
POST /tasks/{id}/complete
→ Agent continues workflow
```

---

## Summary

**From Directus AgencyOS, Agent World pulls:**
1. ✅ **Operational infrastructure** (CRM, tasks, dashboards) — already implemented
2. ✅ **Role-based structure** (admin, operator, viewer) — already implemented
3. ✅ **Template system** (business models as templates) — already implemented
4. ⚠️ **Proposal builder polish** — needs UI enhancement
5. ⚠️ **Asset library** — needs file management system
6. ⚠️ **Human task assignment** — needs explicit handoff mechanism

**Differentiation maintained:**
- Diagnosis-first (not manual project setup)
- 8 specialist agents (not just a workspace)
- Cross-business (not just agencies)
- Revenue tracking + optimization (not just invoicing)

---

## Resources

- AgencyOS GitHub: https://github.com/directus-labs/agency-os
- Directus: https://directus.io
- Nuxt: https://nuxt.com
