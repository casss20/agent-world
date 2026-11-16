"""
youtube_faceless.py — Agent World

Faceless YouTube channel business model.

Automated content creation without on-camera personality.
Revenue through AdSense, affiliate links, sponsorships, digital products.

Key metrics: subscribers, watch time, CTR, RPM, upload consistency.

Migrated to the current BusinessModel interface: checks return CheckResult,
strategies live in a static library keyed by BottleneckCategory.
"""

from typing import Dict, List

from .base import (
    BusinessModel, DiagnosticCheck, CheckResult, BottleneckCategory,
    Severity, Evidence, BusinessContext, Strategy,
    KPITracking
)


# ============================================================================
# Diagnostic Checks
# ============================================================================

class NicheCompetitionCheck(DiagnosticCheck):
    """Analyze niche competition and opportunity for faceless content"""

    HIGH_OPPORTUNITY = [
        "b2b_software_explained", "financial_literacy_genz", "adhd_productivity",
        "historical_mysteries", "science_explained_simple", "ai_tools_reviews",
        "career_transition_guides", "mental_health_coping", "small_business_tutorials",
        "passive_income_beginners", "coding_for_non_coders", "design_principles"
    ]
    SATURATED = [
        "luxury_lifestyle", "generic_motivation", "gaming_highlights",
        "reaction_videos", "top_10_lists_generic", "movie_recaps",
        "funny_compilations"
    ]

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.ACQUISITION

    @property
    def name(self) -> str:
        return "Niche Competition Analysis"

    async def run(self, context: BusinessContext) -> CheckResult:
        niche = context.current_metrics.get("niche", "general")
        top_channels_in_niche = context.current_metrics.get("top_channels_avg_views", 100000)

        # Faceless-specific production capacity factors
        voiceover_available = bool(context.current_metrics.get("has_voiceover_solution", 0))
        footage_budget = context.current_metrics.get("stock_footage_budget", 0)
        can_write_scripts = bool(context.current_metrics.get("can_write_scripts", 1))

        evidence = [Evidence(
            metric="opportunity_score",
            value=50 if niche not in self.HIGH_OPPORTUNITY and niche not in self.SATURATED else (85 if niche in self.HIGH_OPPORTUNITY else 25),
            benchmark=50,
            gap_percentage=0 if niche in self.HIGH_OPPORTUNITY else (50 if niche in self.SATURATED else 0),
            source="heuristic"
        )]

        production_ready = voiceover_available and can_write_scripts

        if niche in self.HIGH_OPPORTUNITY:
            if not production_ready:
                return CheckResult(
                    category=self.category,
                    status=Severity.MEDIUM,
                    description=(
                        f"Niche '{niche}' is high-opportunity for faceless content, but production "
                        f"capacity is incomplete (voiceover: {voiceover_available}, script writing: {can_write_scripts}). "
                        "Faceless works best for: educational, explainer, documentary styles."
                    ),
                    severity=Severity.MEDIUM,
                    estimated_impact="Fixing the missing production piece (voiceover or scripts) unlocks an underserved niche",
                    evidence=evidence
                )
            return CheckResult(
                category=self.category,
                status=Severity.HEALTHY,
                description=(
                    f"Niche '{niche}' is underserved — strong opportunity for faceless content. "
                    "Aim for sub-niche angles (e.g. 'Personal finance' → 'Gen Z first apartment budgeting'); "
                    "check TubeBuddy/VidIQ competition score (aim < 30/100)."
                ),
                severity=Severity.HEALTHY,
                estimated_impact="Lower competition makes ranking and growth significantly easier",
                evidence=evidence
            )
        if niche in self.SATURATED:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=(
                    f"Niche '{niche}' is oversaturated — faceless content here is very competitive. "
                    "Look for niches where top 10 videos average 10k-50k views (not 1M+)."
                ),
                severity=Severity.HIGH,
                estimated_impact="High competition means slow organic growth without a clear sub-niche angle",
                evidence=evidence
            )
        # Moderate/unknown niche — check top-channel competition
        if top_channels_in_niche > 500000:
            evidence.append(Evidence(
                metric="top_channels_avg_views",
                value=top_channels_in_niche,
                benchmark=500000,
                gap_percentage=0,
                source="user_input"
            ))
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=(
                    f"Niche '{niche}' has top channels getting {top_channels_in_niche:,.0f}+ average views — "
                    "high competition. Find a sub-niche where the top videos average 10k-50k views."
                ),
                severity=Severity.HIGH,
                estimated_impact="Competing against 500k+ view incumbents caps breakout odds without differentiation",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.MEDIUM,
            description=(
                f"Niche '{niche}' has moderate competition (top channels ~{top_channels_in_niche:,.0f} avg views). "
                "Differentiation and a micro-niche angle will improve breakout odds."
            ),
            severity=Severity.MEDIUM,
            estimated_impact="A sharper sub-niche focus would improve ranking odds",
            evidence=evidence
        )


