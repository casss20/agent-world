"""
revenue_routes.py — Agent World

Revenue tracking API: Sales, ad spend, ROAS, campaign performance.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from revenue_models import (
    RevenueTransaction, AdSpendTransaction, CampaignPerformance,
    RevenueSyncLog, RevenueGoal
)
from models import get_db
from ledger_client import require_capability

router = APIRouter(prefix="/revenue", tags=["revenue"])


# ============ API Models ============

class RevenueSummary(BaseModel):
    period: str  # today, 7d, 30d, custom
    total_revenue: float
    total_ad_spend: float
    roas: float
    net_profit: float
    orders: int
    
    # Breakdown
    by_channel: dict
    by_campaign: list


class CampaignMetrics(BaseModel):
    campaign_id: str
    campaign_name: str
    platform: str
    spend: float
    revenue: float
    roas: float
    orders: int
    cpa: float
    status: str  # active, paused, scaled


class RecordSaleRequest(BaseModel):
    channel: str
    order_id: str
    product_id: str
    product_name: str
    gross_revenue: float
    platform_fee: float = 0
    payment_fee: float = 0
    currency: str = "USD"
    campaign_id: Optional[str] = None
    transaction_time: Optional[datetime] = None


class RecordAdSpendRequest(BaseModel):
    platform: str
    campaign_id: str
    campaign_name: str
    spend: float
    impressions: int = 0
    clicks: int = 0
    currency: str = "USD"
    transaction_time: Optional[datetime] = None


class ROASAlert(BaseModel):
    campaign_id: str
    campaign_name: str
    roas: float
    threshold: float
    severity: str  # warning (ROAS < 1.0), critical (ROAS < 0.5)
    recommendation: str


# ============ Routes ============

@router.get("/summary", response_model=RevenueSummary)
def get_revenue_summary(
    period: str = Query("7d", enum=["today", "7d", "30d", "custom"]),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    business_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get revenue summary for dashboard"""
    # Calculate date range
    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0)
        end = now
    elif period == "7d":
        start = now - timedelta(days=7)
        end = now
    elif period == "30d":
        start = now - timedelta(days=30)
        end = now
    
    # Query revenue
    revenue_query = db.query(
        func.sum(RevenueTransaction.net_revenue).label("total"),
        func.count(RevenueTransaction.id).label("orders")
    ).filter(
        RevenueTransaction.business_id == business_id,
        RevenueTransaction.transaction_time >= start,
        RevenueTransaction.transaction_time <= end
    ).first()
    
    # Query ad spend
    spend_query = db.query(
        func.sum(AdSpendTransaction.spend).label("total")
    ).filter(
        AdSpendTransaction.business_id == business_id,
        AdSpendTransaction.transaction_time >= start,
        AdSpendTransaction.transaction_time <= end
    ).first()
    
    total_revenue = revenue_query.total or 0
    total_spend = spend_query.total or 0
    orders = revenue_query.orders or 0
    
    # Calculate ROAS
    roas = total_revenue / total_spend if total_spend > 0 else 0
    
    # Channel breakdown
    channel_breakdown = db.query(
        RevenueTransaction.channel,
        func.sum(RevenueTransaction.net_revenue).label("revenue"),
        func.count(RevenueTransaction.id).label("orders")
    ).filter(
        RevenueTransaction.business_id == business_id,
        RevenueTransaction.transaction_time >= start,
        RevenueTransaction.transaction_time <= end
    ).group_by(RevenueTransaction.channel).all()
    
    by_channel = {
        row.channel: {"revenue": row.revenue, "orders": row.orders}
        for row in channel_breakdown
    }
    
    # Campaign performance (top 10)
    campaign_data = db.query(CampaignPerformance).filter(
        CampaignPerformance.business_id == business_id,
        CampaignPerformance.date >= start,
        CampaignPerformance.date <= end
    ).order_by(CampaignPerformance.revenue_attributed.desc()).limit(10).all()
    
    by_campaign = [
        CampaignMetrics(
            campaign_id=c.campaign_id,
            campaign_name=c.campaign_name,
            platform=c.platform,
            spend=c.ad_spend,
            revenue=c.revenue_attributed,
            roas=c.roas,
            orders=c.orders_attributed,
            cpa=c.cpa,
            status="active" if c.roas > 1.5 else "paused" if c.roas < 0.5 else "maintained"
        ) for c in campaign_data
    ]
    
    return RevenueSummary(
        period=period,
        total_revenue=total_revenue,
        total_ad_spend=total_spend,
        roas=roas,
        net_profit=total_revenue - total_spend,
        orders=orders,
        by_channel=by_channel,
        by_campaign=by_campaign
    )


