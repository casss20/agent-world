"""
diagnostic_routes.py — Agent World

API endpoints for business diagnostics and strategy recommendations.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from business_models import (
    registry, BusinessContext, ResourceConstraints, BusinessStage
)
from governance_v2.auth import get_current_user, require_roles
from governance_v2 import EventType, GovernanceEvent

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

# Governance system reference (set by main.py)
governance_system_instance = None

def set_governance_system(gs):
    global governance_system_instance
    governance_system_instance = gs

def get_event_stream():
    """Get event stream from governance system if available"""
    if governance_system_instance:
        return governance_system_instance.event_stream
    return None

def get_tracer():
    """Get tracer from governance system if available"""
    if governance_system_instance:
        return governance_system_instance.tracer
    return None


# ── Request/Response Models ─────────────────────────────────────── #

class BusinessIntakeRequest(BaseModel):
    """Initial business context intake"""
    business_model: str = Field(..., description="Model ID: etsy_pod, shopify_brand, etc.")
    stage: str = Field(..., description="ideation, traction, growth, optimization")
    goals: Dict[str, Any] = Field(default_factory=dict)
    available_hours: float = Field(default=10, description="Hours per week available")
    available_budget: float = Field(default=500, description="Monthly budget in USD")
    team_size: int = Field(default=1)
    skills: list[str] = Field(default_factory=list)
    current_metrics: Dict[str, float] = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class DiagnosisResponse(BaseModel):
    """Diagnostic result"""
    diagnosis_id: str
    business_model: str
    health_score: float
    primary_bottleneck: Dict[str, Any]
    secondary_bottlenecks: list[Dict[str, Any]]
    timestamp: datetime
    recommendations_summary: str


class StrategyRequest(BaseModel):
    """Request strategy generation"""
    diagnosis_id: str
    max_strategies: int = Field(default=3, ge=1, le=5)


class StrategyResponse(BaseModel):
    """Strategy recommendation"""
    strategy_id: str
    primary_strategy: Optional[Dict[str, Any]]
    supporting_strategies: list[Dict[str, Any]]
    expected_outcome: str
    measurement_plan: Dict[str, Any]
    timeline: Dict[str, Any]
    risks: list[str]


# ── In-Memory Store (Replace with DB in production) ───────────── #

# Store for intake contexts and diagnoses
_intake_store: Dict[str, Dict[str, Any]] = {}
_diagnosis_store: Dict[str, Dict[str, Any]] = {}


# ── API Endpoints ─────────────────────────────────────────────── #

@router.post("/intake", response_model=Dict[str, str])
async def submit_business_intake(
    request: BusinessIntakeRequest,
    current_user = Depends(get_current_user)
):
    """
    Submit initial business context for diagnosis.
    
    Creates a business profile that can be used for diagnostics and strategy.
    """
    # Validate business model exists
    model = registry.get(request.business_model)
    if not model:
        available = registry.list_models()
        raise HTTPException(
            status_code=400,
            detail=f"Unknown business model: {request.business_model}. Available: {available}"
        )
    
    # Create business context
    business_id = f"biz_{current_user.tenant_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    context = BusinessContext(
        business_model=request.business_model,
        stage=BusinessStage(request.stage),
        goals=request.goals,
        resources=ResourceConstraints(
            available_hours=request.available_hours,
            available_budget=request.available_budget,
            team_size=request.team_size,
            available_skills=request.skills
        ),
        current_metrics=request.current_metrics,
        channels=request.channels,
        notes=request.notes
    )
    
    # Store (replace with DB in production)
    _intake_store[business_id] = {
        "context": context,
        "user_id": current_user.id,
        "tenant_id": current_user.tenant_id,
        "created_at": datetime.utcnow()
    }
    
    # Emit to Ledger EventStream (audit trail)
    event_stream = get_event_stream()
    if event_stream:
        await event_stream.emit(GovernanceEvent(
            event_id=GovernanceEvent.generate_id(),
            trace_id=get_tracer().start_trace() if get_tracer() else None,
            timestamp=datetime.utcnow(),
            event_type=EventType.DECISION,
            agent_id="system",
            business_id=current_user.tenant_id or 0,
            action="business_intake",
            resource=f"business:{business_id}",
            risk_level="safe",
            decision="recorded",
            reasoning=f"Intake recorded for {model.display_name}",
            metadata={
                "business_model": request.business_model,
                "stage": request.stage,
                "goals": request.goals
            }
        ))
    
    return {
        "business_id": business_id,
        "message": f"Intake recorded for {model.display_name}",
        "next_step": f"POST /diagnostics/run with business_id to start diagnosis"
    }


@router.get("/models")
async def list_business_models():
    """List all available business models"""
    return {
        "models": registry.list_models()
    }


@router.post("/run", response_model=DiagnosisResponse)
async def run_diagnosis(
    business_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Run full diagnostic on a business.
    
    Analyzes all diagnostic checks for the business model and returns
    ranked bottlenecks with health score.
    """
    # Get stored context
    intake = _intake_store.get(business_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Business ID not found")
    
    # Verify ownership
    if intake["tenant_id"] != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    context = intake["context"]
    
    # Get business model
    model = registry.get(context.business_model)
    if not model:
        raise HTTPException(status_code=500, detail="Business model not found")
    
    # Run diagnosis
    trace_id = get_tracer().start_trace() if get_tracer() else None
    start_time = datetime.utcnow()
    
    try:
        diagnosis = await model.diagnose(context)
    except Exception as e:
        # Emit failure event
        event_stream = get_event_stream()
        if event_stream:
            await event_stream.emit(GovernanceEvent(
                event_id=GovernanceEvent.generate_id(),
                trace_id=trace_id,
                timestamp=datetime.utcnow(),
                event_type=EventType.FAILURE,
                agent_id="nova",
                business_id=current_user.tenant_id or 0,
                action="diagnose",
                resource=f"business:{business_id}",
                risk_level="medium",
                decision="failed",
                reasoning=str(e),
                latency_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                metadata={"error": str(e)}
            ))
        raise HTTPException(status_code=500, detail=f"Diagnosis failed: {str(e)}")
    
    # Calculate latency
    latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    # Store result
    diagnosis_id = f"diag_{business_id}"
    _diagnosis_store[diagnosis_id] = {
        "diagnosis": diagnosis,
        "business_id": business_id,
        "user_id": current_user.id,
        "tenant_id": current_user.tenant_id,
        "created_at": datetime.utcnow()
    }
    
    # Emit success event to Ledger
    event_stream = get_event_stream()
    if event_stream:
        await event_stream.emit(GovernanceEvent(
            event_id=GovernanceEvent.generate_id(),
            trace_id=trace_id,
            timestamp=datetime.utcnow(),
            event_type=EventType.ACTION,
            agent_id="nova",
            business_id=current_user.tenant_id or 0,
            action="diagnose",
            resource=f"business:{business_id}",
            risk_level="safe",
            decision="completed",
            reasoning=f"Health score: {diagnosis.health_score:.1%}, Primary: {diagnosis.primary_bottleneck.category.value if diagnosis.primary_bottleneck else 'none'}",
            latency_ms=latency_ms,
            metadata={
                "health_score": diagnosis.health_score,
                "primary_bottleneck": diagnosis.primary_bottleneck.category.value if diagnosis.primary_bottleneck else None,
                "severity": diagnosis.primary_bottleneck.severity.value if diagnosis.primary_bottleneck else None
            }
        ))
        if get_tracer():
            get_tracer().end_trace()
    
    # Format response
    return DiagnosisResponse(
        diagnosis_id=diagnosis_id,
        business_model=diagnosis.business_model,
        health_score=diagnosis.health_score,
        primary_bottleneck={
            "category": diagnosis.primary_bottleneck.category.value,
            "severity": diagnosis.primary_bottleneck.severity.value,
            "description": diagnosis.primary_bottleneck.description,
            "impact": diagnosis.primary_bottleneck.impact
        } if diagnosis.primary_bottleneck else None,
        secondary_bottlenecks=[
            {
                "category": b.category.value,
                "severity": b.severity.value,
                "description": b.description
            }
            for b in diagnosis.secondary_bottlenecks
        ],
        timestamp=diagnosis.timestamp,
        recommendations_summary=f"Primary focus: {diagnosis.primary_bottleneck.category.value if diagnosis.primary_bottleneck else 'None identified'}"
    )


@router.get("/{diagnosis_id}")
async def get_diagnosis(
    diagnosis_id: str,
    current_user = Depends(get_current_user)
):
    """Get full diagnosis results"""
    stored = _diagnosis_store.get(diagnosis_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    if stored["tenant_id"] != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    diagnosis = stored["diagnosis"]
    
    return {
        "diagnosis_id": diagnosis_id,
        "business_id": stored["business_id"],
        "health_score": diagnosis.health_score,
        "primary_bottleneck": {
            "category": diagnosis.primary_bottleneck.category.value,
            "severity": diagnosis.primary_bottleneck.severity.value,
            "description": diagnosis.primary_bottleneck.description,
            "impact": diagnosis.primary_bottleneck.impact,
            "evidence": [
                {
                    "metric": e.metric,
                    "value": e.value,
                    "benchmark": e.benchmark,
                    "gap": e.gap_percentage
                }
                for e in diagnosis.primary_bottleneck.evidence
            ]
        } if diagnosis.primary_bottleneck else None,
        "secondary_bottlenecks": [
            {
                "category": b.category.value,
                "severity": b.severity.value,
                "description": b.description,
                "impact": b.impact
            }
            for b in diagnosis.secondary_bottlenecks
        ],
        "created_at": stored["created_at"]
    }


@router.post("/{diagnosis_id}/strategy", response_model=StrategyResponse)
async def generate_strategy(
    diagnosis_id: str,
    request: StrategyRequest,
    current_user = Depends(get_current_user)
):
    """
    Generate strategy recommendations from a diagnosis.
    
    Matches bottlenecks to strategies filtered by available resources.
    """
    # Get stored diagnosis
    stored = _diagnosis_store.get(diagnosis_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    if stored["tenant_id"] != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    diagnosis = stored["diagnosis"]
    
    # Get business context for resources
    intake = _intake_store.get(stored["business_id"])
    if not intake:
        raise HTTPException(status_code=500, detail="Business context not found")
    
    # Get model and generate strategy
    model = registry.get(diagnosis.business_model)
    if not model:
        raise HTTPException(status_code=500, detail="Business model not found")
    
    try:
        recommendation = await model.recommend_strategies(
            diagnosis,
            intake["context"].resources
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategy generation failed: {str(e)}")
    
    # Format response
    strategy_id = f"strat_{diagnosis_id}"
    
    # Emit strategy generation event
    event_stream = get_event_stream()
    if event_stream:
        await event_stream.emit(GovernanceEvent(
            event_id=GovernanceEvent.generate_id(),
            timestamp=datetime.utcnow(),
            event_type=EventType.ACTION,
            agent_id="forge",
            business_id=current_user.tenant_id or 0,
            action="generate_strategy",
            resource=f"diagnosis:{diagnosis_id}",
            risk_level="medium",
            decision="completed",
            reasoning=f"Generated strategy: {recommendation.primary_strategy.name if recommendation.primary_strategy else 'none'}",
            metadata={
                "strategy_id": strategy_id,
                "primary_strategy": recommendation.primary_strategy.name if recommendation.primary_strategy else None,
                "effort_hours": recommendation.primary_strategy.effort_hours if recommendation.primary_strategy else 0,
                "budget_required": recommendation.primary_strategy.budget_required if recommendation.primary_strategy else 0
            }
        ))
    
    return StrategyResponse(
        strategy_id=strategy_id,
        primary_strategy={
            "name": recommendation.primary_strategy.name,
            "description": recommendation.primary_strategy.description,
            "effort_hours": recommendation.primary_strategy.effort_hours,
            "budget_required": recommendation.primary_strategy.budget_required,
            "expected_impact": recommendation.primary_strategy.expected_impact,
            "steps": recommendation.primary_strategy.steps[:5]  # First 5 steps
        } if recommendation.primary_strategy else None,
        supporting_strategies=[
            {
                "name": s.name,
                "description": s.description,
                "effort_hours": s.effort_hours,
                "expected_impact": s.expected_impact
            }
            for s in recommendation.supporting_strategies[:request.max_strategies-1]
        ],
        expected_outcome=recommendation.expected_outcome,
        measurement_plan=recommendation.measurement_plan,
        timeline=recommendation.timeline,
        risks=recommendation.risks
    )


@router.post("/{diagnosis_id}/approve")
async def approve_strategy(
    diagnosis_id: str,
    current_user = Depends(require_roles(["operator", "governor", "admin"]))
):
    """
    Approve a strategy for execution.
    
    Required before any actions can be taken through Channel Registry.
    """
    # Get stored diagnosis
    stored = _diagnosis_store.get(diagnosis_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    if stored["tenant_id"] != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Mark as approved
    stored["approved"] = True
    stored["approved_by"] = current_user.id
    stored["approved_at"] = datetime.utcnow()
    
    # Get strategy info for event
    primary_strategy = "unknown"
    if stored.get("diagnosis") and stored["diagnosis"].primary_bottleneck:
        primary_strategy = stored["diagnosis"].primary_bottleneck.category.value
    
    # Emit approval event to Ledger
    event_stream = get_event_stream()
    if event_stream:
        await event_stream.emit(GovernanceEvent(
            event_id=GovernanceEvent.generate_id(),
            timestamp=datetime.utcnow(),
            event_type=EventType.APPROVAL,
            agent_id=current_user.id,
            business_id=current_user.tenant_id or 0,
            action="approve_strategy",
            resource=f"diagnosis:{diagnosis_id}",
            risk_level="critical",  # Approvals are critical events
            decision="approved",
            reasoning=f"Strategy approved by {current_user.role if hasattr(current_user, 'role') else 'operator'} for execution",
            metadata={
                "diagnosis_id": diagnosis_id,
                "approved_by": current_user.id,
                "primary_strategy": primary_strategy,
                "role": current_user.role if hasattr(current_user, 'role') else 'operator'
            }
        ))
    
    return {
        "diagnosis_id": diagnosis_id,
        "status": "approved",
        "approved_by": current_user.id,
        "approved_at": stored["approved_at"],
        "next_step": "Strategies can now be executed through Channel Registry"
    }


@router.get("/{diagnosis_id}/events")
async def get_diagnostic_events(
    diagnosis_id: str,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """
    Get audit events for a specific diagnosis.
    
    Queries the Ledger EventStream for all events related to this diagnosis:
    - intake events
    - diagnosis run events
    - strategy generation events
    - approval events
    """
    stored = _diagnosis_store.get(diagnosis_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    if stored["tenant_id"] != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    event_stream = get_event_stream()
    if not event_stream:
        return {
            "diagnosis_id": diagnosis_id,
            "events": [],
            "note": "EventStream not available - audit trail disabled"
        }
    
    # Query events related to this diagnosis
    # Note: This is a simplified query - in production you'd filter by resource pattern
    all_events = event_stream.query(
        business_id=current_user.tenant_id,
        limit=limit * 2  # Get more and filter
    )
    
    # Filter to events related to this diagnosis
    prefix = f"diagnosis:{diagnosis_id}"
    related_events = [
        e for e in all_events
        if e.resource.startswith(prefix) or 
           (e.metadata and e.metadata.get("diagnosis_id") == diagnosis_id)
    ]
    
    return {
        "diagnosis_id": diagnosis_id,
        "event_count": len(related_events),
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "type": e.event_type.value,
                "agent_id": e.agent_id,
                "action": e.action,
                "resource": e.resource,
                "decision": e.decision,
                "reasoning": e.reasoning,
                "risk_level": e.risk_level,
                "latency_ms": e.latency_ms
            }
            for e in related_events[:limit]
        ]
    }
