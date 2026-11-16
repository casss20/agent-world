"""
Content Scout Integration Service
Connects the Content Director agent to the multi-source trend scout.

Allows the Content Director to:
- Discover trending topics across Reddit, HN, ProductHunt, Twitter
- Generate content strategies from trends
- Create content calendars based on engagement data
- Alert on viral opportunities
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from multi_source_scout import MultiSourceScout, TrendItem, SourceType
from agents.roles.role_definitions import get_role

logger = logging.getLogger(__name__)


class ContentScoutService:
    """
    Service for Content Director agent to interact with trend data.
    Bridges content strategy with real-time trend discovery.
    """

    def __init__(self):
        self.agent_id = "content_director"
        self.agent_name = "Taylor"
        self.scout = MultiSourceScout()

    async def discover_trends(
        self,
        source: Optional[str] = None,
        min_engagement: int = 100,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Discover trending topics for content creation.
        Content Director uses this to plan content calendar.
        """
        try:
            # Use the scout to discover trends
            trends = self.scout.discovered_trends
            
            # Filter by engagement
            filtered = [t for t in trends if t.engagement_score >= min_engagement]
            
            # Sort by engagement
            filtered.sort(key=lambda x: x.engagement_score, reverse=True)
            
            # Take top N
            top_trends = filtered[:limit]
            
            # Generate content angles
            content_angles = self._generate_content_angles(top_trends)
            
            return {
                "success": True,
                "trends_discovered": len(trends),
                "trends_filtered": len(filtered),
                "top_trends": [t.to_dict() for t in top_trends],
                "content_angles": content_angles,
                "reported_by": {
                    "agent_id": self.agent_id,
                    "name": self.agent_name,
                    "role": "Content Director",
                },
            }
        except Exception as e:
            logger.error("Content trend discovery failed: %s", e)
            return {
                "success": False,
                "error": str(e),
            }

    def _generate_content_angles(self, trends: List[TrendItem]) -> List[Dict[str, Any]]:
        """Generate content creation angles from trends."""
        angles = []
        for trend in trends:
            angle = {
                "trend_id": trend.id,
                "title": trend.title,
                "source": trend.source.value,
                "suggested_formats": self._suggest_formats(trend),
                "target_audience": self._infer_audience(trend),
                "estimated_engagement": trend.engagement_score,
                "urgency": "high" if trend.engagement_score > 1000 else "medium",
                "monetization_potential": trend.monetization_angle or "unknown",
            }
            angles.append(angle)
        return angles

    def _suggest_formats(self, trend: TrendItem) -> List[str]:
        """Suggest content formats based on trend source."""
        source_formats = {
            "reddit": ["blog_post", "discussion_thread", "community_update"],
            "hackernews": ["technical_article", "tutorial", "deep_dive"],
            "producthunt": ["product_review", "launch_announcement", "demo_video"],
            "twitter": ["thread", "short_form", "visual_content"],
        }
        return source_formats.get(trend.source.value, ["blog_post"])

    def _infer_audience(self, trend: TrendItem) -> str:
        """Infer target audience from trend metadata."""
        if trend.source == SourceType.HACKERNEWS:
            return "technical_founders"
        elif trend.source == SourceType.PRODUCTHUNT:
            return "early_adopters"
        elif trend.source == SourceType.REDDIT:
            return trend.source_subreddit or "general"
        elif trend.source == SourceType.TWITTER:
            return "social_media"
        return "general"

    async def generate_content_calendar(
        self,
        days: int = 7,
        themes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a content calendar based on current trends.
        Content Director schedules content for the week.
        """
        trends_result = await self.discover_trends(limit=days * 2)
        
        if not trends_result.get("success"):
            return trends_result

        trends = trends_result.get("top_trends", [])
        calendar = []

        for i, trend in enumerate(trends[:days]):
            day_plan = {
                "day": i + 1,
                "theme": trend.get("title", "General content"),
                "source": trend.get("source", "unknown"),
                "formats": self._suggest_formats_for_trend(trend),
                "keywords": trend.get("keywords", []),
                "target_publish_time": "09:00 EST" if i % 2 == 0 else "14:00 EST",
                "status": "planned",
            }
            calendar.append(day_plan)

        return {
            "success": True,
            "calendar_days": days,
            "calendar": calendar,
            "total_trends_used": len(calendar),
            "themes": themes or [t.get("title") for t in trends[:3]],
            "reported_by": {
                "agent_id": self.agent_id,
                "name": self.agent_name,
                "role": "Content Director",
            },
        }

    def _suggest_formats_for_trend(self, trend: Dict[str, Any]) -> List[str]:
        """Suggest content formats for a trend dict."""
        source = trend.get("source", "")
        format_map = {
            "reddit": ["blog_post", "reddit_post"],
            "hackernews": ["technical_article", "github_repo"],
            "producthunt": ["product_review", "twitter_thread"],
            "twitter": ["twitter_thread", "instagram_carousel"],
        }
        return format_map.get(source, ["blog_post"])

    async def check_viral_opportunities(
        self,
        min_engagement: int = 5000,
    ) -> Dict[str, Any]:
        """
        Check for viral-worthy trends that need immediate action.
        Content Director escalates to CEO for high-value opportunities.
        """
        trends_result = await self.discover_trends(min_engagement=min_engagement)
        
        if not trends_result.get("success"):
            return trends_result

        viral = [t for t in trends_result.get("top_trends", []) if t.get("engagement_score", 0) > min_engagement]
        
        if viral:
            return {
                "success": True,
                "alert": True,
                "severity": "high",
                "viral_opportunities": viral,
                "count": len(viral),
                "message": f"{len(viral)} viral opportunities detected — immediate content creation recommended",
                "escalation_target": "ceo",  # Content escalates strategic to CEO
                "recommended_action": "Create rapid-response content within 2 hours",
            }

        return {
            "success": True,
            "alert": False,
            "message": "No viral opportunities above threshold",
            "threshold": min_engagement,
        }


# ── Singleton ───────────────────────────────────────────────────────────

_content_scout_service: Optional[ContentScoutService] = None


def get_content_scout_service() -> ContentScoutService:
    global _content_scout_service
    if _content_scout_service is None:
        _content_scout_service = ContentScoutService()
    return _content_scout_service
