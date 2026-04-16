# Directus AgencyOS — Code-Level Pattern Analysis

> Cloned from https://github.com/directus-labs/agency-os  
> Tech stack: Nuxt 3 + Vue 3 + TypeScript + Tailwind + Directus CMS

---

## Architecture Overview

AgencyOS uses **Nuxt 3 Layers** — a modular architecture where each feature is a self-contained layer:

```
layers/
├── proposals/           # Dynamic proposal builder (public)
│   ├── components/blocks/  # Block-based page builder (Hero, Pricing, Acceptance)
│   ├── composables/        # useProposals() - sidebar state management
│   └── pages/proposals/    # [id].vue - dynamic proposal routing
│
├── portal/              # Client portal (authenticated)
│   ├── components/       # TaskList, ProjectMilestones, FileUploadModal
│   ├── pages/portal/     # Client dashboard, projects, billing, files
│   └── server/api/       # Stripe integration, webhooks
│
└── [default layer]        # Marketing website
    ├── components/       # Shared UI components
    ├── pages/            # Homepage, blog, forms
    └── composables/      # useDirectus() - data fetching
```

**Key Pattern:** Layers are feature boundaries. Each layer has its own pages, components, composables, and server routes. This is modularization done right.

---

## Pattern 1: Block-Based Proposal Builder

### What It Is
Proposals are composed of reusable "blocks" (sections) that can be mixed and matched:

| Block | Purpose |
|-------|---------|
| `Hero.vue` | Cover slide with logo, title, client name |
| `Pricing.vue` | Two-tier pricing table with features |
| `Acceptance.vue` | E-signature form with validation |

### Code Structure
```vue
<!-- layers/proposals/components/blocks/Hero.vue -->
<script setup lang="ts">
export interface HeroProps {
  name: string;           // Proposal title
  organization: string;   // Client company
  owner: User;           // Account manager
}
defineProps<HeroProps>();
</script>

<template>
  <div class="relative flex items-center justify-center w-full h-screen">
    <Logo />
    <TypographyHeadline :content="name" size="title" />
    <TypographyHeadline :content="organization" />
    <!-- <VAvatar :author="owner" /> -->
  </div>
</template>
```

### Agent World Equivalent
```jsx
// components/proposals/ProposalCard.jsx (✅ Already implemented)
<ProposalCard 
  strategy={strategy}
  diagnosis={diagnosis}
  onApprove={handleApprove}
  onModify={handleModify}
  onDecline={handleDecline}
/>

// Internally renders:
// - Header (name, org, badge)
// - CostBreakdown (time, budget, ROI)
// - Timeline (4-week grid)
// - AgentsAssigned (badges with icons)
// - ActionBar (approve/modify/decline)
```

**Gap to Close:** AgencyOS has a full block-based page builder with drag-drop visual editing. Agent World's ProposalCard is a single card component. Next step: break into composable blocks.

---

## Pattern 2: Visual State Management (Composables)

### What It Is
Simple, focused composables for local state:

```typescript
// layers/proposals/composables/useProposals.ts
const showSidebar = ref(false);

export default function useProposals() {
  const toggleSidebar = () => {
    showSidebar.value = !showSidebar.value;
  };
  return { showSidebar, toggleSidebar };
}
```

### Agent World Equivalent
```javascript
// hooks/useProposalBuilder.js (create this)
export function useProposalBuilder() {
  const [blocks, setBlocks] = useState([]);
  const [activeBlock, setActiveBlock] = useState(null);
  
  const addBlock = (type, data) => {
    setBlocks([...blocks, { id: crypto.randomUUID(), type, data }]);
  };
  
  const moveBlock = (from, to) => {
    const newBlocks = [...blocks];
    const [removed] = newBlocks.splice(from, 1);
    newBlocks.splice(to, 0, removed);
    setBlocks(newBlocks);
  };
  
  return { blocks, activeBlock, addBlock, moveBlock };
}
```

---

## Pattern 3: E-Signature with Form Validation

### What It Is
The Acceptance block includes a full signature workflow:

```typescript
// Form schema with validation rules
const form = {
  submit_label: 'Accept Proposal',
  schema: [
    { name: 'first_name', type: 'text', validation: 'required', width: '50' },
    { name: 'last_name', type: 'text', validation: 'required', width: '50' },
    { name: 'email', type: 'email', validation: 'required|email', width: '100' },
    { name: 'signature', type: 'signature', options: ['type', 'draw', 'upload'] },
    { name: 'esignature_agreement', type: 'checkbox', validation: 'required' }
  ]
};

// Prefill from URL params
function getPrefillData(query: LocationQuery) {
  const prefillData: { [key: string]: string } = {};
  Object.keys(query).forEach((key) => {
    if (key.startsWith('prefill_')) {
      prefillData[key.replace('prefill_', '')] = query[key] as string;
    }
  });
  return prefillData;
}
```

