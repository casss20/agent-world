"""
test_diagnostic_end_to_end.py — Agent World

End-to-end test for the business diagnosis workflow.
Tests: Intake → Diagnosis → Strategy → Approval
"""

import asyncio
import pytest
from datetime import datetime

from business_models import (
    BusinessContext, ResourceConstraints, BusinessStage, 
    registry, EtsyPODModel
)


@pytest.fixture
def sample_etsy_context():
    """Sample Etsy POD business context"""
    return BusinessContext(
        business_model="etsy_pod",
        stage=BusinessStage.TRACTION,
        goals={
            "revenue_target": 5000,
            "audience_target": "1000 customers",
            "timeline": "90_days"
        },
        resources=ResourceConstraints(
            available_hours=15,
            available_budget=800,
            team_size=1,
            available_skills=["design", "copywriting"]
        ),
        current_metrics={
            "listing_count": 12,
            "revenue": 1200,
            "click_through_rate": 0.015,  # 1.5% - below benchmark
            "conversion_rate": 0.008,     # 0.8% - below benchmark
            "favorites_per_view": 0.04,   # 4% - below benchmark
            "primary_niche": "pet_memorial_gifts",
            "competitor_listings": 15000,
            "printify_connected": True,
            "avg_production_days": 4
        },
        channels=["etsy"],
        notes="Struggling with visibility and conversion. Low CTR on listings."
    )


@pytest.mark.asyncio
async def test_etsy_model_registration():
    """Test that Etsy model is registered"""
    model = registry.get("etsy_pod")
    assert model is not None
    assert model.model_id == "etsy_pod"
    assert model.display_name == "Etsy Print-on-Demand"


@pytest.mark.asyncio
async def test_listing_quality_check(sample_etsy_context):
    """Test listing quality diagnostic check"""
    model = EtsyPODModel()
    
    # Find the listing quality check
    listing_check = None
    for check in model.diagnostic_checks:
        if check.name == "Listing Quality Assessment":
            listing_check = check
            break
    
    assert listing_check is not None
    
    # Run the check
    result = await listing_check.run(sample_etsy_context)
    
    # With low CTR (1.5% vs 3% benchmark), should be HIGH or CRITICAL
    assert result.status.value in ["high", "critical"]
    assert result.category.value == "conversion"
    assert len(result.evidence) > 0
    
    # Check that CTR evidence exists
    ctr_evidence = [e for e in result.evidence if e.metric == "click_through_rate"]
    assert len(ctr_evidence) > 0
    assert ctr_evidence[0].value == 0.015


@pytest.mark.asyncio
async def test_full_diagnosis_flow(sample_etsy_context):
    """Test complete diagnosis flow"""
    model = registry.get("etsy_pod")
    
    # Run diagnosis
    diagnosis = await model.diagnose(sample_etsy_context)
    
    # Assertions
    assert diagnosis.business_model == "etsy_pod"
    assert diagnosis.health_score is not None
    assert 0.0 <= diagnosis.health_score <= 1.0
    
    # With poor metrics, should have a primary bottleneck
    assert diagnosis.primary_bottleneck is not None
    assert diagnosis.primary_bottleneck.category is not None
    assert diagnosis.primary_bottleneck.severity is not None
    
    # Should have evidence
    assert len(diagnosis.primary_bottleneck.evidence) > 0
    
    print(f"\nDiagnosis Results:")
    print(f"  Health Score: {diagnosis.health_score:.1%}")
    print(f"  Primary Bottleneck: {diagnosis.primary_bottleneck.category.value}")
    print(f"  Severity: {diagnosis.primary_bottleneck.severity.value}")
    print(f"  Description: {diagnosis.primary_bottleneck.description}")


