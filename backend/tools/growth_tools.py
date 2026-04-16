"""
growth_tools.py — Agent World

Tools for Growth agent: SEO, content marketing, email campaigns, affiliate/influencer outreach.
"""

import logging
from typing import Dict, Any, List
from mcp_registry import register_tool

logger = logging.getLogger(__name__)


async def keyword_research(
    topic: str,
    platform: str = "google",
    location: str = "us",
    language: str = "en"
) -> Dict[str, Any]:
    """
    Research keywords for SEO optimization. Returns search volume, competition, related keywords.
    
    Args:
        topic: Main topic or seed keyword
        platform: google, youtube, amazon, etsy
        location: Country code for local search volume
        language: Language code
    
    Returns:
        Keywords with volume, difficulty, CPC, and recommendations
    """
    from growth_executor import get_growth_executor
    
    executor = get_growth_executor(None)
    
    return await executor._keyword_research("growth", {
        "topic": topic,
        "platform": platform,
        "location": location,
        "language": language
    })


async def optimize_content_seo(
    content: str,
    target_keywords: List[str],
    content_type: str = "blog_post"
) -> Dict[str, Any]:
    """
    Optimize content for target keywords. Returns improvements and SEO score.
    
    Args:
        content: The content to optimize
        target_keywords: Primary and secondary keywords to target
        content_type: blog_post, product_description, landing_page
    
    Returns:
        Optimized content, SEO score, specific improvements made
    """
    from growth_executor import get_growth_executor
    
    executor = get_growth_executor(None)
    
    return await executor._optimize_content("growth", {
        "content": content,
        "target_keywords": target_keywords,
        "content_type": content_type
    })


async def create_blog_post(
    topic: str,
    target_keywords: List[str],
    tone: str = "professional",
    length: str = "medium",
    include_images: bool = True
) -> Dict[str, Any]:
    """
    Create an SEO-optimized blog post on a topic.
    
    Args:
        topic: Blog post topic/title
        target_keywords: Keywords to optimize for
        tone: casual, professional, technical, friendly
        length: short (500w), medium (1000w), long (2000w)
        include_images: Whether to generate images with the post
    
    Returns:
        Full blog post with title, content, meta description, suggested images
    """
    from growth_executor import get_growth_executor
    
    executor = get_growth_executor(None)
    
    return await executor._create_blog_post("growth", {
        "topic": topic,
        "target_keywords": target_keywords,
        "tone": tone,
        "length": length,
        "include_images": include_images
    })


async def create_email_sequence(
    purpose: str,
    audience: str,
    num_emails: int = 5,
    tone: str = "friendly",
    product_id: str = None
) -> Dict[str, Any]:
    """
    Create an automated email sequence (welcome series, abandoned cart, etc.).
    
    Args:
        purpose: welcome, abandoned_cart, product_launch, nurture
        audience: Who the emails are for (e.g., "new subscribers", "free trial users")
        num_emails: Number of emails in sequence (3-10)
        tone: friendly, professional, urgent, playful
        product_id: Optional product to focus on
    
    Returns:
        Full email sequence with subject lines, body, send delays, CTAs
    """
    from growth_executor import get_growth_executor
    
    executor = get_growth_executor(None)
    
    return await executor._create_email_sequence("growth", {
        "purpose": purpose,
        "audience": audience,
        "num_emails": num_emails,
        "tone": tone,
        "product_id": product_id
    })


async def find_affiliates(
    niche: str,
    platform: str = "all",
    min_followers: int = 1000,
    engagement_threshold: float = 0.02
) -> Dict[str, Any]:
    """
    Find potential affiliate partners and influencers in a niche.
    
    Args:
        niche: The niche/topic (e.g., "productivity planners", "fitness coaching")
        platform: all, instagram, youtube, tiktok, blog, twitter
        min_followers: Minimum follower count to consider
        engagement_threshold: Minimum engagement rate (e.g., 0.02 = 2%)
    
    Returns:
        List of potential affiliates with contact info, audience stats, fit score
    """
    from growth_executor import get_growth_executor
    
    executor = get_growth_executor(None)
    
    return await executor._find_affiliates("growth", {
        "niche": niche,
        "platform": platform,
        "min_followers": min_followers,
        "engagement_threshold": engagement_threshold
    })


