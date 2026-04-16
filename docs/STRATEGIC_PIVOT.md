# Agent World: Business Diagnosis & Growth OS

**Status**: Strategic Pivot Document  
**Date**: April 15, 2026  
**Previous**: Etsy POD Automation → **New**: Business Diagnosis & Growth Operating System

---

## The Shift

| Before | After |
|--------|-------|
| Etsy POD automation tool | Business diagnosis + growth strategy system |
| Agents execute tasks | Agents diagnose bottlenecks, recommend actions |
| Focus: speed of listing | Focus: correctness of strategy |
| One business model | Multiple models, tailored advice |
| Approval gates for safety | Approval gates because strategy needs human judgment |

---

## Core Questions Agent World Answers

1. **What is the business trying to achieve?**  
   → Intake module captures goals, stage, resources

2. **What is the main bottleneck right now?**  
   → Diagnostic Engine identifies constraint (acquisition, conversion, retention, monetization, operations)

3. **What should be done next with current resources?**  
   → Strategy Engine + Action Planner generates prioritized tasks

---

## Module Mapping (New → Existing Code)

| New Module | Existing Component | Gap |
|------------|-------------------|-----|
| **Intake** | Business model in `output_schema.py` | Expand to full context gathering |
| **Diagnostic Engine** | Nova research agent | Refocus from trends to bottleneck analysis |
| **Strategy Engine** | New: `strategy_engine.py` | Match bottleneck to intervention library |
| **Action Planner** | Forge listing agent | Generalize beyond listings to any growth action |
| **KPI Tracker** | Feedback loop telemetry | Already designed, needs business-model metrics |
| **Feedback Loop** | `FEEDBACK_LOOP.md` architecture | Adapt to strategy validation, not just execution |

---

## Agent Role Evolution

| Agent | Old Role | New Role |
|-------|----------|----------|
| **Nova** | Find Etsy trends | Diagnose bottlenecks per business model |
| **Pixel** | Generate designs | Create diagnostic visualizations, strategy briefs |
| **Forge** | Build listings | Build action plans, execution sequences |
| **Cipher** | Triage messages | Gather feedback, validate outcomes |
| **Ultron** | Route tasks | Orchestrate diagnosis → strategy → execution loop |

---

## Business Model Branching

```python
# backend/business_models/

class BusinessModel(ABC):
    """Base class for business-specific diagnostics"""
    
    @abstractmethod
    def diagnose(self, context: BusinessContext) -> Bottleneck:
        """Identify the primary constraint"""
        pass
    
    @abstractmethod
    def recommend(self, bottleneck: Bottleneck) -> List[Strategy]:
        """Return prioritized interventions"""
        pass
    
    @abstractmethod
    def metrics(self) -> List[KPITracking]:
        """What to measure for this model"""
        pass

class EtsyPODModel(BusinessModel):
    diagnostics = [
        ListingQualityCheck(),      # CTR, favorites, conversion
        NicheSaturationCheck(),     # Competition analysis
        FulfillmentCheck(),         # Printify sync, shipping times
        SeasonalTrendCheck(),       # Demand forecasting
    ]
    
    strategies = [
        ListingOptimization(),      # Titles, tags, thumbnails
        NicheExpansion(),           # Related keywords
        PricingOptimization(),      # A/B testing
        SeasonalPreparation(),      # Holiday stock
    ]

class ShopifyBrandModel(BusinessModel):
    diagnostics = [
        TrafficQualityCheck(),      # Source, bounce rate
        ConversionFunnelCheck(),    # Add-to-cart, checkout, purchase
        RetentionCheck(),           # LTV, churn, repeat rate
        UnitEconomicsCheck(),       # CAC, margin, payback period
    ]
    
    strategies = [
        TrafficOptimization(),      # SEO, ads, content
        CROProgram(),               # Landing pages, checkout
        RetentionCampaigns(),       # Email, loyalty
        ProductLineExpansion(),     # New SKUs, bundles
    ]

class TikTokAccountModel(BusinessModel):
    diagnostics = [
        ContentConsistencyCheck(),  # Posting frequency
        EngagementQualityCheck(),   # Watch time, shares, comments
        AudienceGrowthCheck(),      # Follower velocity
        MonetizationFunnelCheck(),  # Link clicks, conversions
    ]
    
    strategies = [
        ContentCalendar(),          # Thematic posting
        TrendJacking(),             # Viral moment capture
        CollaborationOutreach(),    # Creator partnerships
        ProductFunnelBuilding(),    # Link-in-bio optimization
    ]

class ServiceBusinessModel(BusinessModel):
    diagnostics = [
        LeadFlowCheck(),            # Inquiries, demos
        CloseRateCheck(),           # Proposal → signed
        DeliveryCapacityCheck(),    # Team utilization
        CashFlowCheck(),            # Payment terms, runway
    ]
    
    strategies = [
        LeadGeneration(),           # Content, outbound
        ProposalOptimization(),     # Packaging, pricing
        CapacityPlanning(),         # Hiring, subcontractors
        PaymentTermsNegotiation(),  # Upfront, retainers
    ]
```