### Key Features
- **Schema-driven forms:** Define once, render anywhere
- **Validation:** Per-field rules (`required`, `email`, etc.)
- **Prefill:** `?prefill_first_name=John` auto-populates
- **File upload:** Signature images uploaded to Directus
- **Success/error states:** Built-in alert handling

### Agent World Equivalent
```jsx
// components/proposals/StrategyAcceptanceForm.jsx (create this)
<StrategyAcceptanceForm 
  strategy={strategy}
  prefillData={{ business_name, owner_email }}
  onSubmit={handleApproval}
  validationSchema={{
    acknowledgment: 'required',
    budget_confirmation: 'required'
  }}
/>
```

---

## Pattern 4: Project Milestones (Progress Visualization)

### What It Is
Visual timeline showing project phases:

```vue
<!-- ProjectMilestones.vue -->
<nav aria-label="Progress">
  <ol class="flex items-start w-full">
    <li v-for="(step, index) in steps" :key="index" class="flex flex-1">
      <PortalProjectMilestone
        :name="step.name"
        :icon="step.icon"
        :is-complete="step.isComplete"
        :is-current="step.isCurrent"
        :status="step.status"
        :date="step.date"
      />
      <Icon v-if="index !== steps.length - 1" name="i-heroicons-arrow-long-right" />
    </li>
  </ol>
</nav>
```

### Agent World Equivalent
```jsx
// components/proposals/StrategyTimeline.jsx (create this)
<StrategyTimeline 
  phases={[
    { name: 'Setup', icon: '🚀', status: 'complete', date: 'Week 1' },
    { name: 'Content', icon: '✍️', status: 'current', date: 'Week 2' },
    { name: 'Publish', icon: '📢', status: 'pending', date: 'Week 3' },
    { name: 'Optimize', icon: '📈', status: 'pending', date: 'Week 4' }
  ]}
/>
```

---

## Pattern 5: Client Task Assignment

### What It Is
Tasks can be assigned to clients with visibility control:

```typescript
// TaskList.vue filters
tasks.filter({
  _and: [
    { project: { _eq: props.projectId } },
    { is_visible_to_client: { _eq: true } },  // ← Key: client-only visibility
    { type: { _neq: 'milestone' } }
  ]
});

// UI columns
const columns = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'due_date', label: 'Due Date' },
  { key: 'status', label: 'Status' },
  { key: 'assigned_to', label: 'Assigned To' },
  { key: 'actions' }
];
```

### Agent World Equivalent
```jsx
// HumanTaskQueue already implements this (✅)
<HumanTaskQueue 
  businessId={businessId}
  filter={{ is_visible_to_user: true }}
/>

// Task schema:
{
  id: '1',
  title: 'Review TikTok thumbnail',
  assigned_to: 'user',        // 'user' | 'agent'
  is_visible_to_user: true,
  status: 'pending',
  priority: 'high',
  due_date: '2025-04-17'
}
```

---

## Pattern 6: Directus Data Fetching Pattern

### What It Is
A typed composable for CMS queries:

```typescript
// composables/useDirectus.ts (inferred)
const { data: tasks, pending, error } = await useAsyncData(
  `${props.projectId}-tasks`,
  () => useDirectus(
    readItems('os_tasks', {
      fields: ['*', { assigned_to: ['id', 'first_name', 'avatar'] }],
      filter: { project: { _eq: props.projectId } },
      sort: ['due_date']
    })
  )
);
```

### Key Features
- **AsyncData:** Nuxt's SSR-friendly data fetching
- **Field selection:** Only fetch what's needed
- **Relations:** Nested field selection `{ assigned_to: [...] }`
- **Filtering:** Directus filter syntax
- **Caching:** Automatic key-based caching

### Agent World Equivalent
```javascript
// hooks/useBusiness.js (already implemented via useApi)
const { data: business, loading, error } = useApi(`/businesses/${id}`);

// With relations (TODO: implement nested fetching)
const { data: diagnosis } = useApi(
  `/diagnostics/${id}?include=strategy,tasks,agents`
);
```

---

## Pattern 7: File Management with Upload

### What It Is
Client portal file management with Directus integration:

