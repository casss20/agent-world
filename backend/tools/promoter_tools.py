"""
promoter_tools.py — Agent World

Tools for Promoter agent to run paid advertising campaigns.
"""

import logging
from typing import Dict, Any
from mcp_registry import register_tool

logger = logging.getLogger(__name__)


async def create_ads(
    platform: str,
    campaign_name: str,
    objective: str,
    daily_budget: float,
    target_audience: Dict[str, Any],
    creative: Dict[str, Any],
    lifetime_budget: float = None
) -> Dict[str, Any]:
    """
    Create a paid advertising campaign on Meta, Google, Amazon, TikTok, or Pinterest.
    
    Args:
        platform: ad platform (meta, google, amazon, tiktok, pinterest)
        campaign_name: Name for the campaign
        objective: conversion, awareness, traffic, engagement
        daily_budget: Daily spend limit in USD
        target_audience: Demographics, interests, behaviors
        creative: Headlines, images, CTAs
        lifetime_budget: Optional total campaign budget
    
    Returns:
        Campaign ID, estimated reach, status
    """
    from promoter_executor import get_promoter_executor
    
    executor = get_promoter_executor(None)
    
    campaign_config = {
        "name": campaign_name,
        "objective": objective,
        "daily_budget": daily_budget,
        "lifetime_budget": lifetime_budget,
        "target_audience": target_audience,
        "creative": creative
    }
    
    result = await executor._create_campaign("promoter", {
        "platform": platform,
        "campaign": campaign_config
    })
    
    return result


async def modify_budget(
    campaign_id: str,
    new_daily_budget: float = None,
    new_lifetime_budget: float = None
) -> Dict[str, Any]:
    """
    Modify the budget of an active advertising campaign.
    
    Args:
        campaign_id: The campaign to modify
        new_daily_budget: New daily spend limit
        new_lifetime_budget: New total budget cap
    
    Returns:
        Update confirmation
    """
    from promoter_executor import get_promoter_executor
    
    executor = get_promoter_executor(None)
    
    return await executor._modify_budget("promoter", {
        "campaign_id": campaign_id,
        "new_daily_budget": new_daily_budget,
        "new_lifetime_budget": new_lifetime_budget
    })


async def pause_campaign(
    campaign_id: str,
    reason: str = "Manual pause"
) -> Dict[str, Any]:
    """
    Pause an active advertising campaign.
    
    Args:
        campaign_id: Campaign to pause
        reason: Why it's being paused
    
    Returns:
        Pause confirmation with final metrics
    """
    from promoter_executor import get_promoter_executor
    
    executor = get_promoter_executor(None)
    
    return await executor._pause_campaign("promoter", {
        "campaign_id": campaign_id,
        "reason": reason
    })


async def get_campaign_metrics(
    campaign_id: str,
    platform: str = None
) -> Dict[str, Any]:
    """
    Get performance metrics for a campaign (spend, impressions, clicks, conversions, ROAS).
    
    Args:
        campaign_id: The campaign to check
        platform: Optional platform hint
    
    Returns:
        Full metrics breakdown with recommendations
    """
    from promoter_executor import get_promoter_executor
    
    executor = get_promoter_executor(None)
    
    return await executor._get_metrics("promoter", {
        "campaign_id": campaign_id,
        "platform": platform
    })


async def optimize_campaign(
    campaign_id: str,
    auto_scale: bool = True,
    auto_pause: bool = True
) -> Dict[str, Any]:
    """
    Auto-optimize a campaign based on performance rules (pause if ROAS < 0.5, scale if ROAS > 2.5).
    
    Args:
        campaign_id: Campaign to optimize
        auto_scale: Whether to automatically increase budget for high performers
        auto_pause: Whether to automatically pause low performers
    
    Returns:
        Optimization actions taken
    """
    from promoter_executor import get_promoter_executor
    
    executor = get_promoter_executor(None)
    
    return await executor._optimize_campaign("promoter", {
        "campaign_id": campaign_id,
        "auto_scale": auto_scale,
        "auto_pause": auto_pause
    })


async def a_b_test(
    campaign_id: str,
    test_type: str,
    variants: list,
    duration_days: int = 7,
    total_budget: float = 70
) -> Dict[str, Any]:
    """
    Set up an A/B test for ad creative or targeting.
    
    Args:
        campaign_id: Base campaign to test
        test_type: creative, audience, or placement
        variants: List of variant configurations (min 2)
        duration_days: How long to run the test
        total_budget: Total test budget
    
    Returns:
        Test setup with schedule
    """
    from promoter_executor import get_promoter_executor
    
    executor = get_promoter_executor(None)
    
    return await executor._a_b_test("promoter", {
        "campaign_id": campaign_id,
        "test_type": test_type,
        "variants": variants,
        "duration_days": duration_days,
        "total_budget": total_budget
    })