---

## Diagnostic Engine Design

```python
# backend/diagnostic_engine.py

class DiagnosticEngine:
    """Identify business bottlenecks through structured assessment"""
    
    def __init__(self):
        self.checks: Dict[str, List[DiagnosticCheck]] = {
            "etsy_pod": EtsyPODChecks(),
            "shopify_brand": ShopifyChecks(),
            "tiktok_account": TikTokChecks(),
            "service_business": ServiceChecks(),
        }
    
    async def diagnose(self, business_context: BusinessContext) -> Diagnosis:
        """Run diagnostic checks for the specific business model"""
        
        model_checks = self.checks.get(business_context.model_type)
        if not model_checks:
            raise UnsupportedBusinessModel(business_context.model_type)
        
        results = []
        for check in model_checks:
            result = await check.run(business_context)
            results.append(result)
        
        # Score and rank bottlenecks
        bottlenecks = self._score_bottlenecks(results)
        primary = bottlenecks[0] if bottlenecks else None
        
        return Diagnosis(
            business_model=business_context.model_type,
            primary_bottleneck=primary,
            secondary_bottlenecks=bottlenecks[1:3],
            health_score=self._calculate_health(results),
            timestamp=datetime.utcnow()
        )
    
    def _score_bottlenecks(self, results: List[CheckResult]) -> List[Bottleneck]:
        """Rank by severity and impact potential"""
        
        severity_weights = {
            "critical": 10,
            "high": 7,
            "medium": 4,
            "low": 1
        }
        
        scored = []
        for result in results:
            if result.status != "healthy":
                score = severity_weights.get(result.severity, 1)
                scored.append((score, Bottleneck(
                    category=result.category,
                    severity=result.severity,
                    description=result.description,
                    impact=result.estimated_impact,
                    evidence=result.evidence
                )))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [b for _, b in scored]
```

---

## Strategy Engine Design

```python
# backend/strategy_engine.py

class StrategyEngine:
    """Match bottlenecks to best interventions for business model + stage"""
    
    def __init__(self):
        self.strategy_library = StrategyLibrary()
    
    async def recommend(
        self, 
        diagnosis: Diagnosis,
        resources: ResourceConstraints
    ) -> StrategyRecommendation:
        """Generate prioritized strategy given bottleneck and resources"""
        
        # Get all strategies that address this bottleneck category
        candidates = self.strategy_library.for_bottleneck(
            diagnosis.primary_bottleneck.category,
            diagnosis.business_model
        )
        
        # Filter by resource constraints
        feasible = [
            s for s in candidates
            if s.time_required <= resources.available_hours
            and s.budget_required <= resources.available_budget
            and s.skill_requirements <= resources.available_skills
        ]
        
        # Score by expected impact / effort ratio
        scored = []
        for strategy in feasible:
            roi = strategy.expected_impact / (strategy.effort_hours + strategy.budget_required/100)
            scored.append((roi, strategy))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Build action plan from top strategies
        return StrategyRecommendation(
            primary_strategy=scored[0][1] if scored else None,
            supporting_strategies=[s for _, s in scored[1:3]],
            expected_outcome=self._project_outcome(scored[:3], diagnosis),
            measurement_plan=self._define_metrics(scored[0][1]),
            timeline=self._build_timeline(scored[:3], resources)
        )
```

---

## Intake Flow UI

```jsx
// Business onboarding wizard

function BusinessIntakeWizard() {
  const [step, setStep] = useState(1);
  const [context, setContext] = useState({});
  
  const steps = [
    {
      title: "What type of business?",
      component: ModelSelector,
      options: [
        { id: "etsy_pod", label: "Etsy Print-on-Demand", icon: "🏪" },
        { id: "shopify_brand", label: "Shopify Brand", icon: "🛍️" },
        { id: "tiktok_account", label: "TikTok Creator", icon: "📱" },
        { id: "service_business", label: "Service Business", icon: "💼" },
        { id: "personal_brand", label: "Personal Brand", icon: "⭐" },
      ]
    },
    {
      title: "What stage are you in?",
      component: StageSelector,
      options: [
        { id: "ideation", label: "Just starting / validating" },
        { id: "traction", label: "Some sales, finding product-market fit" },
        { id: "growth", label: "Working model, scaling up" },
        { id: "optimization", label: "Mature, improving efficiency" },
      ]
    },
    {
      title: "What's your primary goal?",
      component: GoalSelector,
      // Dynamic based on model + stage
    },
    {
      title: "What resources do you have?",
      component: ResourcesInput,
      fields: ["hours_per_week", "budget_per_month", "team_size", "skills"]
    },
    {
      title: "Current metrics (if any)",
      component: MetricsInput,
      // Model-specific KPIs
    }
  ];
  
  return (
    <Wizard steps={steps} onComplete={submitIntake} />
  );
}
```