@pytest.mark.asyncio
async def test_strategy_recommendation(sample_etsy_context):
    """Test strategy generation from diagnosis"""
    model = registry.get("etsy_pod")
    
    # First diagnose
    diagnosis = await model.diagnose(sample_etsy_context)
    
    # Then get strategy
    strategy = await model.recommend_strategies(
        diagnosis,
        sample_etsy_context.resources
    )
    
    # Assertions
    assert strategy is not None
    
    # Should have a primary strategy
    if diagnosis.primary_bottleneck:
        assert strategy.primary_strategy is not None
        assert strategy.primary_strategy.name is not None
        assert strategy.primary_strategy.description is not None
        assert strategy.primary_strategy.steps is not None
        
        print(f"\nStrategy Recommendation:")
        print(f"  Primary: {strategy.primary_strategy.name}")
        print(f"  Effort: {strategy.primary_strategy.effort_hours}h")
        print(f"  Budget: ${strategy.primary_strategy.budget_required}")
        print(f"  Expected: {strategy.primary_strategy.expected_impact}")
    
    # Should have expected outcome
    assert strategy.expected_outcome is not None
    
    # Should have timeline
    assert strategy.timeline is not None


@pytest.mark.asyncio
async def test_strategy_filters_by_resources():
    """Test that strategies are filtered by available resources"""
    
    # Context with very limited resources
    limited_context = BusinessContext(
        business_model="etsy_pod",
        stage=BusinessStage.TRACTION,
        goals={"revenue_target": 1000},
        resources=ResourceConstraints(
            available_hours=5,       # Only 5 hours/week
            available_budget=100,  # Only $100/month
            team_size=1,
            available_skills=[]      # No specific skills
        ),
        current_metrics={
            "listing_count": 5,
            "click_through_rate": 0.01,
            "conversion_rate": 0.005
        },
        channels=["etsy"]
    )
    
    model = registry.get("etsy_pod")
    diagnosis = await model.diagnose(limited_context)
    strategy = await model.recommend_strategies(diagnosis, limited_context.resources)
    
    # Should still get a strategy, but it should be low-effort
    if strategy.primary_strategy:
        assert strategy.primary_strategy.effort_hours <= 20  # Within 4x weekly hours
        assert strategy.primary_strategy.budget_required <= 100


@pytest.mark.asyncio
async def test_kpi_definitions():
    """Test that KPIs are defined for Etsy POD"""
    model = registry.get("etsy_pod")
    kpis = model.get_kpis()
    
    assert len(kpis) > 0
    
    # Check for expected KPIs
    kpi_names = [k.name for k in kpis]
    assert "Revenue" in kpi_names
    assert "Conversion Rate" in kpi_names
    assert "Click-Through Rate" in kpi_names
    
    print(f"\nDefined KPIs: {len(kpis)}")
    for kpi in kpis[:5]:
        print(f"  - {kpi.name} ({kpi.frequency})")


def test_model_listing():
    """Test that models can be listed"""
    models = registry.list_models()
    
    assert len(models) > 0
    
    etsy_model = [m for m in models if m["id"] == "etsy_pod"]
    assert len(etsy_model) == 1
    assert etsy_model[0]["name"] == "Etsy Print-on-Demand"


if __name__ == "__main__":
    # Run tests manually
    print("Running diagnostic end-to-end tests...\n")
    
    asyncio.run(test_etsy_model_registration())
    print("✓ Model registration test passed")
    
    context = sample_etsy_context()
    asyncio.run(test_listing_quality_check(context))
    print("✓ Listing quality check test passed")
    
    asyncio.run(test_full_diagnosis_flow(context))
    print("✓ Full diagnosis flow test passed")
    
    asyncio.run(test_strategy_recommendation(context))
    print("✓ Strategy recommendation test passed")
    
    asyncio.run(test_strategy_filters_by_resources())
    print("✓ Resource filtering test passed")
    
    asyncio.run(test_kpi_definitions())
    print("✓ KPI definitions test passed")
    
    test_model_listing()
    print("✓ Model listing test passed")
    
    print("\n🎉 All tests passed!")