class ThumbnailOptimizationCheck(DiagnosticCheck):
    """Check thumbnail CTR and optimization"""

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.ACQUISITION

    @property
    def name(self) -> str:
        return "Thumbnail & Title Optimization"

    async def run(self, context: BusinessContext) -> CheckResult:
        metrics = context.current_metrics

        ctr = metrics.get("ctr", 0)
        impressions = metrics.get("impressions", 0)

        # Thumbnail best-practice flags from metrics
        has_faces = bool(metrics.get("thumbnails_have_faces", 0))
        high_contrast = bool(metrics.get("thumbnails_high_contrast", 1))
        simple_text = bool(metrics.get("thumbnails_simple_text", 1))

        issues = []
        practice_downgrade = 0

        if not has_faces:
            issues.append("Faceless channels: use expressive characters/emoji faces instead of real faces")
            practice_downgrade += 1
        if not high_contrast:
            issues.append("Low-contrast thumbnails won't pop in dark mode")
            practice_downgrade += 1
        if not simple_text:
            issues.append("Too much text on thumbnail — max 3-4 words")
            practice_downgrade += 1

        evidence = [Evidence(
            metric="ctr",
            value=ctr,
            benchmark=0.04,
            gap_percentage=max(0.0, (0.04 - ctr) / 0.04 * 100),
            source="user_input"
        )]
        if impressions:
            evidence.append(Evidence(
                metric="impressions",
                value=impressions,
                benchmark=0,
                gap_percentage=0,
                source="user_input"
            ))

        practice_note = ""
        if issues:
            practice_note = " Practice gaps: " + "; ".join(issues) + "."

        if ctr < 0.02:
            return CheckResult(
                category=self.category,
                status=Severity.CRITICAL,
                description=(
                    f"CTR {ctr:.1%} is below 2% — thumbnails need a complete redesign."
                    " Formula: high-contrast background, single focal point, max 3 words of bold text."
                    " A/B test with TubeBuddy or Thumbnail Test; study MrBeast-style curiosity gaps."
                    f"{practice_note}"
                ),
                severity=Severity.CRITICAL,
                estimated_impact="Low CTR caps impressions-to-view conversion — the algorithm stops distributing even good content",
                evidence=evidence
            )
        if ctr < 0.04:
            severity = Severity.MEDIUM if practice_downgrade == 0 else Severity.HIGH
            return CheckResult(
                category=self.category,
                status=severity,
                description=(
                    f"CTR {ctr:.1%} is below the 4% competitive benchmark for faceless niches."
                    " Use the 3-color rule (1 dominant, 1 accent, 1 text color) and design for mobile at 150px wide."
                    f"{practice_note}"
                ),
                severity=severity,
                estimated_impact="Improving CTR to 4-6% would lift views 50%+ at the same impression volume",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.HEALTHY,
            description=f"CTR {ctr:.1%} is healthy (benchmark 4%). Keep A/B testing thumbnails and titles.",
            severity=Severity.HEALTHY,
            estimated_impact="Strong click-through supports algorithmic distribution",
            evidence=evidence
        )