def register_promoter_tools():
    """Register all promoter tools in the MCP registry"""
    
    register_tool(
        name="create_ads",
        description="Create a paid advertising campaign on Meta, Google, Amazon, TikTok, or Pinterest. Returns campaign ID, estimated reach, and requires human approval for budget > $100/day.",
        parameters={
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "Ad platform",
                    "enum": ["meta", "google", "amazon", "tiktok", "pinterest"]
                },
                "campaign_name": {"type": "string", "description": "Name for the campaign"},
                "objective": {
                    "type": "string",
                    "description": "Campaign goal",
                    "enum": ["conversion", "awareness", "traffic", "engagement"]
                },
                "daily_budget": {
                    "type": "number",
                    "description": "Daily spend limit in USD (max $1000)"
                },
                "lifetime_budget": {
                    "type": "number",
                    "description": "Optional total campaign budget cap"
                },
                "target_audience": {
                    "type": "object",
                    "description": "Audience targeting parameters",
                    "properties": {
                        "age_range": {"type": "string", "description": "e.g., 25-54"},
                        "gender": {"type": "string", "enum": ["all", "male", "female"]},
                        "interests": {"type": "array", "items": {"type": "string"}},
                        "behaviors": {"type": "array", "items": {"type": "string"}},
                        "lookalike": {"type": "boolean"}
                    }
                },
                "creative": {
                    "type": "object",
                    "description": "Ad creative elements",
                    "properties": {
                        "headlines": {"type": "array", "items": {"type": "string"}},
                        "descriptions": {"type": "array", "items": {"type": "string"}},
                        "images": {"type": "array", "items": {"type": "string"}},
                        "cta": {"type": "string", "description": "Call to action text"}
                    }
                }
            },
            "required": ["platform", "campaign_name", "objective", "daily_budget", "target_audience", "creative"]
        },
        fn=create_ads
    )
    
    register_tool(
        name="modify_budget",
        description="Modify the budget of an active campaign. Use this to scale up winners or reduce spend.",
        parameters={
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "new_daily_budget": {"type": "number", "description": "New daily limit"},
                "new_lifetime_budget": {"type": "number", "description": "New total cap"}
            },
            "required": ["campaign_id"]
        },
        fn=modify_budget
    )
    
    register_tool(
        name="pause_campaign",
        description="Pause an active advertising campaign. Use when performance drops or budget needs reallocation.",
        parameters={
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "reason": {"type": "string", "description": "Why the campaign is being paused"}
            },
            "required": ["campaign_id"]
        },
        fn=pause_campaign
    )
    
    register_tool(
        name="get_campaign_metrics",
        description="Get full performance metrics for a campaign: spend, impressions, clicks, CTR, CPC, conversions, CPA, ROAS.",
        parameters={
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "platform": {"type": "string"}
            },
            "required": ["campaign_id"]
        },
        fn=get_campaign_metrics
    )
    
    register_tool(
        name="optimize_campaign",
        description="Auto-optimize a campaign. Will pause if ROAS < 0.5, scale 20% if ROAS > 2.5.",
        parameters={
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "auto_scale": {"type": "boolean", "default": True},
                "auto_pause": {"type": "boolean", "default": True}
            },
            "required": ["campaign_id"]
        },
        fn=optimize_campaign
    )
    
    register_tool(
        name="a_b_test",
        description="Set up an A/B test for ad creative or audience targeting. Will run for specified duration and auto-report winner.",
        parameters={
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "test_type": {
                    "type": "string",
                    "enum": ["creative", "audience", "placement"],
                    "description": "What to test"
                },
                "variants": {
                    "type": "array",
                    "description": "At least 2 variant configs",
                    "items": {"type": "object"}
                },
                "duration_days": {"type": "integer", "default": 7, "description": "Test duration"},
                "total_budget": {"type": "number", "default": 70, "description": "Total test budget"}
            },
            "required": ["campaign_id", "test_type", "variants"]
        },
        fn=a_b_test
    )
    
    logger.info("[Promoter Tools] Registered 6 tools: create_ads, modify_budget, pause_campaign, get_campaign_metrics, optimize_campaign, a_b_test")
