"""
Content Scout Routes
API endpoints for Content Director agent + multi-source scout integration.
"""

from fastapi import APIRouter
from typing import Optional, List

from services.content_scout_service import get_content_scout_service

router = APIRouter(prefix="/api/agents/content", tags=["content-scout"])


@router.get("/trends", response_model=dict)
async def discover_trends(
    source: Optional[str] = None,
    min_engagement: int = 100,
    limit: int = 20,
):
    """Discover trending topics for content creation."""
    service = get_content_scout_service()
    return await service.discover_trends(source, min_engagement, limit)


@router.get("/calendar", response_model=dict)
async def generate_content_calendar(
    days: int = 7,
    themes: Optional[List[str]] = None,
):
    """Generate a content calendar based on current trends."""
    service = get_content_scout_service()
    return await service.generate_content_calendar(days, themes)


@router.get("/viral", response_model=dict)
async def check_viral_opportunities(
    min_engagement: int = 5000,
):
    """Check for viral-worthy trends needing immediate action."""
    service = get_content_scout_service()
    return await service.check_viral_opportunities(min_engagement)