class ScriptQualityCheck(DiagnosticCheck):
    """Analyze script quality for voiceover content"""

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.RETENTION

    @property
    def name(self) -> str:
        return "Script & Voiceover Quality"

    async def run(self, context: BusinessContext) -> CheckResult:
        metrics = context.current_metrics

        avg_view_duration = metrics.get("avg_view_duration", 0)
        avg_percentage = metrics.get("avg_view_percentage", 0)

        # Script structure flags
        has_pattern_interrupts = bool(metrics.get("has_pattern_interrupts", 1))
        has_clear_hook = bool(metrics.get("has_clear_hook", 1))
        has_storytelling = bool(metrics.get("has_storytelling", 0))

        evidence = []
        if avg_percentage:
            evidence.append(Evidence(
                metric="avg_view_percentage",
                value=avg_percentage,
                benchmark=40.0,
                gap_percentage=max(0.0, (40.0 - avg_percentage) / 40.0 * 100),
                source="user_input"
            ))
        if avg_view_duration:
            evidence.append(Evidence(
                metric="avg_view_duration",
                value=avg_view_duration,
                benchmark=120.0,
                gap_percentage=max(0.0, (120.0 - avg_view_duration) / 120.0 * 100),
                source="user_input"
            ))

        structure_gaps = []
        if not has_pattern_interrupts:
            structure_gaps.append("add pattern interrupts every 30-45 seconds (B-roll, zoom, sound)")
        if not has_clear_hook:
            structure_gaps.append("first 15 seconds must promise specific value/transformation")
        if not has_storytelling:
            structure_gaps.append("add a narrative arc (problem → journey → solution)")

        gap_note = ""
        if structure_gaps:
            gap_note = " Script fixes: " + "; ".join(structure_gaps) + "."

        if avg_percentage < 30:
            return CheckResult(
                category=self.category,
                status=Severity.CRITICAL,
                description=(
                    f"Viewers are leaving before 30% ({avg_percentage:.0f}% avg retention) — hook or pacing problem. "
                    "Start with the 'result' in the first 5 seconds, use direct 'you/your' address every 3-4 sentences, "
                    "pace at 1 sentence = 3-4 seconds of video and cut every pause. Voiceover: 140-160 WPM "
                    "(11Labs, Murf, or Play.ht)." + gap_note
                ),
                severity=Severity.CRITICAL,
                estimated_impact="Weak retention suppresses algorithmic distribution — growth fully stalls",
                evidence=evidence
            )
        if avg_view_duration < 120:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=(
                    f"Very short watch time ({avg_view_duration:.0f}s avg) — content not engaging enough. "
                    "Open with hook templates like 'I spent 100 hours researching X so you don't have to...' or "
                    "'In the next 8 minutes, you'll learn exactly how to...'." + gap_note
                ),
                severity=Severity.HIGH,
                estimated_impact="Short watch time blocks both AdSense eligibility (4k hours) and algorithmic reach",
                evidence=evidence
            )
        if structure_gaps:
            return CheckResult(
                category=self.category,
                status=Severity.MEDIUM,
                description="Script structure gaps:" + "; ".join(structure_gaps),
                severity=Severity.MEDIUM,
                estimated_impact="Tightening hook and pacing would lift retention 10-20%",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.HEALTHY,
            description=(
                f"Script quality is solid ({avg_percentage:.0f}% avg retention, {avg_view_duration:.0f}s avg duration). "
                "Keep adding cliffhangers before pattern interrupts and end with a clear CTA."
            ),
            severity=Severity.HEALTHY,
            estimated_impact="Strong scripts support watch time and subscriber conversion",
            evidence=evidence
        )


