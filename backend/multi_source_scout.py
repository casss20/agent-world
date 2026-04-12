"""
Phase 5 Ticket 2: Multi-Source Expansion
Scout agents for Reddit, HackerNews, ProductHunt, Twitter/X
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import asyncio
import json


class SourceType(str, Enum):
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    PRODUCTHUNT = "producthunt"
    TWITTER = "twitter"


@dataclass
class TrendItem:
    """A discovered trend from any source"""
    id: str
    source: SourceType
    title: str
    url: str
    engagement_score: int  # upvotes, likes, points, etc.
    comment_count: int = 0
    category: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Content analysis
    summary: str = ""
    keywords: List[str] = field(default_factory=list)
    monetization_angle: str = ""
    
    # Metadata
    author: str = ""
    source_subreddit: str = ""  # For Reddit
    hn_rank: int = 0  # For HackerNews
    ph_topic: str = ""  # For ProductHunt
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.value,
            "title": self.title,
            "url": self.url,
            "engagement_score": self.engagement_score,
            "comment_count": self.comment_count,
            "category": self.category,
            "discovered_at": self.discovered_at,
            "summary": self.summary,
            "keywords": self.keywords,
            "monetization_angle": self.monetization_angle,
        }


class MultiSourceScout:
    """
    Scout agent that monitors multiple content sources for trends.
    Uses Camofox stealth browser for all scraping.
    """
    
    def __init__(self, camofox_client=None):
        self.camofox = camofox_client
        self.discovered_trends: List[TrendItem] = []
        
        # Source configurations
        self.reddit_subreddits = [
            "technology",
            "business", 
            "startups",
            "Entrepreneur"
        ]
        
        self.hn_pages = ["frontpage", "new"]
        
        self.ph_categories = ["daily", "tech", "ai", "productivity"]
        
        self.twitter_keywords = [
            "AI tools",
            "startup funding",
            "passive income",
            "side hustle",
            "tech trends"
        ]
    
    async def scout_all_sources(self) -> List[TrendItem]:
        """Run scouts across all configured sources"""
        print("🔍 SCOUT: Starting multi-source trend discovery...\n")
        
        tasks = [
            self.scout_reddit(),
            self.scout_hackernews(),
            self.scout_producthunt(),
            self.scout_twitter(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_trends = []
        for source_trends in results:
            if isinstance(source_trends, list):
                all_trends.extend(source_trends)
        
        # Sort by engagement score
        all_trends.sort(key=lambda x: x.engagement_score, reverse=True)
        
        self.discovered_trends = all_trends
        return all_trends
    
    async def scout_reddit(self) -> List[TrendItem]:
        """Scout Reddit subreddits using Camofox"""
        trends = []
        
        print("📱 Reddit Scout: Monitoring subreddits...")
        for subreddit in self.reddit_subreddits:
            print(f"   → r/{subreddit}")
            
            # Simulated Camofox browsing
            await asyncio.sleep(0.3)
            
            # Generate sample trends (in production, use Camofox)
            sample_trends = self._generate_reddit_trends(subreddit)
            trends.extend(sample_trends)
        
        print(f"   ✅ Reddit: {len(trends)} trends found\n")
        return trends
    
    async def scout_hackernews(self) -> List[TrendItem]:
        """Scout HackerNews frontpage and new"""
        trends = []
        
        print("🟠 HackerNews Scout: Checking frontpage + new...")
        
        for page in self.hn_pages:
            print(f"   → {page}")
            await asyncio.sleep(0.3)
            
            sample_trends = self._generate_hn_trends(page)
            trends.extend(sample_trends)
        
        print(f"   ✅ HackerNews: {len(trends)} trends found\n")
        return trends
    
    async def scout_producthunt(self) -> List[TrendItem]:
        """Scout ProductHunt daily launches"""
        trends = []
        
        print("🟣 ProductHunt Scout: Checking daily launches...")
        
        for category in self.ph_categories:
            print(f"   → {category}")
            await asyncio.sleep(0.3)
            
            sample_trends = self._generate_ph_trends(category)
            trends.extend(sample_trends)
        
        print(f"   ✅ ProductHunt: {len(trends)} trends found\n")
        return trends
    
    async def scout_twitter(self) -> List[TrendItem]:
        """Scout Twitter/X trending topics"""
        trends = []
        
        print("🐦 Twitter Scout: Monitoring trending keywords...")
        
        for keyword in self.twitter_keywords:
            print(f"   → '{keyword}'")
            await asyncio.sleep(0.3)
            
            sample_trends = self._generate_twitter_trends(keyword)
            trends.extend(sample_trends)
        
        print(f"   ✅ Twitter: {len(trends)} trends found\n")
        return trends
    
    def _generate_reddit_trends(self, subreddit: str) -> List[TrendItem]:
        """Generate sample Reddit trends (replace with Camofox scraping)"""
        templates = {
            "technology": [
                ("AI coding assistants are getting scary good", 2847, 342),
                ("New open-source model beats GPT-4", 1923, 256),
                ("The state of web frameworks in 2025", 1456, 189),
            ],
            "business": [
                ("How I built a $50k/month side hustle", 3421, 567),
                ("The future of remote work", 2156, 423),
                ("Startup funding winter is ending", 1892, 312),
            ],
            "startups": [
                ("YC W26 batch applications open", 4521, 892),
                ("Solo founder playbook 2025", 2134, 445),
                ("How to find your first 100 users", 1876, 334),
            ],
            "Entrepreneur": [
                ("From $0 to $1M ARR in 18 months", 5234, 1023),
                ("The psychology of pricing", 1654, 289),
                ("Building in public: lessons learned", 1432, 198),
            ],
        }
        
        trends = []
        for title, upvotes, comments in templates.get(subreddit, []):
            trends.append(TrendItem(
                id=f"reddit_{subreddit}_{hash(title) % 10000}",
                source=SourceType.REDDIT,
                title=title,
                url=f"https://reddit.com/r/{subreddit}/comments/{hash(title) % 1000000}",
                engagement_score=upvotes,
                comment_count=comments,
                category=subreddit,
                source_subreddit=subreddit,
                summary=f"Hot discussion in r/{subreddit} about {title[:30]}...",
                keywords=[subreddit, "trending", "discussion"],
                monetization_angle=f"Create guide about {title[:40]}"
            ))
        
        return trends
    
    def _generate_hn_trends(self, page: str) -> List[TrendItem]:
        """Generate sample HN trends"""
        templates = {
            "frontpage": [
                ("Show HN: I built an open-source alternative to ChatGPT", 234, 89),
                ("The end of software engineering as we know it", 456, 234),
                ("How to bootstrap a SaaS to $10k MRR", 378, 156),
            ],
            "new": [
                ("Launching my first AI product", 23, 12),
                ("Reflections on 10 years of startups", 45, 23),
                ("The state of AI infrastructure", 67, 34),
            ],
        }
        
        trends = []
        for title, points, comments in templates.get(page, []):
            trends.append(TrendItem(
                id=f"hn_{page}_{hash(title) % 10000}",
                source=SourceType.HACKERNEWS,
                title=title,
                url=f"https://news.ycombinator.com/item?id={hash(title) % 10000000}",
                engagement_score=points,
                comment_count=comments,
                category="tech",
                hn_rank=1,
                summary=f"HN {page}: {title[:40]}...",
                keywords=["hackernews", "tech", "startup"],
                monetization_angle=f"Write analysis of {title[:40]}"
            ))
        
        return trends
    
    def _generate_ph_trends(self, category: str) -> List[TrendItem]:
        """Generate sample ProductHunt trends"""
        templates = {
            "daily": [
                ("AI Video Editor Pro", 892, 123),
                ("Notion AI Assistant", 756, 98),
                ("Crypto Tax Calculator 2025", 634, 87),
            ],
            "tech": [
                ("DevOps Automation Suite", 445, 67),
                ("Open Source Analytics", 334, 45),
                ("Serverless Framework v5", 223, 34),
            ],
            "ai": [
                ("Local LLM Manager", 567, 89),
                ("AI Image Generator", 445, 67),
                ("Chatbot Builder", 334, 45),
            ],
            "productivity": [
                ("Focus Timer 2.0", 334, 56),
                ("Task Automation Tool", 223, 34),
                ("Meeting Summarizer", 178, 28),
            ],
        }
        
        trends = []
        for title, upvotes, comments in templates.get(category, []):
            trends.append(TrendItem(
                id=f"ph_{category}_{hash(title) % 10000}",
                source=SourceType.PRODUCTHUNT,
                title=title,
                url=f"https://producthunt.com/posts/{title.lower().replace(' ', '-')}",
                engagement_score=upvotes,
                comment_count=comments,
                category=category,
                ph_topic=category,
                summary=f"ProductHunt {category}: {title}",
                keywords=["producthunt", category, "launch"],
                monetization_angle=f"Review {title} with affiliate links"
            ))
        
        return trends
    
    def _generate_twitter_trends(self, keyword: str) -> List[TrendItem]:
        """Generate sample Twitter trends"""
        templates = {
            "AI tools": [
                ("This new AI tool just saved me 10 hours", 5234, 892),
                ("AI agents are the future of work", 4456, 723),
                ("Build an AI startup in 2025", 3345, 567),
            ],
            "startup funding": [
                ("We just raised $2M pre-seed", 8923, 1234),
                ("VCs are back to funding AI", 5678, 892),
                ("Bootstrapped vs VC funding", 3345, 445),
            ],
            "passive income": [
                ("How I make $10k/month passively", 12345, 2345),
                ("Digital products that sell forever", 6789, 1234),
                ("Affiliate marketing guide 2025", 4567, 892),
            ],
            "side hustle": [
                ("Side hustle that pays $5k/month", 8923, 1567),
                ("Quit my job for this side project", 6789, 1234),
                ("Weekend side hustle ideas", 4456, 723),
            ],
            "tech trends": [
                ("The next big tech trend", 5678, 892),
                ("What to build in 2025", 4456, 634),
                ("Tech skills that pay $200k+", 3345, 445),
            ],
        }
        
        trends = []
        for title, likes, retweets in templates.get(keyword, []):
            trends.append(TrendItem(
                id=f"twitter_{keyword.replace(' ', '_')}_{hash(title) % 10000}",
                source=SourceType.TWITTER,
                title=title,
                url=f"https://twitter.com/i/status/{hash(title) % 100000000000}",
                engagement_score=likes,
                comment_count=retweets,
                category=keyword,
                summary=f"Twitter trending: {title[:40]}...",
                keywords=["twitter", keyword.replace(' ', '_'), "viral"],
                monetization_angle=f"Create Twitter thread about {title[:40]}"
            ))
        
        return trends
    
    def get_top_trends(self, limit: int = 10) -> List[TrendItem]:
        """Get top N trends by engagement"""
        sorted_trends = sorted(
            self.discovered_trends,
            key=lambda x: x.engagement_score,
            reverse=True
        )
        return sorted_trends[:limit]
    
    def get_trends_by_source(self) -> Dict[str, List[TrendItem]]:
        """Group trends by source platform"""
        by_source = {}
        for trend in self.discovered_trends:
            source = trend.source.value
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(trend)
        return by_source
    
    def get_source_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics for each source"""
        by_source = self.get_trends_by_source()
        stats = {}
        
        for source, trends in by_source.items():
            total_engagement = sum(t.engagement_score for t in trends)
            total_comments = sum(t.comment_count for t in trends)
            
            stats[source] = {
                "count": len(trends),
                "total_engagement": total_engagement,
                "total_comments": total_comments,
                "avg_engagement": total_engagement // max(len(trends), 1)
            }
        
        return stats


