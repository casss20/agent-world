"""
youtube_faceless.py — Agent World Business Models

Faceless YouTube channel business model.
Automated content creation without on-camera personality.
Revenue through AdSense, affiliate links, sponsorships, digital products.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from business_models.base import (
    BusinessModel, DiagnosticCheck, BusinessContext,
    Diagnosis, Strategy, Severity, Bottleneck, BottleneckCategory
)


class YouTubeFacelessModel(BusinessModel):
    """
    Business model for faceless YouTube channels.

    Content types:
    - Explainer videos (educational)
    - Listicles ("Top 10...")
    - Documentary-style storytelling
    - Compilation videos
    - AI-generated content

    Revenue streams:
    1. YouTube AdSense (primary, scalable)
    2. Affiliate marketing (high RPM)
    3. Sponsorships (brand deals)
    4. Digital products (courses, templates)
    5. Memberships/Patreon

    Key metrics: Subscribers, watch time, CTR, RPM, upload consistency
    """

    model_id = "youtube_faceless"
    model_name = "Faceless YouTube Channel"
    description = "Create automated faceless YouTube content using AI tools and stock footage"

    # Benchmarks for faceless channels
    typical_rpm_range = (2, 8)  # $2-8 per 1000 views (lower than personal brands)
    ad_sense_threshold = 1000  # subscribers needed
    watch_time_hours = 4000  # hours needed for monetization

    def get_diagnostic_checks(self) -> List[DiagnosticCheck]:
        return [
            NicheCompetitionCheck(),
            ScriptQualityCheck(),
            ThumbnailOptimizationCheck(),
            UploadConsistencyCheck(),
            RetentionAnalysisCheck(),
            MonetizationReadinessCheck(),
        ]

    def get_kpis(self) -> Dict[str, Dict]:
        return {
            "subscribers": {
                "label": "Subscriber Count",
                "target": 1000,  # Monetization threshold
                "good": 10000,
                "excellent": 100000,
                "unit": "subscribers"
            },
            "watch_time_hours": {
                "label": "Watch Time (Hours)",
                "target": 4000,  # Monetization threshold
                "good": 20000,
                "excellent": 100000,
                "unit": "hours"
            },
            "avg_view_duration": {
                "label": "Avg View Duration",
                "target": 0.40,  # 40% retention
                "good": 0.50,
                "excellent": 0.60,
                "unit": "percentage"
            },
            "ctr": {
                "label": "Click-Through Rate",
                "target": 0.04,  # 4%
                "good": 0.06,
                "excellent": 0.10,
                "unit": "percentage"
            },
            "rpm": {
                "label": "Revenue Per 1K Views",
                "target": 2,
                "good": 5,
                "excellent": 10,
                "unit": "usd"
            },
            "upload_frequency": {
                "label": "Videos Per Week",
                "target": 1,
                "good": 2,
                "excellent": 3,
                "unit": "videos"
            }
        }


# ============================================================================
# Diagnostic Checks
# ============================================================================

class NicheCompetitionCheck(DiagnosticCheck):
    """Analyze niche competition and opportunity for faceless content"""

    check_id = "niche_competition"
    name = "Niche Competition Analysis"
    description = "Checks if niche is oversaturated and suggests underserved sub-niches"

    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        niche = context.niche or "general"
        metrics = context.metrics or {}

        # High-opportunity faceless niches (underserved)
        high_opportunity = [
            "b2b_software_explained", "financial_literacy_genz", "adhd_productivity",
            "historical_mysteries", "science_explained_simple", "ai_tools_reviews",
            "career_transition_guides", "mental_health_coping", "small_business_tutorials",
            "passive_income_beginners", "coding_for_non_coders", "design_principles"
        ]

        # Saturated faceless niches (hard to break in)
        saturated = [
            "luxury_lifestyle", "generic_motivation", "gaming_highlights",
            "reaction_videos", "top_10_lists_generic", "movie_recaps",
            "funny_compilations"
        ]

        opportunity_score = 50
        issues = []

        if niche in high_opportunity:
            opportunity_score = 85
            status = "high_opportunity"
        elif niche in saturated:
            opportunity_score = 25
            status = "saturated"
            issues.append("Niche oversaturated - faceless content very competitive")
        else:
            status = "moderate"

        # Check faceless-specific factors
        top_channels_in_niche = metrics.get("top_channels_avg_views", 100000)
        if top_channels_in_niche > 500000:
            issues.append("Top channels getting 500k+ views - high competition")

        return {
            "score": opportunity_score,
            "niche": niche,
            "status": status,
            "issues": issues,
            "faceless_specific_factors": {
                "voiceover_available": metrics.get("has_voiceover_solution", False),
                "stock_footage_budget": metrics.get("stock_footage_budget", 0),
                "script_writing_capacity": metrics.get("can_write_scripts", True)
            },
            "recommendations": [
                "Find sub-niche: 'Personal finance' → 'Gen Z first apartment budgeting'",
                "Check TubeBuddy/VidIQ competition score (aim < 30/100)",
                "Look for niches where top 10 videos average 10k-50k views (not 1M+)",
                "Faceless works best for: educational, explainer, documentary styles"
            ]
        }


class ScriptQualityCheck(DiagnosticCheck):
    """Analyze script quality for voiceover content"""

    check_id = "script_quality"
    name = "Script & Voiceover Quality"
    description = "Evaluates script structure, hook strength, and voiceover quality"

    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        metrics = context.metrics or {}

        avg_view_duration = metrics.get("avg_view_duration", 0)
        avg_percentage = metrics.get("avg_view_percentage", 0)

        issues = []

        # Retention-based quality indicators
        if avg_percentage < 30:
            issues.append("Viewers leaving before 30% - hook or pacing problem")
        if avg_view_duration < 120:  # 2 minutes
            issues.append("Very short watch time - content not engaging enough")

        # Script structure issues
        script_issues = []
        if not metrics.get("has_pattern_interrupts", True):
            script_issues.append("Add pattern interrupts every 30-45 seconds (B-roll, zoom, sound)")
        if not metrics.get("has_clear_hook", True):
            script_issues.append("First 15 seconds must promise specific value/transformation")
        if not metrics.get("has_storytelling", False):
            script_issues.append("Even educational content needs narrative arc (problem → journey → solution)")

        return {
            "score": min(100, int(avg_percentage * 1.5)),
            "avg_retention_percentage": avg_percentage,
            "avg_view_duration_seconds": avg_view_duration,
            "issues": issues + script_issues,
            "script_optimization": {
                "hook_templates": [
                    "'I spent 100 hours researching X so you don't have to...'",
                    "'The [industry] doesn't want you to know this...'",
                    "'Stop doing [common mistake]. Do this instead...'",
                    "'In the next 8 minutes, you'll learn exactly how to...'"
                ],
                "pacing_guidelines": "1 sentence = 3-4 seconds of video. Cut every pause.",
                "voiceover_tips": "Use 11Labs, Murf, or Play.ht. Aim for 140-160 WPM."
            },
            "recommendations": [
                "Start with 'result' in first 5 seconds (what they'll gain)",
                "Use 'you' and 'your' every 3-4 sentences (direct address)",
                "Add cliffhangers before every pattern interrupt",
                "End with clear CTA: 'Subscribe for part 2' or 'Comment if you want template'"
            ]
        }


class ThumbnailOptimizationCheck(DiagnosticCheck):
    """Check thumbnail CTR and optimization"""

    check_id = "thumbnail_optimization"
    name = "Thumbnail & Title Optimization"
    description = "Analyzes click-through rate and thumbnail effectiveness"

    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        metrics = context.metrics or {}

        ctr = metrics.get("ctr", 0)
        impressions = metrics.get("impressions", 0)

        issues = []
        severity = None

        if ctr < 0.02:
            issues.append("CRITICAL: CTR below 2% - thumbnails need complete redesign")
            severity = Severity.CRITICAL
        elif ctr < 0.04:
            issues.append("Warning: CTR below 4% - not competitive for faceless niche")
            severity = Severity.MEDIUM

        # Thumbnail best practices check
        thumb_issues = []
        if not metrics.get("thumbnails_have_faces", False):
            thumb_issues.append("Faceless channels: Use expressive characters/emoji faces instead")
        if not metrics.get("thumbnails_high_contrast", True):
            thumb_issues.append("Low contrast thumbnails - won't pop in dark mode")
        if not metrics.get("thumbnails_simple_text", True):
            thumb_issues.append("Too much text on thumbnail - max 3-4 words")

        return {
            "score": min(100, int(ctr * 2000)),  # 5% CTR = 100 score
            "ctr": ctr,
            "impressions": impressions,
            "severity": severity.value if severity else "none",
            "issues": issues + thumb_issues,
            "thumbnail_formula": {
                "background": "High contrast, simple gradient or blurred image",
                "subject": "Single focal point (person, object, or reaction)",
                "text": "Max 3 words, bold font, yellow/white with black outline",
                "expression": "Surprise, curiosity, or slight fear (clickable emotions)"
            },
            "title_templates": [
                "How I [achieved result] in [timeframe] (Step-by-Step)",
                "The Real Reason [thing] is [outcome] (Not What You Think)",
                "I Tried [thing] for [time]. Here's What Happened...",
                "[Number] [Topic] Mistakes You're Making (+ How to Fix)",
                "Stop [common action]. Start [better action] Instead."
            ],
            "recommendations": [
                "A/B test thumbnails using TubeBuddy or Thumbnail Test",
                "Study MrBeast thumbnails (even for serious topics - curiosity gap)",
                "Use 3-color rule: 1 dominant, 1 accent, 1 text color",
                "Design for mobile: Check thumbnail at 150px wide"
            ]
        }


class UploadConsistencyCheck(DiagnosticCheck):
    """Check upload schedule and consistency"""

    check_id = "upload_consistency"
    name = "Upload Consistency"
    description = "Analyzes if upload frequency supports algorithm favor"

    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        metrics = context.metrics or {}

        videos_per_week = metrics.get("upload_frequency", 0)
        total_videos = metrics.get("total_videos", 0)
        subscriber_count = metrics.get("subscribers", 0)

        issues = []

        # Faceless channels need higher volume for algorithm
        if videos_per_week < 1:
            issues.append("Uploading less than weekly - algorithm won't boost")
        if videos_per_week < 2 and subscriber_count < 10000:
            issues.append("Growth phase needs 2-3x weekly for faceless channels")

        # Content velocity check
        if total_videos < 10:
            issues.append("Need 10+ videos for algorithm to understand your niche")

        # Optimal schedule for faceless
        if subscriber_count < 1000:
            optimal = "2-3 videos/week (establish presence)"
        elif subscriber_count < 10000:
            optimal = "2 videos/week (quality focus)"
        else:
            optimal = "1-2 videos/week (sustainability)"

        return {
            "score": min(100, videos_per_week * 30),  # 3x/week = 90 score
            "videos_per_week": videos_per_week,
            "total_videos": total_videos,
            "optimal_frequency": optimal,
            "issues": issues,
            "content_pipeline": {
                "batch_recording": "Record 4-5 voiceovers in one session",
                "assembly_line": "Script → Voiceover → Stock footage → Edit → Thumbnail",
                "tools": "Canva (thumbs), CapCut (edit), 11Labs (voice), Pexels (footage)"
            },
            "recommendations": [
                "Pick 1 upload day and stick to it religiously",
                "Create content backlog: Always have 3 videos ready",
                "Use YouTube scheduler to post at optimal time (check analytics)",
                "Faceless channels: Batch everything (voice, editing, thumbnails)"
            ]
        }


class RetentionAnalysisCheck(DiagnosticCheck):
    """Analyze audience retention patterns"""

    check_id = "retention_analysis"
    name = "Audience Retention Analysis"
    description = "Identifies where viewers drop off and how to fix it"

    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        metrics = context.metrics or {}

        retention_curve = metrics.get("retention_curve", {})
        avg_duration = metrics.get("avg_view_duration", 0)
        video_length = metrics.get("avg_video_length", 600)  # 10 min default

        # Find drop-off points
        drop_off_points = []
        if retention_curve:
            for time_point, percentage in retention_curve.items():
                if percentage < 50 and int(time_point) > 30:  # After 30 seconds
                    drop_off_points.append((time_point, percentage))

        issues = []
        if avg_duration < (video_length * 0.3):
            issues.append(f"Losing 70%+ of viewers - content not delivering on promise")

        # Common faceless retention killers
        if metrics.get("long_intros", False):
            issues.append("Intro longer than 15 seconds - start with value immediately")
        if metrics.get("no_b_roll", False):
            issues.append("Voiceover without visuals - add stock footage every 3-5 seconds")
        if metrics.get("monotone_voice", False):
            issues.append("Monotone voiceover - use AI voices with emotion or vary pacing")

        return {
            "score": min(100, int((avg_duration / video_length) * 150)),
            "avg_view_duration": avg_duration,
            "video_length_avg": video_length,
            "retention_percentage": round((avg_duration / video_length) * 100, 1) if video_length > 0 else 0,
            "drop_off_points": drop_off_points[:3],  # Top 3 drop-offs
            "issues": issues,
            "retention_hacks": {
                "0-30s": "Hook + Promise + Proof (why they should watch)",
                "30-60s": "First value delivery (quick win or interesting fact)",
                "1-3min": "Pattern interrupt (B-roll, zoom, sound effect, graphic)",
                "3-8min": "Build tension, tease big reveal coming",
                "8min+": "Main value delivery, keep teasing conclusion",
                "end": "Clear CTA + 'Subscribe for more [specific benefit]'"
            },
            "recommendations": [
                "Check retention graph at 30s, 2min, 5min - fix those cliffs",
                "Add 'coming up' teasers at 25% and 50% marks",
                "Remove every section that doesn't serve the main promise",
                "End every video with question to drive comments (engagement = boost)"
            ]
        }


class MonetizationReadinessCheck(DiagnosticCheck):
    """Check if channel ready for monetization and beyond"""

    check_id = "monetization_ready"
    name = "Monetization Readiness"
    description = "Analyzes path to AdSense and other revenue streams"

    async def run(self, context: BusinessContext) -> Dict[str, Any]:
        metrics = context.metrics or {}

        subscribers = metrics.get("subscribers", 0)
        watch_time = metrics.get("watch_time_hours", 0)

        issues = []
        ready_for_adsense = subscribers >= 1000 and watch_time >= 4000

        if not ready_for_adsense:
            remaining_subs = max(0, 1000 - subscribers)
            remaining_time = max(0, 4000 - watch_time)

            if remaining_subs > 0:
                issues.append(f"Need {remaining_subs} more subscribers for AdSense")
            if remaining_time > 0:
                issues.append(f"Need {remaining_time} more watch hours for AdSense")

        # Revenue stream readiness
        revenue_readiness = {
            "adsense": ready_for_adsense,
            "affiliate": subscribers >= 100,  # Can start early
            "sponsorships": subscribers >= 5000,  # Micro-influencer threshold
            "merch": subscribers >= 10000,
            "digital_products": subscribers >= 5000  # Email list building
        }

        # Calculate potential earnings
        avg_views = metrics.get("avg_views", 0)
        rpm = metrics.get("rpm", 4)  # Conservative for faceless

        potential_monthly = 0
        if ready_for_adsense and avg_views > 0:
            monthly_views = avg_views * 4  # 4 videos/month
            potential_monthly = (monthly_views / 1000) * rpm

        return {
            "score": 100 if ready_for_adsense else int((subscribers / 1000) * 40 + (watch_time / 4000) * 60),
            "adsense_ready": ready_for_adsense,
            "current_subscribers": subscribers,
            "current_watch_time": watch_time,
            "blockers": issues,
            "revenue_readiness": revenue_readiness,
            "potential_earnings": {
                "monthly_adsense_estimate": round(potential_monthly, 2),
                "based_on_rpm": rpm,
                "assumption": "4 videos/month at current avg views"
            },
            "fastest_monetization_path": [
                "1. Affiliate links in description (can do now)",
                "2. Hit 1k subs/4k hours (focus: retention + consistency)",
                "3. Digital product (canva template, notion) at 5k subs",
                "4. Sponsorships (reach out at 5k with high engagement)"
            ],
            "recommendations": [
                "Even before AdSense: Add affiliate links to tools mentioned",
                "Create 'free resource' to collect emails (future product launch)",
                "Design merch/mockups now, launch when you hit 10k",
                "Track which topics have highest RPM (finance > gaming)"
            ]
        }


# ============================================================================
# Strategy Generation
# ============================================================================

class YouTubeFacelessStrategyGenerator:
    """Generate strategies specific to faceless YouTube growth"""

    @staticmethod
    def get_strategies(diagnosis: Diagnosis, context: BusinessContext) -> List[Strategy]:
        strategies = []
        metrics = context.metrics or {}

        subscribers = metrics.get("subscribers", 0)
        videos_count = metrics.get("total_videos", 0)

        # Early stage: Volume + Learning
        if subscribers < 1000 or videos_count < 10:
            strategies.append(Strategy(
                strategy_id="volume_sprint",
                name="30-Day Volume Sprint",
                description="Publish 10-12 videos in 30 days to establish presence and learn what works",
                expected_impact="1000+ subscribers, identify winning content formula",
                effort_hours=40,  # 10-12 videos
                cost_usd=0,  # Free tools
                steps=[
                    "Choose 3 sub-topics in your niche (e.g., finance: budgeting, investing, side hustles)",
                    "Script 12 videos using AI (Claude/ChatGPT) - 1000-1500 words each",
                    "Record voiceovers in 2-3 batch sessions using 11Labs or your voice",
                    "Source free stock footage (Pexels, Pixabay) for each video",
                    "Edit in CapCut (free) - simple cuts, add B-roll every 3-5 seconds",
                    "Create thumbnails in Canva (use templates, adjust for each)",
                    "Upload 3x/week for 4 weeks, post at same time",
                    "After 30 days: Analyze which 2-3 videos performed best",
                    "Double down on winning format/topic for next month"
                ],
                tools=["create_blog_post", "schedule_social_content", "keyword_research"]
            ))

        # Mid stage: Optimization
        if subscribers >= 1000:
            strategies.append(Strategy(
                strategy_id="retention_optimization",
                name="Retention Optimization Protocol",
                description="A/B test hooks, thumbnails, and pacing to maximize watch time",
                expected_impact="+20-40% retention, faster subscriber growth",
                effort_hours=20,
                cost_usd=0,
                steps=[
                    "For next 6 videos, create 2 thumbnails each (A/B test)",
                    "Test 3 different hook styles: Question, Result, Mistake",
                    "Add pattern interrupt every 30 seconds (B-roll, zoom, text)",
                    "Check retention graphs at 30s, 2min, 5min - fix drop-offs",
                    "Remove any 10+ second section without visual change",
                    "End every video with specific CTA + 'Part 2 coming' tease",
                    "Track CTR and retention for each variant",
                    "Standardize winning formula for next batch"
                ],
                tools=["optimize_content_seo", "broadcast_to_room"]
            ))

        # Monetization focus
        if subscribers >= 1000:
            strategies.append(Strategy(
                strategy_id="affiliate_revenue",
                name="Affiliate Revenue Stream",
                description="Add affiliate links to every video for passive income",
                expected_impact="$200-1000/month additional revenue",
                effort_hours=5,
                cost_usd=0,
                steps=[
                    "List all tools/software mentioned in your last 10 videos",
                    "Sign up for Amazon Associates, ShareASale, individual programs",
                    "Add links to description with timestamps (higher CTR)",
                    "Mention 'link in description' verbally in video",
                    "Create 'resources' page using Stan Store or Beacons",
                    "Track which links get clicks (Amazon reports)",
                    "Double down on content around high-converting products"
                ],
                tools=["find_affiliates", "revenue_routes"]
            ))

        # Scaling stage
        if subscribers >= 5000:
            strategies.append(Strategy(
                strategy_id="digital_product_launch",
                name="Digital Product Launch",
                description="Create and sell template/guide to your established audience",
                expected_impact="$2000-10000 launch, $500-2000/month ongoing",
                effort_hours=30,
                cost_usd=50,  # Canva Pro, Gumroad fees
                steps=[
                    "Survey audience: 'What would you pay $27 for?'",
                    "Create simple digital product (Notion template, Canva pack, guide)",
                    "Build email list with 'freebie' before launch",
                    "Create 3-video launch sequence: Problem → Solution → Offer",
                    "Use Gumroad (free) or Stan Store for checkout",
                    "Price at $19-49 (impulse buy range)",
                    "Launch with limited-time discount (urgency)",
                    "Follow up with testimonial/review videos"
                ],
                tools=["create_email_sequence", "broadcast_to_room", "revenue_routes"]
            ))

        # Always applicable: SEO
        strategies.append(Strategy(
            strategy_id="seo_optimization",
            name="YouTube SEO Optimization",
            description="Optimize titles, descriptions, and tags for search traffic",
            expected_impact="+30-50% views from search (long-term passive traffic)",
            effort_hours=10,
            cost_usd=0,
            steps=[
                "Install TubeBuddy or VidIQ (free versions)",
                "Research keywords: Aim for 1k-10k monthly searches, score <30",
                "Rewrite last 10 video titles using keyword + curiosity gap",
                "Add timestamps to descriptions (boosts SEO)",
                "Create playlists around keyword clusters",
                "Design end screens that promote playlist (not just subscribe)",
                "Pin comment with keyword-rich question (engagement)",
                "Link related videos in description and cards"
            ],
            tools=["keyword_research", "optimize_content_seo"]
        ))

        return strategies
