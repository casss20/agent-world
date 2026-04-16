"""
growth_executor.py — Agent World

Execution logic for Growth agent (organic growth, SEO, content, email, partnerships).
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ContentResult:
    """Result of content creation"""
    success: bool
    content_type: str  # blog_post, email, social_post, video_script
    title: str
    content: str
    seo_score: Optional[int]  # 0-100
    keywords_targeted: List[str]
    estimated_read_time: Optional[int]  # minutes
    call_to_action: str


@dataclass
class SEOAnalysis:
    """SEO analysis result"""
    keyword: str
    search_volume: int  # monthly
    difficulty: int  # 0-100
    current_rank: Optional[int]
    competitor_count: int
    opportunity_score: float  # 0-1
    suggested_title: str
    suggested_meta_description: str


class GrowthExecutor:
    """Executes Growth agent organic growth tasks"""
    
    def __init__(self, web_search_tool, ledger_client):
        self.web_search = web_search_tool
        self.ledger = ledger_client
        self.content_calendar: List[Dict] = []
        self.email_sequences: Dict[str, List[Dict]] = {}
        self.affiliate_partnerships: List[Dict] = []
    
    async def execute(self, agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Growth task.
        
        Task types:
        - keyword_research: Find SEO opportunities
        - draft_content: Create blog/email/social content
        - seo_optimize: Optimize existing content
        - email_campaign: Create/send email sequence
        - affiliate_outreach: Draft partner outreach
        - influencer_contact: Draft influencer pitch
        - content_calendar: Plan publishing schedule
        """
        task_type = task.get("task_type")
        payload = task.get("payload", {})
        
        logger.info(f"[Growth:{agent_id}] Executing {task_type}")
        
        if task_type == "keyword_research":
            return await self._keyword_research(agent_id, payload)
        elif task_type == "draft_content":
            return await self._draft_content(agent_id, payload)
        elif task_type == "seo_optimize":
            return await self._seo_optimize(agent_id, payload)
        elif task_type == "email_campaign":
            return await self._email_campaign(agent_id, payload)
        elif task_type == "content_calendar":
            return await self._content_calendar(agent_id, payload)
        elif task_type == "affiliate_outreach":
            return await self._affiliate_outreach(agent_id, payload)
        elif task_type == "influencer_contact":
            return await self._influencer_contact(agent_id, payload)
        elif task_type == "competitor_analysis":
            return await self._competitor_analysis(agent_id, payload)
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _keyword_research(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Research keywords for SEO"""
        seed_keywords = payload.get("seed_keywords", [])
        product_topic = payload.get("product_topic", "")
        
        results = []
        
        # Simulate keyword research (would use SEMrush/Ahrefs API)
        for seed in seed_keywords:
            await asyncio.sleep(0.5)  # Simulate API call
            
            # Mock analysis
            analysis = SEOAnalysis(
                keyword=seed,
                search_volume=1200 + hash(seed) % 8800,  # 1,200 - 10,000
                difficulty=30 + hash(seed) % 60,  # 30-90
                current_rank=None,
                competitor_count=5 + hash(seed) % 20,
                opportunity_score=0.6 + (hash(seed) % 30) / 100,
                suggested_title=f"The Ultimate Guide to {seed.title()}: 10 Proven Strategies",
                suggested_meta_description=f"Discover the best {seed} techniques for 2026. Expert tips, actionable advice, and free resources included."
            )
            
            results.append({
                "keyword": analysis.keyword,
                "search_volume": analysis.search_volume,
                "difficulty": analysis.difficulty,
                "opportunity_score": round(analysis.opportunity_score, 2),
                "suggested_title": analysis.suggested_title,
                "suggested_meta_description": analysis.suggested_meta_description,
                "priority": "high" if analysis.opportunity_score > 0.7 else "medium"
            })
        
        # Sort by opportunity score
        results.sort(key=lambda x: x["opportunity_score"], reverse=True)
        
        return {
            "success": True,
            "seed_keywords": seed_keywords,
            "opportunities": results,
            "top_recommendation": results[0] if results else None,
            "total_monthly_volume": sum(r["search_volume"] for r in results)
        }
    
    async def _draft_content(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Draft blog post, email, or social content"""
        content_type = payload.get("content_type")  # blog, email, social, video_script
        topic = payload.get("topic", "")
        target_keywords = payload.get("target_keywords", [])
        tone = payload.get("tone", "professional")  # professional, casual, educational, humorous
        
        # Content structure based on type
        if content_type == "blog":
            result = await self._draft_blog_post(topic, target_keywords, tone, payload)
        elif content_type == "email":
            result = await self._draft_email(topic, target_keywords, tone, payload)
        elif content_type == "social":
            result = await self._draft_social(topic, target_keywords, tone, payload)
        elif content_type == "video_script":
            result = await self._draft_video_script(topic, target_keywords, tone, payload)
        else:
            return {"success": False, "error": f"Unknown content type: {content_type}"}
        
        return {
            "success": result.success,
            "content_type": result.content_type,
            "title": result.title,
            "content": result.content,
            "seo_score": result.seo_score,
            "keywords_targeted": result.keywords_targeted,
            "estimated_read_time": result.estimated_read_time,
            "call_to_action": result.call_to_action,
            "requires_approval": True  # All external content needs approval
        }
    
    async def _draft_blog_post(self, topic: str, keywords: List[str], tone: str, payload: Dict) -> ContentResult:
        """Draft a blog post"""
        await asyncio.sleep(1)  # Simulate writing
        
        title = f"5 {topic.title()} Strategies That Actually Work in 2026"
        
        content = f"""# {title}

## Introduction

Looking for effective {topic} solutions? You're in the right place. After analyzing hundreds of success stories and consulting with industry experts, we've identified the strategies that consistently deliver results.

## 1. Start with the Foundation

The first step in any successful {topic} journey is understanding your baseline. Take time to assess where you are now before making any major changes.

[Keywords: {', '.join(keywords[:2])}]

## 2. Leverage Proven Systems

Don't reinvent the wheel. The most successful practitioners of {topic} use established frameworks that have been tested and refined over time.

## 3. Focus on Consistency Over Intensity

Small, daily actions compound into massive results. It's better to do a little each day than to burn out with sporadic bursts of activity.

## 4. Measure and Adjust

What gets measured gets managed. Track your progress with simple metrics and be willing to pivot when something isn't working.

## 5. Build Your Support Network

Surround yourself with others who are on the same journey. The accountability and shared learning will accelerate your progress.

## Conclusion

{topic.title()} doesn't have to be complicated. By following these five strategies, you'll be well on your way to achieving your goals. Remember: progress, not perfection.

---

**Ready to get started?** Check out our [product/resource] designed specifically to help you implement strategy #2 with ease.
"""
        
        return ContentResult(
            success=True,
            content_type="blog_post",
            title=title,
            content=content,
            seo_score=75,
            keywords_targeted=keywords,
            estimated_read_time=5,
            call_to_action=f"Learn more about {topic} solutions"
        )
    
    async def _draft_email(self, topic: str, keywords: List[str], tone: str, payload: Dict) -> ContentResult:
        """Draft an email for a sequence"""
        email_type = payload.get("email_type", "welcome")  # welcome, launch, nurture, abandoned_cart
        
        templates = {
            "welcome": {
                "subject": f"Welcome! Here's your {topic} starter guide",
                "body": f"""Hi there,

Welcome to the community! I'm excited you've decided to explore {topic} with us.

As promised, here's your getting-started resource: [LINK]

Over the next few days, I'll be sharing:
• The #1 mistake most people make with {topic}
• A simple 5-minute daily practice that changes everything
• Case studies from people just like you

Talk soon,
[Name]

P.S. Reply to this email and let me know your biggest question about {topic}. I read every response!
"""
            },
            "launch": {
                "subject": f"🚀 {topic.title()} solution is now live (24-hour early bird)",
                "body": f"""Hey,

It's here! After months of development and testing, our {topic} solution is officially live.

**Early bird special:** 30% off for the next 24 hours only.

[Get it now →]

Here's what early users are saying:
"This completely changed how I approach {topic}. Worth every penny." - Sarah M.

Questions? Just reply to this email.

[Name]
"""
            },
            "nurture": {
                "subject": f"Quick question about your {topic} goals",
                "body": f"""Hi,

I was thinking about you today and wondering: what's your biggest challenge with {topic} right now?

I've helped hundreds of people overcome obstacles like:
• Information overload
• Lack of consistent progress
• Not knowing where to start

If any of those resonate, I have a resource that might help.

Just reply and let me know.

Best,
[Name]
"""
            }
        }
        
        template = templates.get(email_type, templates["welcome"])
        
        return ContentResult(
            success=True,
            content_type="email",
            title=template["subject"],
            content=template["body"],
            seo_score=None,
            keywords_targeted=keywords,
            estimated_read_time=2,
            call_to_action=f"Reply or click to learn more about {topic}"
        )
    
    async def _draft_social(self, topic: str, keywords: List[str], tone: str, payload: Dict) -> ContentResult:
        """Draft social media post"""
        platform = payload.get("platform", "instagram")  # instagram, twitter, tiktok, pinterest
        
        posts = {
            "instagram": f"""✨ 3 things I wish I knew about {topic} before I started:

1. Start small, think big
2. Consistency beats intensity  
3. Community > Competition

Save this for later ↗️

#{topic.replace(' ', '')} #tips #2026""",
            
            "twitter": f"""The 3-step {topic} framework:

1. Assess
2. Act  
3. Adjust

Rinse and repeat.

What step do you get stuck on?""",
            
            "tiktok": f"""POV: You finally figured out {topic}

[Hook: "I wasted 2 years doing this wrong..."]

[Value: 3 quick tips with visual demonstration]

[CTA: "Follow for more daily tips"]

#storytime #fyp #learnontiktok""",
            
            "pinterest": f"""{topic.title()} Checklist: 10 Things to Do This Week

☐ Set your baseline
☐ Choose your focus area  
☐ Set a small daily goal
☐ Track progress
☐ Celebrate wins
☐ [6 more items...]

Save this pin for your weekly reset! 📌

#{topic.replace(' ', '')} #checklist #printable"""
        }
        
        content = posts.get(platform, posts["instagram"])
        
        return ContentResult(
            success=True,
            content_type="social_post",
            title=f"{platform.title()} post about {topic}",
            content=content,
            seo_score=None,
            keywords_targeted=keywords,
            estimated_read_time=1,
            call_to_action=f"Follow for more {topic} tips"
        )
    
    async def _draft_video_script(self, topic: str, keywords: List[str], tone: str, payload: Dict) -> ContentResult:
        """Draft a video script"""
        video_type = payload.get("video_type", "educational")  # educational, storytime, review
        duration = payload.get("duration_seconds", 60)
        
        script = f"""[HOOK - 0-3 seconds]
"Stop scrolling! If you're struggling with {topic}, this is for you."

[PROBLEM - 3-10 seconds]
"Most people approach {topic} completely wrong. They try to do everything at once and burn out."

[SOLUTION - 10-45 seconds]
"Here's the 3-step system that actually works:
Step 1: [Brief explanation]
Step 2: [Brief explanation]  
Step 3: [Brief explanation]

[PROOF - 45-50 seconds]
"I used this exact system with 100+ clients and the results speak for themselves."

[CTA - 50-60 seconds]
"Follow for the full breakdown, or check the link in bio for the complete guide."
"""
        
        return ContentResult(
            success=True,
            content_type="video_script",
            title=f"{duration}s {video_type} video about {topic}",
            content=script,
            seo_score=None,
            keywords_targeted=keywords,
            estimated_read_time=duration // 60,
            call_to_action="Follow or click link in bio"
        )
    
    async def _seo_optimize(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Optimize existing content for SEO"""
        content = payload.get("content", "")
        target_keywords = payload.get("target_keywords", [])
        content_type = payload.get("content_type", "blog")
        
        # Simulate optimization analysis
        await asyncio.sleep(1)
        
        optimizations = []
        
        # Check keyword density
        for keyword in target_keywords:
            count = content.lower().count(keyword.lower())
            density = count / len(content.split())
            
            if density < 0.005:  # Less than 0.5%
                optimizations.append({
                    "type": "keyword_density",
                    "keyword": keyword,
                    "current_count": count,
                    "recommendation": f"Add '{keyword}' 2-3 more times naturally",
                    "priority": "high"
                })
            elif density > 0.025:  # More than 2.5%
                optimizations.append({
                    "type": "keyword_stuffing",
                    "keyword": keyword,
                    "current_count": count,
                    "recommendation": f"Reduce '{keyword}' usage to avoid stuffing",
                    "priority": "medium"
                })
        
        # Check structure
        if "# " not in content:
            optimizations.append({
                "type": "headings",
                "recommendation": "Add H1/H2 headings with target keywords",
                "priority": "high"
            })
        
        if "meta description" not in content.lower():
            optimizations.append({
                "type": "meta",
                "recommendation": "Add meta description (150-160 chars) with primary keyword",
                "priority": "medium"
            })
        
        # Calculate new score
        current_score = payload.get("current_seo_score", 50)
        potential_improvement = len([o for o in optimizations if o["priority"] == "high"]) * 5
        new_score = min(100, current_score + potential_improvement)
        
        return {
            "success": True,
            "content_type": content_type,
            "current_seo_score": current_score,
            "potential_score": new_score,
            "improvement": new_score - current_score,
            "optimizations": optimizations,
            "optimized_content_preview": content[:500] + "..." if len(content) > 500 else content,
            "requires_approval": False  # Content optimization is safe
        }
    
    async def _email_campaign(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Create email campaign sequence"""
        sequence_name = payload.get("sequence_name", "welcome_series")
        email_count = payload.get("email_count", 5)
        product_topic = payload.get("product_topic", "")
        
        sequence = []
        
        email_types = ["welcome", "nurture", "nurture", "nurture", "launch"] if email_count == 5 else ["welcome"] * email_count
        
        for i, email_type in enumerate(email_types[:email_count]):
            email_result = await self._draft_email(
                product_topic, [], "professional",
                {"email_type": email_type}
            )
            
            send_delay_days = [0, 1, 3, 7, 14][i] if i < 5 else i * 2
            
            sequence.append({
                "sequence_position": i + 1,
                "email_type": email_type,
                "subject": email_result.title,
                "content": email_result.content,
                "send_after_days": send_delay_days,
                "requires_approval": True
            })
        
        self.email_sequences[sequence_name] = sequence
        
        return {
            "success": True,
            "sequence_name": sequence_name,
            "email_count": len(sequence),
            "total_sequence_days": sequence[-1]["send_after_days"] if sequence else 0,
            "emails": sequence,
            "requires_approval": True  # All email sends need approval
        }
    
    async def _content_calendar(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Create content publishing calendar"""
        duration_weeks = payload.get("duration_weeks", 4)
        platforms = payload.get("platforms", ["blog", "instagram", "email"])
        product_topic = payload.get("product_topic", "")
        
        calendar = []
        
        for week in range(1, duration_weeks + 1):
            week_content = []
            
            if "blog" in platforms and week % 2 == 1:  # Blog every 2 weeks
                week_content.append({
                    "day": "Monday",
                    "platform": "blog",
                    "content_type": "article",
                    "topic": f"{product_topic} guide - Week {week}",
                    "status": "planned"
                })
            
            if "instagram" in platforms:
                week_content.extend([
                    {"day": "Tuesday", "platform": "instagram", "content_type": "carousel", "topic": f"Tips thread", "status": "planned"},
                    {"day": "Thursday", "platform": "instagram", "content_type": "reel", "topic": f"Quick tip video", "status": "planned"},
                    {"day": "Saturday", "platform": "instagram", "content_type": "story", "topic": f"Behind the scenes", "status": "planned"}
                ])
            
            if "email" in platforms and week == 1:
                week_content.append({
                    "day": "Wednesday",
                    "platform": "email",
                    "content_type": "newsletter",
                    "topic": f"Weekly {product_topic} insights",
                    "status": "planned"
                })
            
            calendar.append({
                "week": week,
                "content": week_content,
                "total_pieces": len(week_content)
            })
        
        self.content_calendar = calendar
        
        total_pieces = sum(w["total_pieces"] for w in calendar)
        
        return {
            "success": True,
            "duration_weeks": duration_weeks,
            "platforms": platforms,
            "total_content_pieces": total_pieces,
            "calendar": calendar,
            "requires_approval": False  # Planning is safe
        }
    
    async def _affiliate_outreach(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Draft affiliate partnership outreach"""
        product_name = payload.get("product_name", "")
        product_price = payload.get("product_price", 0)
        commission_rate = payload.get("commission_rate", 0.30)  # 30%
        target_partner = payload.get("target_partner", "")
        partner_type = payload.get("partner_type", "blogger")  # blogger, influencer, educator
        
        commission_per_sale = product_price * commission_rate
        
        email_template = f"""Subject: Partnership Opportunity - {product_name}

Hi [Name],

I've been following your work on [topic] and really appreciate your thoughtful approach to [specific detail].

I wanted to reach out because I think your audience would genuinely benefit from {product_name}. It's a [brief description] that helps people [key benefit].

Given your expertise in this space, I'd love to offer you:
• {commission_rate*100}% commission on every sale ({commission_per_sale:.2f} per sale at ${product_price})
• Early access to new products and content
• Exclusive discount codes for your audience

Would you be interested in learning more? I'm happy to send over a sample and answer any questions.

No pressure either way — I just think it's a great fit for your community.

Best,
[Your name]

P.S. Here's what one of our affiliates said: "[Testimonial]"
"""
        
        return {
            "success": True,
            "partner_type": partner_type,
            "target_partner": target_partner,
            "outreach_email": email_template,
            "commission_structure": {
                "rate": commission_rate,
                "per_sale": round(commission_per_sale, 2),
                "estimated_monthly": round(commission_per_sale * 10, 2)  # Assuming 10 sales
            },
            "requires_approval": True,  # External partnership communication
            "suggested_follow_up": "3 days after initial send"
        }
    
    async def _influencer_contact(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Draft influencer collaboration pitch"""
        influencer_name = payload.get("influencer_name", "")
        influencer_platform = payload.get("influencer_platform", "instagram")
        product_name = payload.get("product_name", "")
        offer_type = payload.get("offer_type", "gifting")  # gifting, paid, affiliate, collaboration
        
        pitches = {
            "gifting": f"""Subject: Gift for you - {product_name}

Hi {influencer_name},

Big fan of your content! Especially loved your recent post about [specific topic].

I created {product_name} and immediately thought of you. It seems like a perfect fit for your audience who [specific interest].

I'd love to send you a complimentary copy — no strings attached. If you find it valuable and want to share, great. If not, no worries at all.

Just reply with your preferred address and I'll get it shipped right away.

Thanks for the great content you put out!

[Your name]
""",
            "paid": f"""Subject: Paid collaboration - {product_name}

Hi {influencer_name},

I'm reaching out from [brand] with a paid collaboration opportunity.

We love your authentic approach to [topic] and think you'd be a great fit for {product_name}.

Partnership details:
• Product: {product_name}
• Deliverables: 1 in-feed post + 3 stories
• Timeline: Within 2 weeks of receiving product
• Compensation: $[amount] + affiliate commission

Interested? I can send over a detailed brief and contract.

[Your name]
""",
            "affiliate": f"""Subject: Affiliate opportunity - {product_name}

Hi {influencer_name},

Quick question: Do you ever recommend resources for [topic] to your audience?

If so, I think {product_name} could be a great fit. It's [brief value prop].

We offer a 30% affiliate commission, which works out to $X per sale at our current price.

Worth a conversation?

[Your name]
"""
        }
        
        pitch = pitches.get(offer_type, pitches["gifting"])
        
        return {
            "success": True,
            "influencer": influencer_name,
            "platform": influencer_platform,
            "offer_type": offer_type,
            "pitch_email": pitch,
            "requires_approval": True,
            "suggested_compensation": {
                "gifting": "Free product only",
                "paid": "$100-500 per 10k followers",
                "affiliate": "30% commission"
            }.get(offer_type)
        }
    
    async def _competitor_analysis(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Analyze competitor SEO/content strategy"""
        competitor_urls = payload.get("competitor_urls", [])
        target_keywords = payload.get("target_keywords", [])
        
        # Would use web scraping + SEO APIs
        await asyncio.sleep(2)
        
        analysis = []
        for url in competitor_urls:
            analysis.append({
                "competitor": url,
                "top_keywords": target_keywords[:3],  # Simulated
                "content_frequency": "2 posts/week",
                "backlinks_estimated": 150 + hash(url) % 850,
                "domain_authority": 30 + hash(url) % 50,
                "content_gaps": ["video content", "email lead magnets", "user testimonials"],
                "opportunities": [
                    "They don't have a downloadable guide",
                    "No email sequence for nurturing",
                    "Limited Pinterest presence"
                ]
            })
        
        return {
            "success": True,
            "competitors_analyzed": len(analysis),
            "analysis": analysis,
            "key_opportunities": [
                "Create downloadable lead magnet (competitors lack this)",
                "Build email nurture sequence",
                "Invest in Pinterest (underserved channel)",
                "Add video content to blog posts"
            ],
            "requires_approval": False
        }


# Singleton instance
_growth_executor: Optional[GrowthExecutor] = None

def get_growth_executor(web_search_tool=None, ledger_client=None) -> GrowthExecutor:
    global _growth_executor
    if _growth_executor is None:
        _growth_executor = GrowthExecutor(web_search_tool, ledger_client)
    return _growth_executor