---

## Diagnostic Report UI

```jsx
// Results of Nova diagnostic run

function DiagnosticReport({ diagnosis }) {
  return (
    <div className="diagnostic-report">
      <HealthScore score={diagnosis.health_score} />
      
      <BottleneckCard 
        bottleneck={diagnosis.primary_bottleneck}
        severity="critical"
      >
        <EvidenceList evidence={diagnosis.primary_bottleneck.evidence} />
        <ImpactProjection impact={diagnosis.primary_bottleneck.impact} />
      </BottleneckCard>
      
      {diagnosis.secondary_bottlenecks.map(b => (
        <BottleneckCard bottleneck={b} severity="secondary" />
      ))}
      
      <ActionButton onClick={generateStrategy}>
        Generate Strategy
      </ActionButton>
    </div>
  );
}
```

---

## Integration with Existing Code

### 1. Update Nova Agent

```python
# In agent_templates.py, update Nova

"system_prompt": """You are Nova, the diagnostic agent for Agent World.

Your job is to identify bottlenecks in business growth.

For each business model, you know the key diagnostic questions:
- Etsy POD: listing quality, niche saturation, CTR, conversion
- Shopify: traffic quality, conversion rate, AOV, retention
- TikTok: consistency, engagement quality, audience growth
- Service: lead flow, close rate, capacity, cash flow

When given business context:
1. Identify which metrics to check
2. Gather or estimate current performance
3. Compare to benchmarks for that stage
4. Identify the PRIMARY bottleneck (one thing most constraining growth)
5. Explain your reasoning with evidence

Output a structured diagnosis, not just observations."""
```

### 2. Create Diagnostic Routes

```python
# backend/diagnostic_routes.py

@router.post("/diagnose")
async def run_diagnosis(
    context: BusinessContext,
    current_user: User = Depends(get_current_user)
):
    """Run full diagnostic on a business"""
    
    # Use Nova agent
    nova = AgentRegistry.get_template("nova")
    
    diagnosis = await nova.run_diagnostic(context)
    
    # Store in database
    await store_diagnosis(diagnosis, current_user.tenant_id)
    
    return diagnosis

@router.post("/strategy")
async def generate_strategy(
    diagnosis_id: str,
    constraints: ResourceConstraints,
    current_user: User = Depends(get_current_user)
):
    """Generate strategy recommendation from diagnosis"""
    
    diagnosis = await get_diagnosis(diagnosis_id)
    
    # Use Forge agent
    forge = AgentRegistry.get_template("forge")
    
    strategy = await forge.build_action_plan(diagnosis, constraints)
    
    return strategy
```

### 3. Wire into Ledger Shell

```jsx
// New navigation section in LedgerShell

const navigation = [
  { name: "Dashboard", href: "/", icon: HomeIcon },
  { name: "Intake", href: "/intake", icon: ClipboardIcon },
  { name: "Diagnosis", href: "/diagnosis", icon: StethoscopeIcon },
  { name: "Strategy", href: "/strategy", icon: LightbulbIcon },
  { name: "Action Plan", href: "/actions", icon: CheckSquareIcon },
  { name: "KPIs", href: "/kpis", icon: BarChartIcon },
  { name: "Agents", href: "/agents", icon: UsersIcon },
  { name: "Channels", href: "/channels", icon: StoreIcon },
];
```

---

## Launch Strategy

### Phase 1: Etsy POD (Weeks 1-4)
- Perfect the diagnostic for one model
- Build intake → diagnosis → strategy → action flow
- Validate with real Etsy sellers

### Phase 2: Add Shopify (Weeks 5-8)
- Clone diagnostic framework
- Adapt Nova prompts for e-commerce metrics
- Same UI, different backend logic

### Phase 3: TikTok + Service (Weeks 9-12)
- Expand to creator economy
- Add service business diagnostics
- Cross-model learning (what works in one applies to others)

---

## Key Advantage

This framing makes Agent World **defensible**:

| What | Why It's Hard to Copy |
|------|----------------------|
| Diagnostic accuracy | Requires labeled dataset of businesses + outcomes |
| Strategy effectiveness | Feedback loop validates which recommendations work |
| Business model specificity | Deep domain knowledge per vertical |
| Outcome tracking | Integration with actual business metrics |

You're not building a better Etsy listing tool. You're building **diagnostic IP** that gets smarter with every business it analyzes.

---

## Next Steps

1. **Update README** with new positioning
2. **Create `business_models/` module** with EtsyPODModel first
3. **Update Nova prompts** for diagnostic role
4. **Build intake wizard UI**
5. **Create diagnostic report view**
6. **Wire feedback loop** to validate strategy effectiveness