class RetentionAnalysisCheck(DiagnosticCheck):
    """Analyze audience retention patterns"""

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.RETENTION

    @property
    def name(self) -> str:
        return "Audience Retention Analysis"

    async def run(self, context: BusinessContext) -> CheckResult:
        metrics = context.current_metrics

        retention_curve = metrics.get("retention_curve", {})
        avg_duration = metrics.get("avg_view_duration", 0)
        video_length = metrics.get("avg_video_length", 600)  # 10 min default

        retention_ratio = (avg_duration / video_length) if video_length > 0 else 0
        retention_percentage = round(retention_ratio * 100, 1)

        # Find drop-off points (after 30s, below 50%)
        drop_off_points = []
        if isinstance(retention_curve, dict):
            for time_point, percentage in retention_curve.items():
                if percentage < 50 and int(time_point) > 30:
                    drop_off_points.append((time_point, percentage))
        drop_off_points.sort(key=lambda x: x[1])
        top_dropoffs = drop_off_points[:3]

        # Common faceless retention killers
        killers = []
        if metrics.get("long_intros", 0):
            killers.append("intro longer than 15 seconds — start with value immediately")
        if metrics.get("no_b_roll", 0):
            killers.append("voiceover without visuals — add stock footage every 3-5 seconds")
        if metrics.get("monotone_voice", 0):
            killers.append("monotone voiceover — use AI voices with emotion or vary pacing")

        evidence = [Evidence(
            metric="retention_percentage",
            value=retention_percentage,
            benchmark=40.0,
            gap_percentage=max(0.0, (40.0 - retention_percentage) / 40.0 * 100),
            source="user_input"
        )]

        dropoff_note = ""
        if top_dropoffs:
            dropoff_note = " Top drop-offs: " + ", ".join(
                f"{t}s at {p}%" for t, p in top_dropoffs
            ) + ". Fix those cliffs; add 'coming up' teasers at 25% and 50% marks."

        if retention_ratio < 0.3:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=(
                    f"Losing 70%+ of viewers ({retention_percentage}% avg retention vs 40% target)."
                    " Retention structure: 0-30s hook+promise+proof, 30-60s first quick win, "
                    "then a pattern interrupt every 1-3 minutes, building tension to the reveal." + dropoff_note
                ),
                severity=Severity.HIGH,
                estimated_impact="Low retention caps both AdSense watch-hour accumulation and algorithmic reach",
                evidence=evidence
            )
        if killers:
            return CheckResult(
                category=self.category,
                status=Severity.MEDIUM,
                description="Retention killers detected: " + "; ".join(killers) + "." + dropoff_note,
                severity=Severity.MEDIUM,
                estimated_impact="Fixing retention killers would lift watch time 15-30%",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.HEALTHY,
            description=(
                f"Retention is healthy at {retention_percentage}% (target 40%). "
                "End every video with a question to drive comments — engagement boosts distribution."
            ),
            severity=Severity.HEALTHY,
            estimated_impact="Solid retention compounds watch hours and algorithmic distribution",
            evidence=evidence
        )


class UploadConsistencyCheck(DiagnosticCheck):
    """Check upload schedule and consistency"""

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.OPERATIONS

    @property
    def name(self) -> str:
        return "Upload Consistency"

    async def run(self, context: BusinessContext) -> CheckResult:
        metrics = context.current_metrics

        videos_per_week = metrics.get("upload_frequency", 0)
        total_videos = metrics.get("total_videos", 0)
        subscriber_count = metrics.get("subscribers", 0)

        # Optimal schedule for faceless
        if subscriber_count < 1000:
            optimal_label = "2-3 videos/week (establish presence)"
        elif subscriber_count < 10000:
            optimal_label = "2 videos/week (quality focus)"
        else:
            optimal_label = "1-2 videos/week (sustainability)"

        evidence = [Evidence(
            metric="videos_per_week",
            value=videos_per_week,
            benchmark=2.0,
            gap_percentage=max(0.0, (2.0 - videos_per_week) / 2.0 * 100),
            source="user_input"
        )]

        if videos_per_week < 1:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=(
                    f"Uploading {videos_per_week}x/week — the algorithm won't boost infrequent channels. "
                    f"Optimal now: {optimal_label}. Pipeline: batch 4-5 voiceovers in one session, then run an "
                    "assembly line (script → voiceover → stock footage → edit → thumbnail) with "
                    "Canva, CapCut, 11Labs, and Pexels. Keep a 3-video backlog."
                ),
                severity=Severity.HIGH,
                estimated_impact="Low cadence caps reach and subscriber growth regardless of content quality",
                evidence=evidence
            )
        if videos_per_week < 2 and subscriber_count < 10000:
            return CheckResult(
                category=self.category,
                status=Severity.MEDIUM,
                description=(
                    f"Growth phase needs 2-3x weekly uploads for faceless channels; currently {videos_per_week}x/week. "
                    f"Optimal now: {optimal_label}. Pick one upload day and stick to it religiously."
                ),
                severity=Severity.MEDIUM,
                estimated_impact="Higher velocity would compound algorithmic learnings about your niche",
                evidence=evidence
            )
        if total_videos < 10:
            return CheckResult(
                category=self.category,
                status=Severity.MEDIUM,
                description=(
                    f"Only {total_videos} videos total — need 10+ for the algorithm to understand your niche. "
                    "Current cadence is fine; keep publishing consistently."
                ),
                severity=Severity.MEDIUM,
                estimated_impact="Reaching 10+ videos unlocks more reliable algorithmic categorization",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.HEALTHY,
            description=f"Uploading {videos_per_week}x/week — matches optimal cadence ({optimal_label})",
            severity=Severity.HEALTHY,
            estimated_impact="Consistent cadence supports steady algorithmic distribution",
            evidence=evidence
        )