```vue
<!-- FileUploadModal.vue -->
<script setup>
function uploadTheFiles(files: File[]) {
  const formData = new FormData();
  files.forEach((file) => formData.append('file', file));
  return useDirectus(uploadFiles(formData));
}
</script>
```

### Agent World Equivalent
```jsx
// AssetLibrary (✅ Already implemented)
<AssetLibrary 
  businessId={businessId}
  onUpload={handleUpload}
  filter={{ status: 'approved' }}
/>

// Upload flow:
// 1. Drag-drop or click to select
// 2. Upload to S3/Cloudinary (TODO)
// 3. Create record in Directus (TODO)
// 4. Show in grid with preview
```

---

## Pattern 8: Theme System

### What It Is
Programmatic theme configuration:

```typescript
// theme.ts
export default defineTheme({
  colors: {
    primary: '#06b6d4',      // cyan-500
    secondary: '#8b5cf6',    // violet-500
    background: '#0f172a',   // slate-900
    surface: 'rgba(255,255,255,0.05)'
  },
  borderRadius: {
    sm: '0.5rem',
    DEFAULT: '0.75rem',
    lg: '1rem'
  }
});
```

### Agent World Equivalent
```javascript
// tailwind.config.js (already implemented)
colors: {
  background: '#0a0a0f',
  surface: 'rgba(255,255,255,0.05)',
  glass: {
    light: 'rgba(255,255,255,0.08)',
    medium: 'rgba(255,255,255,0.12)',
    heavy: 'rgba(255,255,255,0.16)'
  },
  accent: {
    cyan: '#22d3ee',
    violet: '#8b5cf6'
  }
}
```

---

## Detailed Comparison Table

| AgencyOS Pattern | Implementation | Agent World Equivalent | Status |
|------------------|----------------|------------------------|--------|
| **Block-based proposals** | Vue components per block | ProposalCard (single) | ⚠️ Partial — needs block breakdown |
| **E-signature flow** | FormKit schema + file upload | Not implemented | ❌ Missing |
| **Project milestones** | Timeline visualization | Timeline component | ⚠️ Partial — needs visual polish |
| **Client task assignment** | `is_visible_to_client` filter | HumanTaskQueue | ✅ Implemented |
| **File upload modal** | Directus file API | AssetLibrary | ✅ Implemented |
| **Prefill from URL** | `?prefill_name=John` | Not implemented | ❌ Missing |
| **Form validation** | FormKit validation rules | Manual validation | ⚠️ Partial |
| **Async data fetching** | `useAsyncData` + `useDirectus` | `useApi` hook | ✅ Implemented |
| **Layer architecture** | Nuxt layers | Component folders | ⚠️ Different approach |

---

## Immediate Action Items (Priority Order)

### P1 — Proposal Builder Enhancements
1. **Break ProposalCard into blocks:**
   - `ProposalHeader` — Title, badge, organization
   - `CostBreakdown` — Investment grid
   - `TimelineBlock` — Week-by-week phases
   - `AgentAssignments` — Agent badges
   - `ActionFooter` — Approve/Modify/Decline

2. **Add URL prefill support:**
   ```jsx
   // StrategyRecommendation.jsx
   const query = useQueryParams();
   const prefillData = extractPrefill(query); // ?prefill_budget=500
   ```

### P2 — E-Signature Integration
1. **Create StrategyAcceptanceForm:**
   - Schema-driven form config
   - Digital signature (type/draw)
   - Checkbox acknowledgments
   - Submit to Ledger for audit trail

### P3 — Visual Timeline
1. **Create StrategyTimeline component:**
   - Horizontal step visualization
   - Icons per phase
   - Complete/Current/Pending states
   - Animated transitions

---

## Key Takeaways

**What AgencyOS Does Exceptionally Well:**
1. **Layer architecture** — True modularization
2. **Block-based builder** — Composable proposals
3. **E-signature flow** — Legally binding acceptance
4. **Schema-driven forms** — Validation + prefill
5. **Visual progress** — Milestone timelines

**What Agent World Already Has:**
1. Proposal presentation (single card)
2. Human task queue
3. Asset library
4. API fetching patterns

**What Needs Building:**
1. Block breakdown of proposals
2. E-signature workflow
3. URL prefill
4. Visual timeline polish

---

## Resources

- **Repository:** `/root/.openclaw/workspace/agency-os`
- **Key Layers:**
  - `layers/proposals/` — Proposal builder
  - `layers/portal/` — Client portal
  - `layers/portal/server/api/stripe/` — Payment integration
- **Agent World Docs:** `/root/.openclaw/workspace/agent-world/docs/AGENCYOS_PATTERNS.md`
