"""
Revenue Metrics Exporter
Phase 5 Ticket 1: Revenue Dashboard

Exposes revenue metrics to Prometheus for Grafana dashboard
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import aioredis
except ImportError:
    aioredis = None


class RevenueMetricsExporter:
    """
    Export revenue metrics for Prometheus/Grafana
    
    Metrics exposed:
    - revenue_total_usd: Total revenue from all campaigns
    - revenue_affiliate_usd: Affiliate revenue
    - revenue_cost_usd: Total costs
    - revenue_cpa_usd: Cost per acquisition
    - revenue_roas: Return on ad spend
    - campaigns_live: Number of active campaigns
    - campaigns_total: Total campaigns
    - campaign_impressions_total: Total impressions
    - campaign_clicks_total: Total clicks
    - campaign_conversions_total: Total conversions
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.metrics_cache: Dict[str, Any] = {}
        self.last_update = None
    
    async def update_metrics(self, tracker):
        """Update metrics from revenue tracker"""
        dashboard = tracker.get_dashboard()
        by_source = tracker.get_metrics_by_source()
        by_platform = tracker.get_metrics_by_publish_platform()
        
        metrics = {
            # Core revenue metrics
            "revenue_total_usd": dashboard.total_revenue,
            "revenue_affiliate_usd": dashboard.total_affiliate_revenue,
            "revenue_cost_usd": dashboard.total_cost,
            "revenue_profit_usd": dashboard.total_profit,
            
            # KPIs
            "revenue_cpa_usd": dashboard.overall_cpa,
            "revenue_roas": dashboard.overall_roas,
            "revenue_ctr": dashboard.overall_ctr,
            
            # Campaign counts
            "campaigns_live": dashboard.campaigns_live,
            "campaigns_completed": dashboard.campaigns_completed,
            "campaigns_total": dashboard.campaigns_total,
            
            # Engagement metrics
            "campaign_impressions_total": dashboard.total_impressions,
            "campaign_clicks_total": dashboard.total_clicks,
            "campaign_conversions_total": dashboard.total_conversions,
        }
        
        # Add source breakdown
        for source, data in by_source.items():
            metrics[f"revenue_by_source{{source=\"{source}\"}}"] = data["revenue"]
            metrics[f"cost_by_source{{source=\"{source}\"}}"] = data["cost"]
            metrics[f"roas_by_source{{source=\"{source}\"}}"] = data["roas"]
        
        # Add platform breakdown
        for platform, data in by_platform.items():
            metrics[f"revenue_by_platform{{platform=\"{platform}\"}}"] = data["revenue"]
            metrics[f"cost_by_platform{{platform=\"{platform}\"}}"] = data["cost"]
            metrics[f"roas_by_platform{{platform=\"{platform}\"}}"] = data["roas"]
        
        self.metrics_cache = metrics
        self.last_update = datetime.now().isoformat()
        
        # Store in Redis for persistence
        if self.redis:
            await self.redis.hset("revenue:metrics", mapping={k: str(v) for k, v in metrics.items()})
            await self.redis.set("revenue:last_update", self.last_update)
        
        return metrics
    
    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        lines.append("# HELP revenue_total_usd Total revenue from all campaigns")
        lines.append("# TYPE revenue_total_usd gauge")
        lines.append(f"revenue_total_usd {self.metrics_cache.get('revenue_total_usd', 0)}")
        
        lines.append("# HELP revenue_affiliate_usd Affiliate revenue")
        lines.append("# TYPE revenue_affiliate_usd gauge")
        lines.append(f"revenue_affiliate_usd {self.metrics_cache.get('revenue_affiliate_usd', 0)}")
        
        lines.append("# HELP revenue_cost_usd Total costs")
        lines.append("# TYPE revenue_cost_usd gauge")
        lines.append(f"revenue_cost_usd {self.metrics_cache.get('revenue_cost_usd', 0)}")
        
        lines.append("# HELP revenue_profit_usd Total profit")
        lines.append("# TYPE revenue_profit_usd gauge")
        lines.append(f"revenue_profit_usd {self.metrics_cache.get('revenue_profit_usd', 0)}")
        
        lines.append("# HELP revenue_cpa_usd Cost per acquisition")
        lines.append("# TYPE revenue_cpa_usd gauge")
        lines.append(f"revenue_cpa_usd {self.metrics_cache.get('revenue_cpa_usd', 0)}")
        
        lines.append("# HELP revenue_roas Return on ad spend")
        lines.append("# TYPE revenue_roas gauge")
        lines.append(f"revenue_roas {self.metrics_cache.get('revenue_roas', 0)}")
        
        lines.append("# HELP revenue_ctr Click-through rate")
        lines.append("# TYPE revenue_ctr gauge")
        lines.append(f"revenue_ctr {self.metrics_cache.get('revenue_ctr', 0)}")
        
        lines.append("# HELP campaigns_live Number of active campaigns")
        lines.append("# TYPE campaigns_live gauge")
        lines.append(f"campaigns_live {self.metrics_cache.get('campaigns_live', 0)}")
        
        lines.append("# HELP campaigns_total Total number of campaigns")
        lines.append("# TYPE campaigns_total gauge")
        lines.append(f"campaigns_total {self.metrics_cache.get('campaigns_total', 0)}")
        
        lines.append("# HELP campaign_impressions_total Total impressions")
        lines.append("# TYPE campaign_impressions_total counter")
        lines.append(f"campaign_impressions_total {self.metrics_cache.get('campaign_impressions_total', 0)}")
        
        lines.append("# HELP campaign_clicks_total Total clicks")
        lines.append("# TYPE campaign_clicks_total counter")
        lines.append(f"campaign_clicks_total {self.metrics_cache.get('campaign_clicks_total', 0)}")
        
        lines.append("# HELP campaign_conversions_total Total conversions")
        lines.append("# TYPE campaign_conversions_total counter")
        lines.append(f"campaign_conversions_total {self.metrics_cache.get('campaign_conversions_total', 0)}")
        
        # Source breakdown
        lines.append("# HELP revenue_by_source Revenue by source platform")
        lines.append("# TYPE revenue_by_source gauge")
        for key, value in self.metrics_cache.items():
            if key.startswith("revenue_by_source"):
                lines.append(f"{key} {value}")
        
        # Platform breakdown
        lines.append("# HELP revenue_by_platform Revenue by publish platform")
        lines.append("# TYPE revenue_by_platform gauge")
        for key, value in self.metrics_cache.items():
            if key.startswith("revenue_by_platform"):
                lines.append(f"{key} {value}")
        
        return "\n".join(lines)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for API/dashboard"""
        return {
            "metrics": self.metrics_cache,
            "last_update": self.last_update,
            "targets": {
                "monthly_revenue": 10000,
                "current_month": sum(v for k, v in self.metrics_cache.items() if "revenue" in k and isinstance(v, (int, float))),
            }
        }


# FastAPI endpoint for revenue metrics
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

revenue_router = APIRouter(prefix="/revenue", tags=["revenue"])

# Global exporter instance
_revenue_exporter: Optional[RevenueMetricsExporter] = None
_revenue_tracker = None


def init_revenue_metrics(redis_client, tracker):
    """Initialize revenue metrics"""
    global _revenue_exporter, _revenue_tracker
    _revenue_exporter = RevenueMetricsExporter(redis_client)
    _revenue_tracker = tracker


@revenue_router.get("/metrics", response_class=PlainTextResponse)
async def get_revenue_metrics():
    """Prometheus-compatible metrics endpoint"""
    if _revenue_exporter and _revenue_tracker:
        await _revenue_exporter.update_metrics(_revenue_tracker)
        return _revenue_exporter.get_prometheus_metrics()
    return "# No revenue data available"


@revenue_router.get("/dashboard")
async def get_revenue_dashboard():
    """Revenue dashboard data"""
    if _revenue_exporter:
        return _revenue_exporter.get_dashboard_data()
    return {"error": "Revenue metrics not initialized"}


@revenue_router.get("/campaigns")
async def list_campaigns():
    """List all revenue campaigns"""
    if _revenue_tracker:
        campaigns = [c.to_dict() for c in _revenue_tracker.campaigns.values()]
        return {"campaigns": campaigns, "count": len(campaigns)}
    return {"campaigns": [], "count": 0}


@revenue_router.post("/campaigns/{campaign_id}/metrics")
async def update_campaign_metrics(campaign_id: str, metrics: Dict[str, Any]):
    """Update campaign metrics"""
    if _revenue_tracker:
        _revenue_tracker.update_campaign_metrics(campaign_id, **metrics)
        return {"status": "updated", "campaign_id": campaign_id}
    return {"error": "Revenue tracker not initialized"}