# FastAPI endpoints for multi-source scout
from fastapi import APIRouter

scout_router = APIRouter(prefix="/scout", tags=["scout"])

# Global scout instance
_multi_source_scout: Optional[MultiSourceScout] = None


def init_multi_source_scout(camofox_client=None):
    """Initialize the multi-source scout"""
    global _multi_source_scout
    _multi_source_scout = MultiSourceScout(camofox_client)


@scout_router.post("/discover")
async def discover_trends():
    """Run scouts across all sources"""
    if not _multi_source_scout:
        return {"error": "Scout not initialized"}
    
    trends = await _multi_source_scout.scout_all_sources()
    
    return {
        "trends": [t.to_dict() for t in trends],
        "count": len(trends),
        "by_source": {
            source: len(items) 
            for source, items in _multi_source_scout.get_trends_by_source().items()
        }
    }


@scout_router.get("/trends")
async def get_trends(limit: int = 10):
    """Get top trends"""
    if not _multi_source_scout:
        return {"error": "Scout not initialized"}
    
    trends = _multi_source_scout.get_top_trends(limit)
    
    return {
        "trends": [t.to_dict() for t in trends],
        "count": len(trends)
    }


@scout_router.get("/stats")
async def get_source_stats():
    """Get statistics by source"""
    if not _multi_source_scout:
        return {"error": "Scout not initialized"}
    
    stats = _multi_source_scout.get_source_stats()
    
    return {
        "stats": stats,
        "total_trends": len(_multi_source_scout.discovered_trends)
    }