class MonetizationReadinessCheck(DiagnosticCheck):
    """Check if channel ready for monetization and beyond"""

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.MONETIZATION

    @property
    def name(self) -> str:
        return "Monetization Readiness"

    async def run(self, context: BusinessContext) -> CheckResult:
        metrics = context.current_metrics

        subscribers = metrics.get("subscribers", 0)
        watch_time = metrics.get("watch_time_hours", 0)

        ready_for_adsense = subscribers >= 1000 and watch_time >= 4000

        blockers = []
        evidence = []
        if subscribers < 1000:
            remaining = 1000 - subscribers
            blockers.append(f"need {remaining} more subscribers for AdSense")
            evidence.append(Evidence(
                metric="subscribers",
                value=subscribers,
                benchmark=1000,
                gap_percentage=(1000 - subscribers) / 1000 * 100,
                source="user_input"
            ))
        if watch_time < 4000:
            remaining = 4000 - watch_time
            blockers.append(f"need {remaining} more watch hours for AdSense")
            evidence.append(Evidence(
                metric="watch_time_hours",
                value=watch_time,
                benchmark=4000,
                gap_percentage=(4000 - watch_time) / 4000 * 100,
                source="user_input"
            ))

        # Calculate potential earnings (4 videos/month at current avg views)
        avg_views = metrics.get("avg_views", 0)
        rpm = metrics.get("rpm", 4)  # Conservative for faceless
        potential_monthly = 0
        if ready_for_adsense and avg_views > 0:
            monthly_views = avg_views * 4
            potential_monthly = (monthly_views / 1000) * rpm
            evidence.append(Evidence(
                metric="monthly_adsense_estimate",
                value=potential_monthly,
                benchmark=0,
                gap_percentage=0,
                source="estimate"
            ))

        if not blockers:
            return CheckResult(
                category=self.category,
                status=Severity.HEALTHY,
                description=(
                    f"AdSense ready (1k subs / 4k hours). Revenue readiness: affiliate (100+ subs), "
                    f"digital products and sponsorships (5k+), merch (10k+). At {avg_views:,.0f} avg views, "
                    f"~4 videos/month, ${rpm} RPM → ~${potential_monthly:,.2f}/month AdSense potential. "
                    "Track which topics have highest RPM (finance > gaming)."
                ),
                severity=Severity.HEALTHY,
                estimated_impact="Channel can stack AdSense + affiliate + sponsorship revenue streams",
                evidence=evidence
            )
        if len(blockers) >= 2:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=(
                    "Monetization blocked: " + "; ".join(blockers) + ". "
                    "Fastest path: affiliate links in descriptions (works at 100+ subs), "
                    "then focus retention + consistency to hit AdSense thresholds."
                ),
                severity=Severity.HIGH,
                estimated_impact="Revenue opportunities are closed until monetization thresholds are met",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.MEDIUM,
            description=(
                "Monetization partially blocked: " + blockers[0] + ". "
                "Even before AdSense: add affiliate links to tools mentioned and create a free resource to collect emails."
            ),
            severity=Severity.MEDIUM,
            estimated_impact="Fixing the remaining blocker unlocks AdSense revenue",
            evidence=evidence
        )


# ============================================================================
# Business Model
# ============================================================================

