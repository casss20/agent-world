"""
tiktok_ugc.py — Agent World Business Models

TikTok UGC (User Generated Content) creator business model.
Helps creators monetize through brand deals, affiliate marketing, and product sales.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from business_models.base import (
    BusinessModel, DiagnosticCheck, BusinessContext, 
    Diagnosis, Strategy, Severity
)


class TikTokUGCModel(BusinessModel):
    """
    Business model for TikTok UGC creators.
    
    Revenue streams:
    1. Brand deals/sponsorships
    2. Affiliate commissions
    3. TikTok Creator Fund
    4. Own product sales (merch, digital products)
    5. Live gifting
    
    Key metrics: Followers, engagement rate, views, CPM, conversion rate
    """
    
    model_id = "tiktok_ugc"
    model_name = "TikTok UGC Creator"
    description = "Create TikTok content to monetize through brand deals, affiliate marketing, and product sales"
    
    typical_revenue_per_1k_followers = 10  # $10-50 per 1k followers for brand deals
    
    def get_diagnostic_checks(self) -> List[DiagnosticCheck]:
        return [
            ContentQualityCheck(),
            NicheSaturationCheck(),
            EngagementHealthCheck(),
            MonetizationReadinessCheck(),
            PostingConsistencyCheck(),
        ]
    
    def get_kpis(self) -> Dict[str, Dict]:
        return {
            "followers": {
                "label": "Follower Count",
                "target": 10000,  # Minimum for monetization
                "good": 50000,
                "excellent": 100000,
                "unit": "followers"
            },
            "engagement_rate": {
                "label": "Engagement Rate",
                "target": 0.03,  # 3%
                "good": 0.05,    # 5%
                "excellent": 0.08,  # 8%+
                "unit": "percentage"
            },
            "views_per_video": {
                "label": "Average Views",
                "target": 1000,
                "good": 10000,
                "excellent": 100000,
                "unit": "views"
            },
            "monthly_revenue": {
                "label": "Monthly Revenue",
                "target": 500,
                "good": 2000,
                "excellent": 10000,
                "unit": "usd"
            },
            "content_velocity": {
                "label": "Posts Per Week",
                "target": 5,
                "good": 10,
                "excellent": 21,  # 3x daily
                "unit": "posts"
            },
            "brand_deal_conversion": {
                "label": "Brand Deal Close Rate",
                "target": 0.05,  # 5% of outreach
                "good": 0.10,
                "excellent": 0.20,
                "unit": "percentage"
            }
        }


# ============================================================================
# Diagnostic Checks
# ============================================================================

class ContentQualityCheck(DiagnosticCheck):
    """Analyze content quality vs top performers in niche"""
    
    check_id = "content_quality"
    name = "Content Quality Analysis"
    description = "Compares your content quality to top performers in your niche"
    
    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        # In production: Use Camofox to scrape top TikToks in niche
        # Compare hooks, editing, music trends, visual quality
        
        current_metrics = context.metrics or {}
        views = current_metrics.get("avg_views", 0)
        saves = current_metrics.get("avg_saves", 0)
        
        # Quality score based on saves (indicates value) vs views
        if views > 0:
            save_rate = saves / views
        else:
            save_rate = 0
        
        issues = []
        if save_rate < 0.02:
            issues.append("Low save rate - content may not be valuable enough to revisit")
        if views < 1000:
            issues.append("Low average views - hook or thumbnail needs improvement")
        
        return {
            "score": min(100, int(save_rate * 2000 + views / 100)),
            "save_rate": round(save_rate, 3),
            "issues": issues,
            "benchmark": {
                "avg_views_top_10": 50000,  # Top 10% in niche
                "save_rate_top_10": 0.05
            },
            "recommendations": [
                "Study top 10 videos in your niche - analyze their first 3 seconds",
                "Add text overlay with key point in first 1 second",
                "Test 5 different hooks per topic, keep the winner"
            ]
        }


class NicheSaturationCheck(DiagnosticCheck):
    """Check if niche is oversaturated or has opportunity"""
    
    check_id = "niche_saturation"
    name = "Niche Saturation Analysis"
    description = "Analyzes competition level and opportunity in your content niche"
    
    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        niche = context.niche or "general"
        
        # High-opportunity niches (underserved)
        high_opportunity = [
            "b2b_saas", "productivity_tools", "developer_tools",
            "finance_for_teen", "career_advice_gen_z", "adhd_productivity",
            "small_business_tips", "ecommerce_tutorials"
        ]
        
        # Saturated niches (hard to break in)
        saturated = [
            "general_lifestyle", "fitness_motivation", "makeup_tutorials",
            "daily_vlogs", "dance_trends"
        ]
        
        opportunity_score = 50  # Neutral
        issues = []
        
        if niche in high_opportunity:
            opportunity_score = 80
            status = "high_opportunity"
        elif niche in saturated:
            opportunity_score = 30
            status = "saturated"
            issues.append("Niche is saturated - need unique angle or sub-niche")
        else:
            status = "moderate"
        
        return {
            "score": opportunity_score,
            "niche": niche,
            "status": status,
            "issues": issues,
            "recommendations": [
                "Find micro-niche within your topic (e.g., 'Productivity' → 'ADHD Productivity for Developers')",
                "Check #hashtag volume - aim for 10M-100M views (not 10B+)",
                "Look for niches where top videos have < 100k views (easier to rank)"
            ]
        }


class EngagementHealthCheck(DiagnosticCheck):
    """Analyze engagement patterns and health"""
    
    check_id = "engagement_health"
    name = "Engagement Health"
    description = "Checks if followers are actively engaging vs passive scrolling"
    
    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        metrics = context.metrics or {}
        
        followers = metrics.get("followers", 0)
        likes = metrics.get("avg_likes", 0)
        comments = metrics.get("avg_comments", 0)
        shares = metrics.get("avg_shares", 0)
        
        # Engagement rate calculation
        if followers > 0:
            engagement_rate = (likes + comments * 2 + shares * 3) / followers
        else:
            engagement_rate = 0
        
        issues = []
        severity = None
        
        if engagement_rate < 0.02:
            issues.append("Critical: Engagement rate below 2% - algorithm will stop showing your content")
            severity = Severity.CRITICAL
        elif engagement_rate < 0.03:
            issues.append("Warning: Engagement rate below 3% - growth will be slow")
            severity = Severity.MEDIUM
        
        return {
            "score": min(100, int(engagement_rate * 2000)),
            "engagement_rate": round(engagement_rate, 4),
            "severity": severity.value if severity else "none",
            "issues": issues,
            "comment_to_like_ratio": round(comments / likes, 3) if likes > 0 else 0,
            "recommendations": [
                "Ask specific questions in captions to drive comments",
                "End videos with 'Save this for later' CTA",
                "Respond to first 10 comments within 30 minutes (boosts algorithm)",
                "Create 'reply videos' to high-engagement comments"
            ]
        }


class MonetizationReadinessCheck(DiagnosticCheck):
    """Check if account is ready to monetize effectively"""
    
    check_id = "monetization_ready"
    name = "Monetization Readiness"
    description = "Analyzes if you're ready for brand deals and what rates to charge"
    
    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        metrics = context.metrics or {}
        
        followers = metrics.get("followers", 0)
        engagement_rate = metrics.get("engagement_rate", 0)
        has_email_in_bio = metrics.get("has_contact", False)
        
        issues = []
        blockers = []
        
        # Brand deal readiness
        if followers < 10000:
            blockers.append("Need 10k followers for most brand deals")
        if not has_email_in_bio:
            blockers.append("No contact method in bio - brands can't reach you")
        if engagement_rate < 0.02:
            blockers.append("Engagement too low - brands want active audiences")
        
        # Calculate suggested rates
        base_rate = (followers / 1000) * 10  # $10 per 1k is baseline
        engagement_multiplier = min(2.0, engagement_rate / 0.03)  # Higher engagement = higher rates
        suggested_rate = base_rate * engagement_multiplier
        
        return {
            "score": 100 if not blockers else max(0, 100 - len(blockers) * 25),
            "followers": followers,
            "ready_for_brand_deals": len(blockers) == 0,
            "blockers": blockers,
            "sponsored_post_rate": round(suggested_rate, 2),
            "suggested_rates": {
                "sponsored_video": round(suggested_rate, 2),
                "affiliate_commission": "10-20% of sales",
                "bundle_deal_3_posts": round(suggested_rate * 2.5, 2)
            },
            "recommendations": [
                "Add 'Business: email@example.com' to bio immediately" if not has_email_in_bio else None,
                "Create 'media kit' highlight with stats and past collabs",
                "Join influencer platforms: AspireIQ, Grin, or Upfluence",
                "Start with affiliate programs while building follower count" if followers < 10000 else None
            ]
        }


class PostingConsistencyCheck(DiagnosticCheck):
    """Check content velocity and consistency"""
    
    check_id = "posting_consistency"
    name = "Posting Consistency"
    description = "Analyzes if posting frequency is optimal for growth"
    
    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        metrics = context.metrics or {}
        
        posts_per_week = metrics.get("posts_per_week", 0)
        avg_views = metrics.get("avg_views", 0)
        
        issues = []
        
        if posts_per_week < 3:
            issues.append("Posting too infrequently - algorithm forgets you")
        if posts_per_week > 21:
            issues.append("Posting too much - quality likely suffering, risk burnout")
        
        # Optimal depends on stage
        followers = metrics.get("followers", 0)
        if followers < 1000:
            optimal = "7-14 per week (growth phase)"
            optimal_min, optimal_max = 7, 14
        elif followers < 10000:
            optimal = "5-10 per week (quality focus)"
            optimal_min, optimal_max = 5, 10
        else:
            optimal = "3-7 per week (sustainability)"
            optimal_min, optimal_max = 3, 7
        
        is_optimal = optimal_min <= posts_per_week <= optimal_max
        
        return {
            "score": 100 if is_optimal else 50,
            "posts_per_week": posts_per_week,
            "optimal_range": optimal,
            "is_optimal": is_optimal,
            "issues": issues,
            "recommendations": [
                f"Current optimal: {optimal}",
                "Batch create content on weekends, schedule throughout week",
                "Post at optimal times: 7-9am, 12-1pm, 7-9pm (test your audience)",
                "Use TikTok's scheduler or Later/Planoly for consistency"
            ]
        }


# ============================================================================
# Strategy Generation
# ============================================================================

class TikTokUGCStrategyGenerator:
    """Generate strategies specific to TikTok UGC growth"""
    
    @staticmethod
    def get_strategies(diagnosis: Diagnosis, context: BusinessContext) -> List[Strategy]:
        strategies = []
        
        # Growth strategies
        if diagnosis.health_score < 40:
            strategies.append(Strategy(
                strategy_id="growth_sprint",
                name="30-Day Growth Sprint",
                description="Post 2x daily for 30 days using trending sounds and hooks",
                expected_impact="+500-2000 followers",
                effort_hours=2,
                cost_usd=0,
                steps=[
                    "Research top 20 trending sounds this week",
                    "Create content batch (14 videos) every Sunday",
                    "Post at 8am and 7pm daily",
                    "Reply to every comment in first hour",
                    "Duets/Stitches with trending creators daily"
                ]
            ))
        
        # Monetization strategies
        if diagnosis.health_score > 50:
            strategies.append(Strategy(
                strategy_id="affiliate_launch",
                name="Affiliate Revenue Stream",
                description="Join affiliate programs for tools/products you already use",
                expected_impact="$200-1000/month within 60 days",
                effort_hours=5,
                cost_usd=0,
                steps=[
                    "List 10 products you use and love",
                    "Apply to affiliate programs (Amazon, ShareASale, individual brands)",
                    "Create 'honest review' content for each",
                    "Add affiliate links to bio (Linktree)",
                    "Track conversions, double down on winners"
                ]
            ))
            
            strategies.append(Strategy(
                strategy_id="ugc_creator_deals",
                name="UGC Creator for Brands",
                description="Create content FOR brands (not just sponsored posts on your account)",
                expected_impact="$500-3000/month creating content for brand accounts",
                effort_hours=10,
                cost_usd=0,
                steps=[
                    "Create portfolio of 5 high-quality videos",
                    "Join UGC platforms: Billo, Insense, Trend.io",
                    "Reach out to 20 brands/week with portfolio",
                    "Charge $100-500 per video package",
                    "Build retainer relationships with 3-5 brands"
                ]
            ))
        
        # Content optimization
        strategies.append(Strategy(
            strategy_id="hook_testing",
            name="Hook A/B Testing System",
            description="Test 3 different hooks for every topic, keep the winner",
            expected_impact="+50-100% view retention",
            effort_hours=1,
            cost_usd=0,
            steps=[
                "For each topic, write 3 different first 3 seconds",
                "Post all 3 within 24 hours",
                "Compare view velocity in first hour",
                "Keep winner, archive losers",
                "Build 'hook library' of proven openers"
            ]
        ))
        
        # Revenue diversification
        if context.current_revenue and context.current_revenue > 500:
            strategies.append(Strategy(
                strategy_id="digital_product",
                name="Digital Product Launch",
                description="Create and sell digital product to your audience",
                expected_impact="$1000-5000 launch, $500/month ongoing",
                effort_hours=20,
                cost_usd=50,
                steps=[
                    "Survey audience: 'What would you pay $20 for?'",
                    "Create simple digital product (template, guide, notion)",
                    "Pre-sell to validate (10 pre-orders = build it)",
                    "Use Gumroad ($0/month) or Stan Store",
                    "Launch with 3-video sequence: problem → solution → offer"
                ]
            ))
        
        return strategies