async def outreach_message(
    contact_name: str,
    platform: str,
    niche: str,
    product_pitch: str,
    offer_type: str = "affiliate",
    personalization: str = ""
) -> Dict[str, Any]:
    """
    Create personalized outreach message for affiliate/influencer.
    
    Args:
        contact_name: Name of the person to contact
        platform: instagram, youtube, email, linkedin
        niche: Their niche/topic
        product_pitch: Brief description of what you're offering
        offer_type: affiliate, sponsored_post, collaboration, free_product
        personalization: Any specific detail to include (e.g., "loved your video on X")
    
    Returns:
        Personalized message, subject line (if email), follow-up suggestions
    """
    from growth_executor import get_growth_executor
    
    executor = get_growth_executor(None)
    
    return await executor._outreach_message("growth", {
        "contact_name": contact_name,
        "platform": platform,
        "niche": niche,
        "product_pitch": product_pitch,
        "offer_type": offer_type,
        "personalization": personalization
    })


async def analyze_backlinks(
    url: str,
    competitors: List[str] = None
) -> Dict[str, Any]:
    """
    Analyze backlink profile for a URL and suggest link-building opportunities.
    
    Args:
        url: The URL to analyze
        competitors: Competitor URLs to compare against
    
    Returns:
        Backlink count, quality scores, gap analysis vs competitors, opportunities
    """
    from growth_executor import get_growth_executor
    
    executor = get_growth_executor(None)
    
    return await executor._analyze_backlinks("growth", {
        "url": url,
        "competitors": competitors or []
    })


async def schedule_social_content(
    content: str,
    platforms: List[str],
    best_times: bool = True,
    recycling: bool = False
) -> Dict[str, Any]:
    """
    Schedule content across social media platforms with optimal timing.
    
    Args:
        content: The content to post (text, can include image URLs)
        platforms: twitter, instagram, facebook, linkedin, pinterest, tiktok
        best_times: Auto-schedule for optimal engagement times
        recycling: Whether to recycle this post periodically
    
    Returns:
        Schedule with post times, platform-specific variations, estimated reach
    """
    from growth_executor import get_growth_executor
    
    executor = get_growth_executor(None)
    
    return await executor._schedule_social("growth", {
        "content": content,
        "platforms": platforms,
        "best_times": best_times,
        "recycling": recycling
    })


