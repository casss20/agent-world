"""
Revenue Tracking Models and Metrics
Phase 5 Ticket 1: Revenue Dashboard
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class CampaignStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SourcePlatform(str, Enum):
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    PRODUCTHUNT = "producthunt"
    TWITTER = "twitter"


class PublishPlatform(str, Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    MEDIUM = "medium"
    YOUTUBE = "youtube"


@dataclass
class RevenueCampaign:
    """A content arbitrage campaign with revenue tracking"""
    id: str
    name: str
    status: CampaignStatus
    
    # Source (where trend discovered)
    source_platform: SourcePlatform
    source_url: str
    source_engagement: int  # upvotes, likes, etc.
    
    # Content (what was created)
    content_headline: str
    content_body: str
    content_platform: PublishPlatform
    publish_url: Optional[str] = None
    
    # Revenue tracking
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue_usd: float = 0.0
    cost_usd: float = 0.0  # API costs, etc.
    
    # Affiliate tracking
    affiliate_links: List[Dict[str, Any]] = field(default_factory=list)
    affiliate_revenue: float = 0.0
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    published_at: Optional[str] = None
    
    @property
    def cpa(self) -> float:
        """Cost per acquisition"""
        if self.conversions > 0:
            return self.cost_usd / self.conversions
        return 0.0
    
    @property
    def roas(self) -> float:
        """Return on ad spend (revenue / cost)"""
        if self.cost_usd > 0:
            return self.revenue_usd / self.cost_usd
        return 0.0
    
    @property
    def ctr(self) -> float:
        """Click-through rate"""
        if self.impressions > 0:
            return (self.clicks / self.impressions) * 100
        return 0.0
    
    @property
    def conversion_rate(self) -> float:
        """Conversion rate"""
        if self.clicks > 0:
            return (self.conversions / self.clicks) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "source_platform": self.source_platform.value,
            "source_url": self.source_url,
            "source_engagement": self.source_engagement,
            "content_headline": self.content_headline,
            "content_platform": self.content_platform.value,
            "publish_url": self.publish_url,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "revenue_usd": self.revenue_usd,
            "cost_usd": self.cost_usd,
            "affiliate_revenue": self.affiliate_revenue,
            "cpa": self.cpa,
            "roas": self.roas,
            "ctr": self.ctr,
            "conversion_rate": self.conversion_rate,
            "created_at": self.created_at,
            "published_at": self.published_at,
        }


@dataclass
class RevenueDashboard:
    """Aggregated revenue dashboard metrics"""
    
    # Campaign counts
    campaigns_live: int = 0
    campaigns_completed: int = 0
    campaigns_total: int = 0
    
    # Aggregate metrics
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_revenue: float = 0.0
    total_cost: float = 0.0
    total_affiliate_revenue: float = 0.0
    
    # Calculated metrics
    @property
    def overall_cpa(self) -> float:
        if self.total_conversions > 0:
            return self.total_cost / self.total_conversions
        return 0.0
    
    @property
    def overall_roas(self) -> float:
        if self.total_cost > 0:
            return self.total_revenue / self.total_cost
        return 0.0
    
    @property
    def overall_ctr(self) -> float:
        if self.total_impressions > 0:
            return (self.total_clicks / self.total_impressions) * 100
        return 0.0
    
    @property
    def total_profit(self) -> float:
        return self.total_revenue + self.total_affiliate_revenue - self.total_cost
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaigns": {
                "live": self.campaigns_live,
                "completed": self.campaigns_completed,
                "total": self.campaigns_total,
            },
            "metrics": {
                "impressions": self.total_impressions,
                "clicks": self.total_clicks,
                "conversions": self.total_conversions,
                "revenue": round(self.total_revenue, 2),
                "affiliate_revenue": round(self.total_affiliate_revenue, 2),
                "cost": round(self.total_cost, 2),
                "profit": round(self.total_profit, 2),
            },
            "kpis": {
                "cpa": round(self.overall_cpa, 2),
                "roas": round(self.overall_roas, 2),
                "ctr": round(self.overall_ctr, 2),
            },
            "timestamp": datetime.now().isoformat(),
        }


class RevenueTracker:
    """Track revenue metrics for campaigns"""
    
    def __init__(self, redis_client=None):
        self.campaigns: Dict[str, RevenueCampaign] = {}
        self.redis = redis_client
    
    def create_campaign(self, **kwargs) -> RevenueCampaign:
        """Create a new revenue campaign"""
        campaign_id = f"camp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        campaign = RevenueCampaign(id=campaign_id, **kwargs)
        self.campaigns[campaign_id] = campaign
        return campaign
    
    def update_campaign_metrics(self, campaign_id: str, **metrics):
        """Update campaign metrics (impressions, clicks, etc.)"""
        if campaign_id not in self.campaigns:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        campaign = self.campaigns[campaign_id]
        for key, value in metrics.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)
    
    def get_dashboard(self) -> RevenueDashboard:
        """Generate revenue dashboard from all campaigns"""
        dashboard = RevenueDashboard()
        
        for campaign in self.campaigns.values():
            dashboard.campaigns_total += 1
            
            if campaign.status == CampaignStatus.ACTIVE:
                dashboard.campaigns_live += 1
            elif campaign.status == CampaignStatus.COMPLETED:
                dashboard.campaigns_completed += 1
            
            dashboard.total_impressions += campaign.impressions
            dashboard.total_clicks += campaign.clicks
            dashboard.total_conversions += campaign.conversions
            dashboard.total_revenue += campaign.revenue_usd
            dashboard.total_cost += campaign.cost_usd
            dashboard.total_affiliate_revenue += campaign.affiliate_revenue
        
        return dashboard
    
    def get_metrics_by_source(self) -> Dict[str, Dict[str, Any]]:
        """Get aggregated metrics by source platform"""
        by_source = {}
        
        for source in SourcePlatform:
            campaigns = [c for c in self.campaigns.values() if c.source_platform == source]
            if not campaigns:
                continue
            
            by_source[source.value] = {
                "campaigns": len(campaigns),
                "impressions": sum(c.impressions for c in campaigns),
                "revenue": round(sum(c.revenue_usd for c in campaigns), 2),
                "affiliate_revenue": round(sum(c.affiliate_revenue for c in campaigns), 2),
                "cost": round(sum(c.cost_usd for c in campaigns), 2),
                "roas": round(
                    sum(c.revenue_usd for c in campaigns) / max(sum(c.cost_usd for c in campaigns), 0.01),
                    2
                ),
            }
        
        return by_source
    
    def get_metrics_by_publish_platform(self) -> Dict[str, Dict[str, Any]]:
        """Get aggregated metrics by publish platform"""
        by_platform = {}
        
        for platform in PublishPlatform:
            campaigns = [c for c in self.campaigns.values() if c.content_platform == platform]
            if not campaigns:
                continue
            
            by_platform[platform.value] = {
                "campaigns": len(campaigns),
                "impressions": sum(c.impressions for c in campaigns),
                "revenue": round(sum(c.revenue_usd for c in campaigns), 2),
                "affiliate_revenue": round(sum(c.affiliate_revenue for c in campaigns), 2),
                "cost": round(sum(c.cost_usd for c in campaigns), 2),
                "roas": round(
                    sum(c.revenue_usd for c in campaigns) / max(sum(c.cost_usd for c in campaigns), 0.01),
                    2
                ),
            }
        
        return by_platform
