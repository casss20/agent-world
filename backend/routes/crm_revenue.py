"""
CRM Revenue Routes
API endpoints for CRM agent revenue integration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from services.crm_revenue_service import get_crm_revenue_service

router = APIRouter(prefix="/api/agents/crm", tags=["crm-revenue"])


@router.get("/revenue/summary", response_model=dict)
async def get_revenue_summary(
    period: str = "30d",
    db: AsyncSession = Depends(get_db),
):
    """Get revenue summary for CRM reporting."""
    service = get_crm_revenue_service()
    return await service.get_revenue_summary(db, period)


@router.get("/revenue/campaigns/health", response_model=dict)
async def get_campaign_health(
    campaign_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Check campaign health — CRM monitors and reports to leadership."""
    service = get_crm_revenue_service()
    return await service.get_campaign_health(db, campaign_id)


@router.get("/revenue/customer/{customer_id}", response_model=dict)
async def get_customer_revenue_report(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate revenue report for a specific customer."""
    service = get_crm_revenue_service()
    return await service.generate_customer_revenue_report(db, customer_id)


@router.get("/revenue/alert", response_model=dict)
async def check_revenue_alert(
    threshold: float = 1000.0,
    period: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    """Check if revenue is below threshold — CRM alerts if needed."""
    service = get_crm_revenue_service()
    return await service.alert_revenue_threshold(db, threshold, period)
