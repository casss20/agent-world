"""
tiktok_ugc.py — Agent World

TikTok UGC (User Generated Content) creator business model.

Revenue streams: brand deals/sponsorships, affiliate commissions,
Creator Fund, own product sales, live gifting.

Key metrics: followers, engagement rate, views, CPM, conversion rate.

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

class ContentQualityCheck(DiagnosticCheck):
    """Analyze content quality vs top performers in niche"""

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.ACQUISITION

    @property
    def name(self) -> str:
        return "Content Quality Analysis"

    async def run(self, context: BusinessContext) -> CheckResult:
        """Compare save rate and average views to top-performer benchmarks."""

        metrics = context.current_metrics
        views = metrics.get("avg_views", 0)
        saves = metrics.get("avg_saves", 0)

        save_rate = (saves / views) if views > 0 else 0

        evidence = []
        if save_rate < 0.05:
            evidence.append(Evidence(
                metric="save_rate",
                value=save_rate,
                benchmark=0.05,  # top 10% benchmark
                gap_percentage=max(0.0, (0.05 - save_rate) / 0.05 * 100),
                source="user_input"
            ))
        if views < 10000:
            evidence.append(Evidence(
                metric="avg_views",
                value=views,
                benchmark=10000,  # top 10% in niche
                gap_percentage=max(0.0, (10000 - views) / 10000 * 100),
                source="user_input"
            ))

        if save_rate >= 0.05 and views >= 10000:
            return CheckResult(
                category=self.category,
                status=Severity.HEALTHY,
                description="Content quality metrics at or above top-performer benchmarks",
                severity=Severity.HEALTHY,
                estimated_impact="Strong hooks and save-worthy content support organic reach",
                evidence=evidence
            )
        if save_rate < 0.02 or views < 1000:
            return CheckResult(
                category=self.category,
                status=Severity.CRITICAL,
                description=(
                    f"Content underperforming: save rate {save_rate:.1%} "
                    f"(benchmark 5%), avg views {views:,.0f} (benchmark 10k). "
                    "Hook or content value is limiting reach."
                ),
                severity=Severity.CRITICAL,
                estimated_impact="Algorithm is not distributing content; growth is blocked at the top of funnel",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.MEDIUM,
            description=(
                f"Content quality below top performers: save rate {save_rate:.1%}, "
                f"avg views {views:,.0f}"
            ),
            severity=Severity.MEDIUM,
            estimated_impact="Improving hooks and content value would lift reach 2-5x",
            evidence=evidence
        )


class NicheSaturationCheck(DiagnosticCheck):
    """Check if niche is oversaturated or has opportunity"""

    HIGH_OPPORTUNITY = [
        "b2b_saas", "productivity_tools", "developer_tools",
        "finance_for_teen", "career_advice_gen_z", "adhd_productivity",
        "small_business_tips", "ecommerce_tutorials",
    ]
    SATURATED = [
        "general_lifestyle", "fitness_motivation", "makeup_tutorials",
        "daily_vlogs", "dance_trends",
    ]

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.ACQUISITION

    @property
    def name(self) -> str:
        return "Niche Saturation Analysis"

    async def run(self, context: BusinessContext) -> CheckResult:
        niche = context.current_metrics.get("niche", "unknown")

        if niche in self.HIGH_OPPORTUNITY:
            return CheckResult(
                category=self.category,
                status=Severity.HEALTHY,
                description=f"Niche '{niche}' is underserved — strong opportunity",
                severity=Severity.HEALTHY,
                estimated_impact="Lower competition makes ranking and growth significantly easier",
                evidence=[Evidence(
                    metric="opportunity_score",
                    value=80,
                    benchmark=50,
                    gap_percentage=0,
                    source="heuristic"
                )]
            )
        if niche in self.SATURATED:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=f"Niche '{niche}' is saturated — need a unique angle or sub-niche to break in",
                severity=Severity.HIGH,
                estimated_impact="High competition means slow organic growth without clear differentiation",
                evidence=[Evidence(
                    metric="opportunity_score",
                    value=30,
                    benchmark=50,
                    gap_percentage=40,
                    source="heuristic"
                )]
            )
        return CheckResult(
            category=self.category,
            status=Severity.MEDIUM,
            description=f"Niche '{niche}' has moderate competition",
            severity=Severity.MEDIUM,
            estimated_impact="Differentiation and a micro-niche angle will improve breakout odds",
            evidence=[Evidence(
                metric="opportunity_score",
                value=50,
                benchmark=50,
                gap_percentage=0,
                source="heuristic"
            )]
        )


class EngagementHealthCheck(DiagnosticCheck):
    """Analyze engagement patterns and audience health"""

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.RETENTION

    @property
    def name(self) -> str:
        return "Engagement Health"

    async def run(self, context: BusinessContext) -> CheckResult:
        metrics = context.current_metrics

        followers = metrics.get("followers", 0)
        likes = metrics.get("avg_likes", 0)
        comments = metrics.get("avg_comments", 0)
        shares = metrics.get("avg_shares", 0)

        # Weighted engagement rate: comments and shares signal quality
        engagement_rate = (
            (likes + comments * 2 + shares * 3) / followers if followers > 0 else 0
        )

        evidence = [Evidence(
            metric="engagement_rate",
            value=engagement_rate,
            benchmark=0.03,
            gap_percentage=max(0.0, (0.03 - engagement_rate) / 0.03 * 100),
            source="user_input"
        )]

        if engagement_rate < 0.02:
            return CheckResult(
                category=self.category,
                status=Severity.CRITICAL,
                description=f"Engagement rate {engagement_rate:.1%} is below 2% — the algorithm will stop distributing content",
                severity=Severity.CRITICAL,
                estimated_impact="Without engagement, TikTok stops showing content to new audiences — growth fully stalls",
                evidence=evidence
            )
        if engagement_rate < 0.03:
            return CheckResult(
                category=self.category,
                status=Severity.MEDIUM,
                description=f"Engagement rate {engagement_rate:.1%} is below the 3% healthy threshold — growth will be slow",
                severity=Severity.MEDIUM,
                estimated_impact="Improving comment/share rates would compound reach",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.HEALTHY,
            description=f"Engagement rate {engagement_rate:.1%} is healthy",
            severity=Severity.HEALTHY,
            estimated_impact="Audience is actively engaging — good signal for monetization readiness",
            evidence=evidence
        )


class MonetizationReadinessCheck(DiagnosticCheck):
    """Check if the account is ready to monetize and at what rates"""

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.MONETIZATION

    @property
    def name(self) -> str:
        return "Monetization Readiness"

    async def run(self, context: BusinessContext) -> CheckResult:
        metrics = context.current_metrics

        followers = metrics.get("followers", 0)
        engagement_rate = metrics.get("engagement_rate", 0)
        has_contact = metrics.get("has_contact", False)

        blockers = []
        evidence = []
        if followers < 10000:
            blockers.append("need 10k+ followers for most brand deals")
            evidence.append(Evidence(
                metric="followers", value=followers, benchmark=10000,
                gap_percentage=(10000 - followers) / 10000 * 100,
                source="user_input"
            ))
        if not has_contact:
            blockers.append("no contact method in bio — brands can't reach you")
        if engagement_rate and engagement_rate < 0.02:
            blockers.append("engagement too low — brands want active audiences")

        # Suggested brand-deal rate: $10 per 1k followers, scaled by engagement
        base_rate = (followers / 1000) * 10
        engagement_multiplier = min(2.0, engagement_rate / 0.03) if engagement_rate else 1.0
        suggested_rate = round(base_rate * engagement_multiplier, 2)

        if not blockers:
            return CheckResult(
                category=self.category,
                status=Severity.HEALTHY,
                description=f"Ready for brand deals — suggested rate ~${suggested_rate}/sponsored video",
                severity=Severity.HEALTHY,
                estimated_impact=f"Can charge ${suggested_rate:.0f}+ per sponsored video and pursue affiliate revenue",
                evidence=evidence
            )
        if len(blockers) >= 2:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description="Monetization blocked: " + "; ".join(blockers[:2]),
                severity=Severity.HIGH,
                estimated_impact="Revenue opportunities are closed until readiness issues are fixed",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.MEDIUM,
            description="Monetization partially ready: " + blockers[0],
            severity=Severity.MEDIUM,
            estimated_impact="Fixing the remaining blocker unlocks brand-deal revenue",
            evidence=evidence
        )


class PostingConsistencyCheck(DiagnosticCheck):
    """Check content velocity and consistency vs growth-stage optimum"""

    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.OPERATIONS

    @property
    def name(self) -> str:
        return "Posting Consistency"

    async def run(self, context: BusinessContext) -> CheckResult:
        metrics = context.current_metrics

        posts_per_week = metrics.get("posts_per_week", 0)
        followers = metrics.get("followers", 0)

        # Optimal cadence depends on account size
        if followers < 1000:
            optimal_min, optimal_max = 7, 14
            optimal_label = "7-14/week (growth phase)"
        elif followers < 10000:
            optimal_min, optimal_max = 5, 10
            optimal_label = "5-10/week (quality focus)"
        else:
            optimal_min, optimal_max = 3, 7
            optimal_label = "3-7/week (sustainability)"

        is_optimal = optimal_min <= posts_per_week <= optimal_max
        evidence = [Evidence(
            metric="posts_per_week",
            value=posts_per_week,
            benchmark=float(optimal_min),
            gap_percentage=max(0.0, (optimal_min - posts_per_week) / optimal_min * 100),
            source="user_input"
        )]

        if posts_per_week < 3:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=f"Posting {posts_per_week}x/week — too infrequent; the algorithm forgets you. Optimal now: {optimal_label}.",
                severity=Severity.HIGH,
                estimated_impact="Low cadence caps reach and follower growth regardless of content quality",
                evidence=evidence
            )
        if posts_per_week > 21:
            return CheckResult(
                category=self.category,
                status=Severity.MEDIUM,
                description=f"Posting {posts_per_week}x/week — likely sacrificing quality and risking burnout",
                severity=Severity.MEDIUM,
                estimated_impact="Quality dilution may be suppressing per-video performance",
                evidence=evidence
            )
        if is_optimal:
            return CheckResult(
                category=self.category,
                status=Severity.HEALTHY,
                description=f"Posting cadence {posts_per_week}x/week is optimal for your stage ({optimal_label})",
                severity=Severity.HEALTHY,
                estimated_impact="Consistent cadence supports steady algorithmic distribution",
                evidence=evidence
            )
        return CheckResult(
            category=self.category,
            status=Severity.MEDIUM,
            description=f"Posting {posts_per_week}x/week vs optimal {optimal_label}",
            severity=Severity.MEDIUM,
            estimated_impact="Adjusting cadence toward the optimal band would lift consistency signals",
            evidence=evidence
        )


# ============================================================================
# Business Model
# ============================================================================

class TikTokUGCModel(BusinessModel):
    """TikTok UGC creator: brand deals, affiliate, products, live gifting."""

    model_id = "tiktok_ugc"
    display_name = "TikTok UGC Creator"
    icon = "🎵"
    description = "Monetize TikTok content through brand deals, affiliate marketing, and product sales"

    def _get_diagnostic_checks(self) -> List[DiagnosticCheck]:
        return [
            ContentQualityCheck(),
            NicheSaturationCheck(),
            EngagementHealthCheck(),
            MonetizationReadinessCheck(),
            PostingConsistencyCheck(),
        ]

    def _get_strategy_library(self) -> Dict[BottleneckCategory, List[Strategy]]:
        return {
            BottleneckCategory.ACQUISITION: [
                Strategy(
                    name="30-Day Growth Sprint",
                    description="Post 2x daily for 30 days using trending sounds and proven hooks",
                    target_bottleneck=BottleneckCategory.ACQUISITION,
                    effort_hours=2,
                    budget_required=0,
                    skill_requirements=["content_creation"],
                    expected_impact="+500-2000 followers in 30 days",
                    success_metrics=["followers", "avg_views", "views_per_video"],
                    steps=[
                        "Research top 20 trending sounds this week",
                        "Create content batch (14 videos) every Sunday",
                        "Post at 8am and 7pm daily",
                        "Reply to every comment in the first hour",
                        "Duets/Stitches with trending creators daily"
                    ],
                    time_to_result="2-4 weeks"
                ),
                Strategy(
                    name="Hook A/B Testing System",
                    description="Test 3 different hooks for every topic and keep the winner",
                    target_bottleneck=BottleneckCategory.ACQUISITION,
                    effort_hours=1,
                    budget_required=0,
                    skill_requirements=["content_creation"],
                    expected_impact="+50-100% view retention",
                    success_metrics=["avg_views", "view_retention", "completion_rate"],
                    steps=[
                        "For each topic, write 3 different first-3-seconds hooks",
                        "Post all 3 within 24 hours",
                        "Compare view velocity in the first hour",
                        "Keep the winner, archive the losers",
                        "Build a 'hook library' of proven openers"
                    ],
                    time_to_result="1-2 weeks"
                ),
                Strategy(
                    name="Sub-Niche Positioning",
                    description="Carve a micro-niche within a saturated niche (e.g. 'Productivity' → 'ADHD Productivity for Developers')",
                    target_bottleneck=BottleneckCategory.ACQUISITION,
                    effort_hours=6,
                    budget_required=0,
                    skill_requirements=["positioning", "research"],
                    expected_impact="Escape saturation — rank in hashtags with 10M-100M views instead of 1B+",
                    success_metrics=["hashtag_rank", "avg_views", "follower_growth_rate"],
                    steps=[
                        "List your broad niche and 5 sub-audiences you belong to",
                        "Target hashtag bands with 10M-100M views (not 1B+)",
                        "Look for niches where top videos have <100k views",
                        "Rewrite bio and first 9 videos around the sub-niche",
                        "Post 10 videos testing sub-niche angles, double down on the winner"
                    ],
                    time_to_result="3-5 weeks"
                )
            ],
            BottleneckCategory.RETENTION: [
                Strategy(
                    name="Engagement Engine System",
                    description="Systematically drive comments, saves, and shares that fuel algorithmic distribution",
                    target_bottleneck=BottleneckCategory.RETENTION,
                    effort_hours=3,
                    budget_required=0,
                    skill_requirements=["community_management"],
                    expected_impact="Engagement rate 2-3x in 30 days",
                    success_metrics=["engagement_rate", "avg_comments", "avg_shares"],
                    steps=[
                        "Ask specific questions in captions to drive comments",
                        "End videos with 'Save this for later' CTA",
                        "Reply to the first 10 comments within 30 minutes (boosts algorithm)",
                        "Create reply videos to high-engagement comments"
                    ],
                    time_to_result="2-4 weeks"
                )
            ],
            BottleneckCategory.MONETIZATION: [
                Strategy(
                    name="Affiliate Revenue Stream",
                    description="Join affiliate programs for tools and products you already use",
                    target_bottleneck=BottleneckCategory.MONETIZATION,
                    effort_hours=5,
                    budget_required=0,
                    skill_requirements=["copywriting"],
                    expected_impact="$200-1000/month within 60 days",
                    success_metrics=["affiliate_revenue", "link_clicks", "conversion_rate"],
                    steps=[
                        "List 10 products you use and love",
                        "Apply to affiliate programs (Amazon, ShareASale, individual brands)",
                        "Create 'honest review' content for each",
                        "Add affiliate links to bio (Linktree)",
                        "Track conversions, double down on winners"
                    ],
                    time_to_result="4-8 weeks"
                ),
                Strategy(
                    name="UGC Creator for Brands",
                    description="Create content FOR brands (not just sponsored posts on your account)",
                    target_bottleneck=BottleneckCategory.MONETIZATION,
                    effort_hours=10,
                    budget_required=0,
                    skill_requirements=["outreach", "content_creation"],
                    expected_impact="$500-3000/month creating content for brand accounts",
                    success_metrics=["brand_clients", "ugc_revenue", "retainer_count"],
                    steps=[
                        "Create a portfolio of 5 high-quality videos",
                        "Join UGC platforms: Billo, Insense, Trend.io",
                        "Reach out to 20 brands/week with your portfolio",
                        "Charge $100-500 per video package",
                        "Build retainer relationships with 3-5 brands"
                    ],
                    time_to_result="4-8 weeks"
                ),
                Strategy(
                    name="Digital Product Launch",
                    description="Create and sell a digital product to your existing audience",
                    target_bottleneck=BottleneckCategory.MONETIZATION,
                    effort_hours=20,
                    budget_required=50,
                    skill_requirements=["product_creation", "marketing"],
                    expected_impact="$1000-5000 launch, $500/month ongoing",
                    success_metrics=["product_revenue", "conversion_rate", "email_signups"],
                    steps=[
                        "Survey audience: 'What would you pay $20 for?'",
                        "Create a simple digital product (template, guide, Notion pack)",
                        "Pre-sell to validate (10 pre-orders = build it)",
                        "Use Gumroad ($0/month) or Stan Store",
                        "Launch with a 3-video sequence: problem → solution → offer"
                    ],
                    time_to_result="6-10 weeks"
                )
            ],
            BottleneckCategory.OPERATIONS: [
                Strategy(
                    name="Batch Content Production",
                    description="Produce a week of content in one session; schedule the rest",
                    target_bottleneck=BottleneckCategory.OPERATIONS,
                    effort_hours=4,
                    budget_required=0,
                    skill_requirements=["planning"],
                    expected_impact="Consistent posting without daily grind; protects quality",
                    success_metrics=["posts_per_week", "batch_completion_rate", "burnout_signals"],
                    steps=[
                        "Batch create content on weekends (14 videos in one session)",
                        "Use TikTok's scheduler or Later/Planoly for the week",
                        "Post at optimal times: 7-9am, 12-1pm, 7-9pm (test your audience)",
                        "Keep a backlog buffer of 3+ finished videos"
                    ],
                    time_to_result="1-2 weeks to systemize"
                )
            ]
        }

    def _get_kpi_definitions(self) -> List[KPITracking]:
        return [
            KPITracking(
                name="Followers",
                description="Total follower count — gates brand-deal eligibility",
                calculation="count(tiktok_followers)",
                target_range=(10000, 100000),
                frequency="weekly",
                data_source="user_input"
            ),
            KPITracking(
                name="Engagement Rate",
                description="Weighted engagement: (likes + 2*comments + 3*shares) / followers",
                calculation="(likes + 2*comments + 3*shares) / followers",
                target_range=(0.03, 0.08),
                frequency="weekly",
                data_source="user_input"
            ),
            KPITracking(
                name="Average Views",
                description="Mean views per video",
                calculation="avg(video_views)",
                target_range=(1000, 100000),
                frequency="weekly",
                data_source="user_input"
            ),
            KPITracking(
                name="Monthly Revenue",
                description="All monetization combined",
                calculation="sum(brand_deals + affiliate + product_sales + gifts)",
                target_range=(500, 10000),
                frequency="monthly",
                data_source="user_input"
            ),
            KPITracking(
                name="Content Velocity",
                description="Posts per week vs stage optimum",
                calculation="count(posts) / 7",
                target_range=(5, 21),
                frequency="weekly",
                data_source="user_input"
            ),
            KPITracking(
                name="Brand Deal Close Rate",
                description="Outreach that converts to paid deals",
                calculation="closed_deals / outreach_sent",
                target_range=(0.05, 0.20),
                frequency="monthly",
                data_source="user_input"
            )
        ]
