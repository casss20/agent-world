"""
business_models/base.py — Agent World

Base class for business-specific diagnostic and strategy logic.
Each business model (Etsy POD, Shopify, TikTok, Service) implements
these interfaces to provide tailored diagnosis and recommendations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class BusinessStage(Enum):
    """Growth stages for any business"""
    IDEATION = "ideation"           # Validating idea
    TRACTION = "traction"           # Some sales, finding PMF
    GROWTH = "growth"               # Working model, scaling
    OPTIMIZATION = "optimization"   # Mature, improving efficiency


class BottleneckCategory(Enum):
    """Categories of business constraints"""
    ACQUISITION = "acquisition"     # Getting traffic/leads
    CONVERSION = "conversion"       # Turning visitors into customers
    RETENTION = "retention"         # Keeping customers
    MONETIZATION = "monetization"   # Revenue per customer
    OPERATIONS = "operations"       # Delivery, fulfillment, capacity


class Severity(Enum):
    """Bottleneck severity levels"""
    CRITICAL = "critical"           # Blocking all growth
    HIGH = "high"                   # Major constraint
    MEDIUM = "medium"               # Moderate impact
    LOW = "low"                     # Minor optimization
    HEALTHY = "healthy"             # Not a bottleneck


@dataclass
class ResourceConstraints:
    """Available resources for executing strategies"""
    available_hours: float          # Hours per week
    available_budget: float         # Monthly budget in USD
    team_size: int                  # Number of people
    available_skills: List[str]     # e.g., ["design", "copywriting", "ads"]


@dataclass
class BusinessContext:
    """Complete context for a business"""
    business_model: str             # "etsy_pod", "shopify_brand", etc.
    stage: BusinessStage
    goals: Dict[str, Any]           # Revenue target, audience size, etc.
    resources: ResourceConstraints
    current_metrics: Dict[str, float]  # Traffic, conversion, revenue, etc.
    channels: List[str]             # Connected platforms
    notes: Optional[str] = None
    business_id: Optional[str] = None  # Unique identifier


@dataclass
class Evidence:
    """Evidence supporting a diagnostic finding"""
    metric: str                     # e.g., "conversion_rate"
    value: float                    # Current value
    benchmark: float              # Expected/typical value for stage
    gap_percentage: float           # How far below benchmark
    source: str                     # "api", "user_input", "estimate"


@dataclass
class Bottleneck:
    """Identified constraint in the business"""
    category: BottleneckCategory
    severity: Severity
    description: str                # Human-readable explanation
    impact: str                     # What this is costing the business
    evidence: List[Evidence]          # Supporting data
    suggested_checks: List[str]     # Additional diagnostics to run


@dataclass
class CheckResult:
    """Result of a single diagnostic check"""
    category: BottleneckCategory
    status: Severity
    description: str
    severity: Severity
    estimated_impact: str
    evidence: List[Evidence]


@dataclass
class Diagnosis:
    """Complete diagnostic result for a business"""
    business_model: str
    business_id: str
    primary_bottleneck: Bottleneck
    secondary_bottlenecks: List[Bottleneck]
    health_score: float             # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


@dataclass
class Strategy:
    """A strategy/intervention to address a bottleneck"""
    name: str
    description: str
    target_bottleneck: BottleneckCategory
    effort_hours: float             # Estimated time required
    budget_required: float          # Estimated cost
    skill_requirements: List[str]   # Required skills
    expected_impact: str            # Expected outcome
    success_metrics: List[str]     # How to measure success
    steps: List[str]               # Step-by-step implementation
    time_to_result: str            # How long until impact visible


@dataclass
class StrategyRecommendation:
    """Recommended strategy with supporting context"""
    primary_strategy: Optional[Strategy]
    supporting_strategies: List[Strategy]
    expected_outcome: str
    measurement_plan: Dict[str, Any]
    timeline: Dict[str, Any]
    risks: List[str]


@dataclass
class KPITracking:
    """Metric to track for a specific business model"""
    name: str
    description: str
    calculation: str
    target_range: tuple            # (min, max) or typical range
    frequency: str                  # "daily", "weekly", "monthly"
    data_source: str                # Where to get this metric


class DiagnosticCheck(ABC):
    """Abstract base for specific diagnostic checks"""
    
    @property
    @abstractmethod
    def category(self) -> BottleneckCategory:
        """Which category this check assesses"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name"""
        pass
    
    @abstractmethod
    async def run(self, context: BusinessContext) -> CheckResult:
        """Execute the diagnostic check"""
        pass