class YouTubeFacelessModel(BusinessModel):
    """Faceless YouTube channel: AdSense, affiliate, sponsorships, digital products."""

    model_id = "youtube_faceless"
    display_name = "Faceless YouTube Channel"
    icon = "🎬"
    description = "Create automated faceless YouTube content using AI tools and stock footage"

    def _get_diagnostic_checks(self) -> List[DiagnosticCheck]:
        return [
            NicheCompetitionCheck(),
            ThumbnailOptimizationCheck(),
            ScriptQualityCheck(),
            RetentionAnalysisCheck(),
            UploadConsistencyCheck(),
            MonetizationReadinessCheck(),
        ]

    def _get_strategy_library(self) -> Dict[BottleneckCategory, List[Strategy]]:
        return {
            BottleneckCategory.ACQUISITION: [
                Strategy(
                    name="30-Day Volume Sprint",
                    description="Publish 10-12 videos in 30 days to establish presence and learn what works",
                    target_bottleneck=BottleneckCategory.ACQUISITION,
                    effort_hours=40,
                    budget_required=0,
                    skill_requirements=["content_creation"],
                    expected_impact="1000+ subscribers, identify winning content formula",
                    success_metrics=["subscribers", "avg_views", "total_videos"],
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
                    time_to_result="4-6 weeks"
                ),
                Strategy(
                    name="YouTube SEO Optimization",
                    description="Optimize titles, descriptions, and tags for search traffic",
                    target_bottleneck=BottleneckCategory.ACQUISITION,
                    effort_hours=10,
                    budget_required=0,
                    skill_requirements=["seo", "keyword_research"],
                    expected_impact="+30-50% views from search (long-term passive traffic)",
                    success_metrics=["search_impressions", "search_traffic_share", "avg_views"],
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
                    time_to_result="4-8 weeks"
                )
            ],
            BottleneckCategory.RETENTION: [
                Strategy(
                    name="Retention Optimization Protocol",
                    description="A/B test hooks, thumbnails, and pacing to maximize watch time",
                    target_bottleneck=BottleneckCategory.RETENTION,
                    effort_hours=20,
                    budget_required=0,
                    skill_requirements=["content_creation", "analytics"],
                    expected_impact="+20-40% retention, faster subscriber growth",
                    success_metrics=["avg_view_duration", "avg_view_percentage", "ctr"],
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
                    time_to_result="3-4 weeks"
                )
            ],
            BottleneckCategory.MONETIZATION: [
                Strategy(
                    name="Affiliate Revenue Stream",
                    description="Add affiliate links to every video for passive income",
                    target_bottleneck=BottleneckCategory.MONETIZATION,
                    effort_hours=5,
                    budget_required=0,
                    skill_requirements=["affiliate_marketing"],
                    expected_impact="$200-1000/month additional revenue",
                    success_metrics=["affiliate_revenue", "link_clicks"],
                    steps=[
                        "List all tools/software mentioned in your last 10 videos",
                        "Sign up for Amazon Associates, ShareASale, individual programs",
                        "Add links to description with timestamps (higher CTR)",
                        "Mention 'link in description' verbally in video",
                        "Create 'resources' page using Stan Store or Beacons",
                        "Track which links get clicks (Amazon reports)",
                        "Double down on content around high-converting products"
                    ],
                    time_to_result="2-4 weeks"
                ),
                Strategy(
                    name="Digital Product Launch",
                    description="Create and sell template/guide to your established audience",
                    target_bottleneck=BottleneckCategory.MONETIZATION,
                    effort_hours=30,
                    budget_required=50,
                    skill_requirements=["product_creation", "marketing"],
                    expected_impact="$2000-10000 launch, $500-2000/month ongoing",
                    success_metrics=["product_revenue", "email_signups", "conversion_rate"],
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
                    time_to_result="6-10 weeks"
                )
            ]
        }

    def _get_kpi_definitions(self) -> List[KPITracking]:
        return [
            KPITracking(
                name="Subscribers",
                description="Subscriber count — gates AdSense monetization at 1k",
                calculation="count(youtube_subscribers)",
                target_range=(1000, 100000),
                frequency="weekly",
                data_source="user_input"
            ),
            KPITracking(
                name="Watch Time (Hours)",
                description="Public watch hours — gates AdSense monetization at 4k hours",
                calculation="sum(public_watch_hours)",
                target_range=(4000, 100000),
                frequency="weekly",
                data_source="user_input"
            ),
            KPITracking(
                name="Avg View Duration",
                description="Average percentage of each video watched",
                calculation="avg_view_duration / avg_video_length",
                target_range=(0.40, 0.60),
                frequency="weekly",
                data_source="user_input"
            ),
            KPITracking(
                name="Click-Through Rate",
                description="Thumbnail/title CTR from impressions",
                calculation="views / impressions",
                target_range=(0.04, 0.10),
                frequency="weekly",
                data_source="user_input"
            ),
            KPITracking(
                name="Revenue Per 1K Views (RPM)",
                description="AdSense revenue per 1000 views",
                calculation="revenue / (views / 1000)",
                target_range=(2, 10),
                frequency="monthly",
                data_source="user_input"
            ),
            KPITracking(
                name="Videos Per Week",
                description="Upload frequency vs stage optimum",
                calculation="count(videos) / 7",
                target_range=(1, 3),
                frequency="weekly",
                data_source="user_input"
            )
        ]