@router.get("/campaigns", response_model=List[CampaignMetrics])
def get_campaigns(
    status: Optional[str] = Query(None, enum=["active", "paused", "scaled", "all"]),
    min_roas: Optional[float] = None,
    max_roas: Optional[float] = None,
    business_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get all campaigns with filters"""
    query = db.query(CampaignPerformance).filter(
        CampaignPerformance.business_id == business_id
    )
    
    if status and status != "all":
        if status == "active":
            query = query.filter(CampaignPerformance.roas >= 1.0)
        elif status == "paused":
            query = query.filter(CampaignPerformance.roas < 0.5)
        elif status == "scaled":
            query = query.filter(CampaignPerformance.roas >= 2.5)
    
    if min_roas is not None:
        query = query.filter(CampaignPerformance.roas >= min_roas)
    
    if max_roas is not None:
        query = query.filter(CampaignPerformance.roas <= max_roas)
    
    campaigns = query.order_by(CampaignPerformance.roas.desc()).all()
    
    return [
        CampaignMetrics(
            campaign_id=c.campaign_id,
            campaign_name=c.campaign_name,
            platform=c.platform,
            spend=c.ad_spend,
            revenue=c.revenue_attributed,
            roas=c.roas,
            orders=c.orders_attributed,
            cpa=c.cpa,
            status="active" if c.roas > 1.5 else "paused" if c.roas < 0.5 else "maintained"
        ) for c in campaigns
    ]


@router.get("/alerts")
def get_roas_alerts(business_id: int = Query(...), db: Session = Depends(get_db)):
    """Get campaigns that need attention (low ROAS)"""
    alerts = []
    
    # Critical: ROAS < 0.5 (losing money fast)
    critical = db.query(CampaignPerformance).filter(
        CampaignPerformance.business_id == business_id,
        CampaignPerformance.roas < 0.5,
        CampaignPerformance.ad_spend > 10  # Minimum spend to matter
    ).all()
    
    for c in critical:
        alerts.append(ROASAlert(
            campaign_id=c.campaign_id,
            campaign_name=c.campaign_name,
            roas=c.roas,
            threshold=0.5,
            severity="critical",
            recommendation=f"Pause immediately — losing ${c.ad_spend - c.revenue_attributed:.2f}"
        ))
    
    # Warning: ROAS < 1.0 (not profitable)
    warning = db.query(CampaignPerformance).filter(
        CampaignPerformance.business_id == business_id,
        CampaignPerformance.roas >= 0.5,
        CampaignPerformance.roas < 1.0,
        CampaignPerformance.ad_spend > 10
    ).all()
    
    for c in warning:
        alerts.append(ROASAlert(
            campaign_id=c.campaign_id,
            campaign_name=c.campaign_name,
            roas=c.roas,
            threshold=1.0,
            severity="warning",
            recommendation="Review targeting or creative — break-even needed"
        ))
    
    return {"alerts": alerts, "total": len(alerts)}


@router.post("/record-sale")
def record_sale(
    request: RecordSaleRequest,
    business_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Record a sale (from Merchant agent or webhook)"""
    # Calculate net revenue
    net = request.gross_revenue - request.platform_fee - request.payment_fee
    
    transaction = RevenueTransaction(
        business_id=business_id,
        tenant_id=str(business_id),  # Simplified — real impl uses JWT
        channel=request.channel,
        order_id=request.order_id,
        product_id=request.product_id,
        product_name=request.product_name,
        gross_revenue=request.gross_revenue,
        platform_fee=request.platform_fee,
        payment_fee=request.payment_fee,
        net_revenue=net,
        currency=request.currency,
        campaign_id=request.campaign_id,
        transaction_time=request.transaction_time or datetime.utcnow(),
        synced_from="api"
    )
    
    db.add(transaction)
    db.commit()
    
    # Update campaign performance if attributed
    if request.campaign_id:
        update_campaign_performance(business_id, request.campaign_id, db)
    
    return {
        "success": True,
        "transaction_id": transaction.id,
        "net_revenue": net
    }


@router.post("/record-ad-spend")
def record_ad_spend(
    request: RecordAdSpendRequest,
    business_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Record ad spend (from Promoter agent or API sync)"""
    transaction = AdSpendTransaction(
        business_id=business_id,
        tenant_id=str(business_id),
        platform=request.platform,
        campaign_id=request.campaign_id,
        campaign_name=request.campaign_name,
        spend=request.spend,
        impressions=request.impressions,
        clicks=request.clicks,
        currency=request.currency,
        transaction_time=request.transaction_time or datetime.utcnow(),
        synced_from="api"
    )
    
    db.add(transaction)
    db.commit()
    
    # Update campaign performance
    update_campaign_performance(business_id, request.campaign_id, db)
    
    return {
        "success": True,
        "transaction_id": transaction.id
    }


@router.get("/sync-status")
def get_sync_status(business_id: int = Query(...), db: Session = Depends(get_db)):
    """Get status of external integrations"""
    syncs = db.query(RevenueSyncLog).filter(
        RevenueSyncLog.business_id == business_id
    ).all()
    
    return {
        "integrations": [
            {
                "integration": s.integration,
                "last_sync": s.last_sync_at.isoformat() if s.last_sync_at else None,
                "status": s.status,
                "transactions_synced": s.transactions_synced
            }
            for s in syncs
        ]
    }


# ============ Helper Functions ============

def update_campaign_performance(business_id: int, campaign_id: str, db: Session):
    """Recalculate campaign performance metrics"""
    # Get date range (today)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0)
    
    # Aggregate revenue
    revenue_agg = db.query(
        func.sum(RevenueTransaction.net_revenue).label("revenue"),
        func.count(RevenueTransaction.id).label("orders")
    ).filter(
        RevenueTransaction.business_id == business_id,
        RevenueTransaction.campaign_id == campaign_id,
        RevenueTransaction.transaction_time >= today
    ).first()
    
    # Aggregate spend
    spend_agg = db.query(
        func.sum(AdSpendTransaction.spend).label("spend"),
        func.sum(AdSpendTransaction.impressions).label("impressions"),
        func.sum(AdSpendTransaction.clicks).label("clicks")
    ).filter(
        AdSpendTransaction.business_id == business_id,
        AdSpendTransaction.campaign_id == campaign_id,
        AdSpendTransaction.transaction_time >= today
    ).first()
    
    revenue = revenue_agg.revenue or 0
    orders = revenue_agg.orders or 0
    spend = spend_agg.spend or 0
    impressions = spend_agg.impressions or 0
    clicks = spend_agg.clicks or 0
    
    # Calculate metrics
    roas = revenue / spend if spend > 0 else 0
    cpa = spend / orders if orders > 0 else 0
    aov = revenue / orders if orders > 0 else 0
    ctr = (clicks / impressions * 100) if impressions > 0 else 0
    cpc = spend / clicks if clicks > 0 else 0
    
    # Upsert performance record
    perf = db.query(CampaignPerformance).filter(
        CampaignPerformance.business_id == business_id,
        CampaignPerformance.campaign_id == campaign_id,
        CampaignPerformance.date == today
    ).first()
    
    if not perf:
        # Get campaign details from ad spend
        ad_record = db.query(AdSpendTransaction).filter(
            AdSpendTransaction.campaign_id == campaign_id
        ).first()
        
        perf = CampaignPerformance(
            business_id=business_id,
            tenant_id=str(business_id),
            campaign_id=campaign_id,
            campaign_name=ad_record.campaign_name if ad_record else campaign_id,
            platform=ad_record.platform if ad_record else "unknown",
            date=today,
            granularity="daily"
        )
        db.add(perf)
    
    # Update metrics
    perf.ad_spend = spend
    perf.revenue_attributed = revenue
    perf.orders_attributed = orders
    perf.roas = roas
    perf.cpa = cpa
    perf.aov = aov
    perf.impressions = impressions
    perf.clicks = clicks
    perf.ctr = ctr
    perf.cpc = cpc
    
    # Determine agent action
    if roas >= 2.5:
        perf.agent_action = "scaled"
        perf.agent_reasoning = f"ROAS {roas:.2f} exceeds 2.5 threshold — scaling budget"
    elif roas < 0.5:
        perf.agent_action = "paused"
        perf.agent_reasoning = f"ROAS {roas:.2f} below 0.5 threshold — pausing to prevent losses"
    else:
        perf.agent_action = "maintained"
        perf.agent_reasoning = f"ROAS {roas:.2f} within acceptable range"
    
    db.commit()