class BusinessModel(ABC):
    """Base class for business-specific diagnostics and strategies"""
    
    model_id: str = "base"
    display_name: str = "Base Business Model"
    icon: str = "🏢"
    description: str = "Abstract base business model"
    
    def __init__(self):
        self.diagnostic_checks: List[DiagnosticCheck] = self._get_diagnostic_checks()
        self.strategy_library = self._get_strategy_library()
        self.kpi_definitions = self._get_kpi_definitions()
    
    @abstractmethod
    def _get_diagnostic_checks(self) -> List[DiagnosticCheck]:
        """Return list of diagnostic checks for this business model"""
        pass
    
    @abstractmethod
    def _get_strategy_library(self) -> Dict[BottleneckCategory, List[Strategy]]:
        """Return mapping of bottleneck categories to strategies"""
        pass
    
    @abstractmethod
    def _get_kpi_definitions(self) -> List[KPITracking]:
        """Return KPIs relevant to this business model"""
        pass
    
    async def diagnose(self, context: BusinessContext) -> Diagnosis:
        """Run full diagnostic on the business"""
        
        # Run all diagnostic checks
        results = []
        for check in self.diagnostic_checks:
            try:
                result = await check.run(context)
                results.append(result)
            except Exception as e:
                # Log error but continue with other checks
                results.append(CheckResult(
                    category=check.category,
                    status=Severity.MEDIUM,
                    description=f"Check failed: {check.name}",
                    severity=Severity.MEDIUM,
                    estimated_impact="Unknown - check failed to complete",
                    evidence=[]
                ))
        
        # Score and rank bottlenecks
        bottlenecks = self._identify_bottlenecks(results)
        
        # Calculate overall health
        health_score = self._calculate_health_score(results)
        
        return Diagnosis(
            business_model=self.model_id,
            business_id=getattr(context, 'business_id', 'unknown'),
            primary_bottleneck=bottlenecks[0] if bottlenecks else None,
            secondary_bottlenecks=bottlenecks[1:3],
            health_score=health_score
        )
    
    def _identify_bottlenecks(self, results: List[CheckResult]) -> List[Bottleneck]:
        """Convert check results to ranked bottlenecks"""
        
        severity_scores = {
            Severity.CRITICAL: 10,
            Severity.HIGH: 7,
            Severity.MEDIUM: 4,
            Severity.LOW: 1,
            Severity.HEALTHY: 0
        }
        
        bottlenecks = []
        for result in results:
            if result.status != Severity.HEALTHY:
                score = severity_scores.get(result.severity, 1)
                bottleneck = Bottleneck(
                    category=result.category,
                    severity=result.severity,
                    description=result.description,
                    impact=result.estimated_impact,
                    evidence=result.evidence,
                    suggested_checks=[]
                )
                bottlenecks.append((score, bottleneck))
        
        # Sort by severity score descending
        bottlenecks.sort(key=lambda x: x[0], reverse=True)
        return [b for _, b in bottlenecks]
    
    def _calculate_health_score(self, results: List[CheckResult]) -> float:
        """Calculate overall business health (0.0 to 1.0)"""
        
        if not results:
            return 0.5  # Unknown
        
        severity_scores = {
            Severity.CRITICAL: 0.0,
            Severity.HIGH: 0.3,
            Severity.MEDIUM: 0.6,
            Severity.LOW: 0.85,
            Severity.HEALTHY: 1.0
        }
        
        total_score = sum(
            severity_scores.get(r.status, 0.5) 
            for r in results
        )
        
        return total_score / len(results)
    
    async def recommend_strategies(
        self,
        diagnosis: Diagnosis,
        resources: ResourceConstraints
    ) -> StrategyRecommendation:
        """Generate strategy recommendations based on diagnosis"""
        
        # Get strategies for primary bottleneck
        candidates = self.strategy_library.get(
            diagnosis.primary_bottleneck.category, 
            []
        )
        
        # Filter by resource constraints
        feasible = self._filter_by_resources(candidates, resources)
        
        # Score by ROI (expected impact / effort)
        scored = []
        for strategy in feasible:
            # Simple ROI scoring: impact / (hours + budget/100)
            effort = strategy.effort_hours + (strategy.budget_required / 100)
            roi = 1.0 / effort if effort > 0 else 0
            scored.append((roi, strategy))
        
        # Sort by ROI
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Build recommendation
        primary = scored[0][1] if scored else None
        supporting = [s for _, s in scored[1:3]]
        
        return StrategyRecommendation(
            primary_strategy=primary,
            supporting_strategies=supporting,
            expected_outcome=self._project_outcome(primary, supporting, diagnosis),
            measurement_plan=self._build_measurement_plan(primary),
            timeline=self._build_timeline(primary, supporting, resources),
            risks=self._identify_risks(primary, diagnosis)
        )
    
    def _filter_by_resources(
        self, 
        strategies: List[Strategy], 
        resources: ResourceConstraints
    ) -> List[Strategy]:
        """Filter strategies by available resources"""
        
        feasible = []
        for strategy in strategies:
            # Check time
            if strategy.effort_hours > resources.available_hours * 4:  # Monthly budget
                continue
            
            # Check budget
            if strategy.budget_required > resources.available_budget:
                continue
            
            # Check skills (require at least one match or no specific skills)
            if strategy.skill_requirements:
                has_skill = any(
                    skill in resources.available_skills 
                    for skill in strategy.skill_requirements
                )
                if not has_skill:
                    continue
            
            feasible.append(strategy)
        
        return feasible
    
    def _project_outcome(
        self,
        primary: Optional[Strategy],
        supporting: List[Strategy],
        diagnosis: Diagnosis
    ) -> str:
        """Project expected outcome from implementing strategies"""
        
        if not primary:
            return "No feasible strategy found with current resources"
        
        return (
            f"Addressing {diagnosis.primary_bottleneck.category.value} through "
            f"{primary.name} and {len(supporting)} supporting initiatives. "
            f"Expected to see {primary.time_to_result}."
        )
    
    def _build_measurement_plan(self, primary: Optional[Strategy]) -> Dict[str, Any]:
        """Define how to measure strategy success"""
        
        if not primary:
            return {}
        
        return {
            "primary_metrics": primary.success_metrics,
            "review_frequency": "weekly",
            "success_criteria": "10% improvement in primary metric",
            "abort_criteria": "No improvement after 4 weeks"
        }
    
    def _build_timeline(
        self,
        primary: Optional[Strategy],
        supporting: List[Strategy],
        resources: ResourceConstraints
    ) -> Dict[str, Any]:
        """Build implementation timeline"""
        
        if not primary:
            return {}
        
        weeks = []
        
        # Week 1: Primary strategy
        weeks.append({
            "week": 1,
            "focus": f"Start {primary.name}",
            "tasks": primary.steps[:3] if primary.steps else ["Begin implementation"]
        })
        
        # Week 2-3: Continue primary, start first supporting
        for i, strategy in enumerate(supporting[:2], start=2):
            weeks.append({
                "week": i,
                "focus": f"Continue {primary.name}, start {strategy.name}",
                "tasks": strategy.steps[:2] if strategy.steps else ["Begin implementation"]
            })
        
        # Week 4: Review
        weeks.append({
            "week": 4,
            "focus": "Review results and adjust",
            "tasks": ["Measure outcomes", "Compare to baseline", "Decide: continue, adjust, or pivot"]
        })
        
        return {
            "duration_weeks": 4,
            "weekly_breakdown": weeks,
            "hours_per_week": min(resources.available_hours / 4, 10)
        }
    
    def _identify_risks(
        self, 
        primary: Optional[Strategy], 
        diagnosis: Diagnosis
    ) -> List[str]:
        """Identify potential risks in the strategy"""
        
        risks = [
            f"Primary bottleneck ({diagnosis.primary_bottleneck.category.value}) "
            "may not be correctly identified"
        ]
        
        if primary and primary.effort_hours > 40:
            risks.append("High time investment may delay other improvements")
        
        risks.append("External factors (market changes, platform policies) may affect outcomes")
        
        return risks
    
    def get_kpis(self) -> List[KPITracking]:
        """Get KPIs relevant to this business model"""
        return self.kpi_definitions


class BusinessModelRegistry:
    """Registry of available business models"""
    
    def __init__(self):
        self._models: Dict[str, BusinessModel] = {}
    
    def register(self, model: BusinessModel):
        """Register a business model"""
        self._models[model.model_id] = model
    
    def get(self, model_id: str) -> Optional[BusinessModel]:
        """Get a business model by ID"""
        return self._models.get(model_id)
    
    def list_models(self) -> List[Dict[str, str]]:
        """List all available models"""
        return [
            {
                "id": m.model_id,
                "name": m.display_name,
                "icon": m.icon,
                "description": m.description
            }
            for m in self._models.values()
        ]


# Global registry instance
registry = BusinessModelRegistry()