def register_growth_tools():
    """Register all growth tools in the MCP registry"""
    
    register_tool(
        name="keyword_research",
        description="Research keywords for SEO. Returns search volume, competition score, and related keyword suggestions for Google, YouTube, Amazon, or Etsy.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Main topic or seed keyword to research"},
                "platform": {
                    "type": "string",
                    "description": "Which platform to optimize for",
                    "enum": ["google", "youtube", "amazon", "etsy"],
                    "default": "google"
                },
                "location": {"type": "string", "description": "Country code for local search volume", "default": "us"},
                "language": {"type": "string", "description": "Language code", "default": "en"}
            },
            "required": ["topic"]
        },
        fn=keyword_research
    )
    
    register_tool(
        name="optimize_content_seo",
        description="Optimize existing content for target keywords. Returns improved content with SEO score and specific changes made.",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The content to optimize"},
                "target_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Primary and secondary keywords to target"
                },
                "content_type": {
                    "type": "string",
                    "description": "Type of content",
                    "enum": ["blog_post", "product_description", "landing_page"],
                    "default": "blog_post"
                }
            },
            "required": ["content", "target_keywords"]
        },
        fn=optimize_content_seo
    )
    
    register_tool(
        name="create_blog_post",
        description="Create an SEO-optimized blog post. Includes keyword optimization, meta description, and image suggestions.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Blog post topic or title"},
                "target_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to optimize the post for"
                },
                "tone": {
                    "type": "string",
                    "description": "Writing tone",
                    "enum": ["casual", "professional", "technical", "friendly"],
                    "default": "professional"
                },
                "length": {
                    "type": "string",
                    "description": "Post length",
                    "enum": ["short", "medium", "long"],
                    "default": "medium"
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to include image generation prompts",
                    "default": True
                }
            },
            "required": ["topic", "target_keywords"]
        },
        fn=create_blog_post
    )
    
    register_tool(
        name="create_email_sequence",
        description="Create an automated email sequence (welcome series, abandoned cart, product launch). Returns full emails with subject lines, timing, and CTAs.",
        parameters={
            "type": "object",
            "properties": {
                "purpose": {
                    "type": "string",
                    "description": "Goal of the sequence",
                    "enum": ["welcome", "abandoned_cart", "product_launch", "nurture"]
                },
                "audience": {"type": "string", "description": "Who the emails are for (e.g., 'new subscribers')"},
                "num_emails": {
                    "type": "integer",
                    "description": "Number of emails in sequence (3-10)",
                    "minimum": 3,
                    "maximum": 10,
                    "default": 5
                },
                "tone": {
                    "type": "string",
                    "description": "Email tone",
                    "enum": ["friendly", "professional", "urgent", "playful"],
                    "default": "friendly"
                },
                "product_id": {"type": "string", "description": "Optional product to focus on"}
            },
            "required": ["purpose", "audience"]
        },
        fn=create_email_sequence
    )
    
    register_tool(
        name="find_affiliates",
        description="Find potential affiliate partners and influencers in a niche. Returns list with contact info, audience stats, and relevance scores.",
        parameters={
            "type": "object",
            "properties": {
                "niche": {"type": "string", "description": "The niche/topic to search in (e.g., 'productivity planners')"},
                "platform": {
                    "type": "string",
                    "description": "Platform to search",
                    "enum": ["all", "instagram", "youtube", "tiktok", "blog", "twitter"],
                    "default": "all"
                },
                "min_followers": {
                    "type": "integer",
                    "description": "Minimum follower count",
                    "default": 1000
                },
                "engagement_threshold": {
                    "type": "number",
                    "description": "Minimum engagement rate (0.02 = 2%)",
                    "default": 0.02
                }
            },
            "required": ["niche"]
        },
        fn=find_affiliates
    )
    
    register_tool(
        name="outreach_message",
        description="Create personalized outreach message for an affiliate or influencer. Returns message, subject line, and follow-up suggestions.",
        parameters={
            "type": "object",
            "properties": {
                "contact_name": {"type": "string", "description": "Name of the person to contact"},
                "platform": {
                    "type": "string",
                    "description": "Where to reach them",
                    "enum": ["instagram", "youtube", "email", "linkedin"]
                },
                "niche": {"type": "string", "description": "Their niche/topic"},
                "product_pitch": {"type": "string", "description": "Brief description of your product/offer"},
                "offer_type": {
                    "type": "string",
                    "description": "Type of partnership",
                    "enum": ["affiliate", "sponsored_post", "collaboration", "free_product"],
                    "default": "affiliate"
                },
                "personalization": {"type": "string", "description": "Specific detail to include (e.g., 'loved your video on X')"}
            },
            "required": ["contact_name", "platform", "niche", "product_pitch"]
        },
        fn=outreach_message
    )
    
    register_tool(
        name="analyze_backlinks",
        description="Analyze backlink profile for SEO. Returns backlink count, quality scores, and link-building opportunities compared to competitors.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to analyze"},
                "competitors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Competitor URLs to compare",
                    "default": []
                }
            },
            "required": ["url"]
        },
        fn=analyze_backlinks
    )
    
    register_tool(
        name="schedule_social_content",
        description="Schedule content across social media platforms with optimal timing. Returns schedule with platform-specific variations.",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content to post (text with optional image URLs)"},
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["twitter", "instagram", "facebook", "linkedin", "pinterest", "tiktok"]
                    },
                    "description": "Platforms to post to"
                },
                "best_times": {
                    "type": "boolean",
                    "description": "Auto-schedule for optimal engagement",
                    "default": True
                },
                "recycling": {
                    "type": "boolean",
                    "description": "Whether to recycle this post periodically",
                    "default": False
                }
            },
            "required": ["content", "platforms"]
        },
        fn=schedule_social_content
    )
    
    logger.info("[Growth Tools] Registered 8 tools: keyword_research, optimize_content_seo, create_blog_post, create_email_sequence, find_affiliates, outreach_message, analyze_backlinks, schedule_social_content")
