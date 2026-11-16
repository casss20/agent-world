"""
CRM Revenue Integration Service
Connects the CRM agent to the revenue tracking layer.

Allows the CRM agent to:
- Query revenue summaries and campaign performance
- Generate customer revenue reports
- Track monetization opportunities
- Alert on revenue thresholds
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from revenue_models import RevenueTransaction, CampaignPerformance, RevenueGoal
from agents.roles.role_definitions import get_role
from infrastructure.interfaces.base_storage_provider import BaseStorageProvider

logger = logging.getLogger(__name__)


class CRMRevenueService:
    """
    Service for CRM agent to interact with revenue data.
    Acts as the bridge between customer relations and financial metrics.
    """

    def __init__(self, storage_provider: Optional[BaseStorageProvider] = None):
        self.agent_id = "crm"
        self.agent_name = "Casey"
        self.storage_provider = storage_provider

    # ── Revenue Queries ──────────────────────────────────────────────────

    async def get_revenue_summary(
        self,
        db: AsyncSession,
        period: str = "30d",
    ) -> Dict[str, Any]:
        """
        Get revenue summary for the CRM agent to report to leadership.
        period: today, 7d, 30d, 90d
        """
        # Calculate date range
        now = datetime.utcnow()
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "7d":
            start = now - timedelta(days=7)
        elif period == "30d":
            start = now - timedelta(days=30)
        elif period == "90d":
            start = now - timedelta(days=90)
        else:
            start = now - timedelta(days=30)

        # Query revenue transactions
        result = await db.execute(
            select(RevenueTransaction)
            .where(RevenueTransaction.created_at >= start)
            .order_by(desc(RevenueTransaction.created_at))
        )
        transactions = result.scalars().all()

        total_revenue = sum(t.gross_revenue for t in transactions)
        total_fees = sum(t.platform_fee + t.payment_fee for t in transactions)
        net_revenue = total_revenue - total_fees
        order_count = len(transactions)

        # Campaign performance
        campaign_result = await db.execute(
            select(CampaignPerformance)
            .where(CampaignPerformance.updated_at >= start)
            .order_by(desc(CampaignPerformance.roas))
        )
        campaigns = campaign_result.scalars().all()

        top_campaigns = [
            {
                "id": c.campaign_id,
                "name": c.campaign_name,
                "platform": c.platform,
                "spend": c.spend,
                "revenue": c.revenue,
                "roas": c.roas,
                "status": c.status,
            }
            for c in campaigns[:5]
        ]

        return {
            "success": True,
            "period": period,
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "net_revenue": round(net_revenue, 2),
                "total_fees": round(total_fees, 2),
                "orders": order_count,
                "avg_order_value": round(total_revenue / max(order_count, 1), 2),
            },
            "top_campaigns": top_campaigns,
            "reported_by": {
                "agent_id": self.agent_id,
                "name": self.agent_name,
                "role": "CRM",
            },
        }

    async def get_campaign_health(
        self,
        db: AsyncSession,
        campaign_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check health of campaigns. Alert if ROAS drops below thresholds.
        """
        query = select(CampaignPerformance)
        if campaign_id:
            query = query.where(CampaignPerformance.campaign_id == campaign_id)

        result = await db.execute(query.order_by(desc(CampaignPerformance.updated_at)))
        campaigns = result.scalars().all()

        healthy = []
        at_risk = []
        critical = []

        for c in campaigns:
            data = {
                "id": c.campaign_id,
                "name": c.campaign_name,
                "roas": c.roas,
                "spend": c.spend,
                "revenue": c.revenue,
                "status": c.status,
            }
            if c.roas >= 3.0:
                healthy.append(data)
            elif c.roas >= 1.5:
                at_risk.append(data)
            else:
                critical.append(data)

        return {
            "success": True,
            "campaigns_checked": len(campaigns),
            "healthy": healthy,
            "at_risk": at_risk,
            "critical": critical,
            "recommendations": self._generate_recommendations(healthy, at_risk, critical),
        }

    def _generate_recommendations(self, healthy, at_risk, critical) -> List[str]:
        """Generate CRM recommendations based on campaign health."""
        recs = []
        if critical:
            recs.append(f"🚨 {len(critical)} campaigns critical — pause or reallocate budget immediately")
        if at_risk:
            recs.append(f"⚠️ {len(at_risk)} campaigns at risk — review targeting and creative")
        if healthy:
            recs.append(f"✅ {len(healthy)} campaigns healthy — consider scaling budget")
        if not healthy and not at_risk and not critical:
            recs.append("📊 No active campaigns — recommend starting test campaigns")
        return recs

    async def generate_customer_revenue_report(
        self,
        db: AsyncSession,
        customer_id: str,
    ) -> Dict[str, Any]:
        """
        Generate a revenue report for a specific customer.
        CRM uses this for account management and upselling.
        """
        result = await db.execute(
            select(RevenueTransaction)
            .where(RevenueTransaction.customer_id == customer_id)
            .order_by(desc(RevenueTransaction.created_at))
        )
        transactions = result.scalars().all()

        if not transactions:
            return {
                "success": False,
                "error": f"No revenue data for customer {customer_id}",
            }

        lifetime_value = sum(t.gross_revenue for t in transactions)
        avg_order = lifetime_value / len(transactions)
        last_order = transactions[0].created_at if transactions else None

        # Product affinity
        products = {}
        for t in transactions:
            products[t.product_id] = products.get(t.product_id, 0) + t.gross_revenue

        top_products = sorted(products.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "success": True,
            "customer_id": customer_id,
            "lifetime_value": round(lifetime_value, 2),
            "total_orders": len(transactions),
            "avg_order_value": round(avg_order, 2),
            "last_order_date": last_order.isoformat() if last_order else None,
            "top_products": [
                {"product_id": p[0], "revenue": round(p[1], 2)} for p in top_products
            ],
            "recommendations": [
                f"Customer LTV: ${round(lifetime_value, 2)} — {'high value' if lifetime_value > 500 else 'standard'}",
                f"Last order: {last_order.strftime('%Y-%m-%d') if last_order else 'N/A'}",
            ],
        }

    async def alert_revenue_threshold(
        self,
        db: AsyncSession,
        threshold: float = 1000.0,
        period: str = "7d",
    ) -> Dict[str, Any]:
        """
        Check if revenue is below threshold and generate alert.
        CRM escalates to COO if needed.
        """
        summary = await self.get_revenue_summary(db, period)
        net_revenue = summary["summary"]["net_revenue"]

        if net_revenue < threshold:
            return {
                "success": True,
                "alert": True,
                "severity": "high" if net_revenue < threshold * 0.5 else "medium",
                "message": f"Revenue ${net_revenue} below threshold ${threshold} for period {period}",
                "net_revenue": net_revenue,
                "threshold": threshold,
                "period": period,
                "escalation_target": "coo",  # CRM escalates operational to COO
                "recommended_action": "Review campaign performance and customer outreach",
            }

        return {
            "success": True,
            "alert": False,
            "message": f"Revenue ${net_revenue} above threshold ${threshold}",
            "net_revenue": net_revenue,
        }


# ── Singleton ───────────────────────────────────────────────────────────

_crm_revenue_service: Optional[CRMRevenueService] = None


def get_crm_revenue_service() -> CRMRevenueService:
    global _crm_revenue_service
    if _crm_revenue_service is None:
        _crm_revenue_service = CRMRevenueService()
    return _crm_revenue_service
