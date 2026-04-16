"""
business_models/etsy_pod.py — Agent World

Etsy Print-on-Demand business model diagnostics and strategies.

Key diagnostic areas:
- Listing quality (CTR, favorites, conversion)
- Niche selection (saturation, demand signal)
- Fulfillment (Printify sync, shipping times)
- Seasonality (trend alignment)

Key strategies:
- Listing optimization
- Niche expansion
- Pricing optimization
- Seasonal preparation
"""

from typing import Dict, List, Optional
from .base import (
    BusinessModel, DiagnosticCheck, CheckResult, BottleneckCategory,
    Severity, Evidence, BusinessContext, Strategy, Bottleneck,
    KPITracking, BusinessStage
)


class ListingQualityCheck(DiagnosticCheck):
    """Assess Etsy listing quality metrics"""
    
    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.CONVERSION
    
    @property
    def name(self) -> str:
        return "Listing Quality Assessment"
    
    async def run(self, context: BusinessContext) -> CheckResult:
        """Analyze listing performance metrics"""
        
        metrics = context.current_metrics
        
        # Get key metrics with defaults
        ctr = metrics.get("click_through_rate", 0)
        favorites_per_view = metrics.get("favorites_per_view", 0)
        conversion_rate = metrics.get("conversion_rate", 0)
        listing_count = metrics.get("listing_count", 0)
        
        # Benchmarks for Etsy POD (by stage)
        benchmarks = {
            BusinessStage.IDEATION: {
                "ctr": 0.02,      # 2%
                "favorites_pv": 0.05,  # 5%
                "conversion": 0.01     # 1%
            },
            BusinessStage.TRACTION: {
                "ctr": 0.03,
                "favorites_pv": 0.08,
                "conversion": 0.015
            },
            BusinessStage.GROWTH: {
                "ctr": 0.04,
                "favorites_pv": 0.10,
                "conversion": 0.02
            },
            BusinessStage.OPTIMIZATION: {
                "ctr": 0.05,
                "favorites_pv": 0.12,
                "conversion": 0.025
            }
        }
        
        stage_benchmarks = benchmarks.get(context.stage, benchmarks[BusinessStage.TRACTION])
        
        # Collect evidence
        evidence = []
        issues = []
        
        # Check CTR
        if ctr < stage_benchmarks["ctr"]:
            gap = ((stage_benchmarks["ctr"] - ctr) / stage_benchmarks["ctr"]) * 100
            evidence.append(Evidence(
                metric="click_through_rate",
                value=ctr,
                benchmark=stage_benchmarks["ctr"],
                gap_percentage=gap,
                source="api"
            ))
            issues.append(f"CTR is {gap:.0f}% below benchmark ({ctr:.1%} vs {stage_benchmarks['ctr']:.1%})")
        
        # Check favorites
        if favorites_per_view < stage_benchmarks["favorites_pv"]:
            gap = ((stage_benchmarks["favorites_pv"] - favorites_per_view) / stage_benchmarks["favorites_pv"]) * 100
            evidence.append(Evidence(
                metric="favorites_per_view",
                value=favorites_per_view,
                benchmark=stage_benchmarks["favorites_pv"],
                gap_percentage=gap,
                source="api"
            ))
            issues.append(f"Favorites per view low ({favorites_per_view:.1%} vs {stage_benchmarks['favorites_pv']:.1%})")
        
        # Check conversion
        if conversion_rate < stage_benchmarks["conversion"]:
            gap = ((stage_benchmarks["conversion"] - conversion_rate) / stage_benchmarks["conversion"]) * 100
            evidence.append(Evidence(
                metric="conversion_rate",
                value=conversion_rate,
                benchmark=stage_benchmarks["conversion"],
                gap_percentage=gap,
                source="api"
            ))
            issues.append(f"Conversion rate below target ({conversion_rate:.1%} vs {stage_benchmarks['conversion']:.1%})")
        
        # Check listing count
        if listing_count < 20:
            evidence.append(Evidence(
                metric="listing_count",
                value=listing_count,
                benchmark=50,
                gap_percentage=((50 - listing_count) / 50) * 100,
                source="api"
            ))
            issues.append(f"Only {listing_count} listings (recommend 50+ for visibility)")
        
        # Determine severity
        if not issues:
            status = Severity.HEALTHY
            severity = Severity.HEALTHY
            description = "Listing quality metrics are at or above benchmarks"
            impact = "Listings are performing well"
        elif ctr < 0.01 or conversion_rate < 0.005:
            status = Severity.CRITICAL
            severity = Severity.CRITICAL
            description = "Critical listing quality issues: " + "; ".join(issues[:2])
            impact = "Listings are not attracting or converting customers. This is blocking all revenue."
        elif len(issues) >= 2:
            status = Severity.HIGH
            severity = Severity.HIGH
            description = "Multiple listing quality issues: " + "; ".join(issues[:2])
            impact = "Poor listing performance is significantly limiting sales potential"
        else:
            status = Severity.MEDIUM
            severity = Severity.MEDIUM
            description = issues[0]
            impact = "Listing optimization would improve conversion"
        
        return CheckResult(
            category=self.category,
            status=status,
            description=description,
            severity=severity,
            estimated_impact=impact,
            evidence=evidence
        )


class NicheSaturationCheck(DiagnosticCheck):
    """Assess niche competition and demand"""
    
    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.ACQUISITION
    
    @property
    def name(self) -> str:
        return "Niche Saturation Analysis"
    
    async def run(self, context: BusinessContext) -> CheckResult:
        """Analyze niche competition"""
        
        # In a real implementation, this would:
        # 1. Query Etsy API for competitor listings in niche
        # 2. Analyze search volume vs competition ratio
        # 3. Check for pricing compression
        # 4. Identify gaps
        
        # For MVP, use heuristics from user input
        niche = context.current_metrics.get("primary_niche", "unknown")
        competitor_count = context.current_metrics.get("competitor_listings", 0)
        avg_competitor_price = context.current_metrics.get("avg_competitor_price", 0)
        your_price = context.current_metrics.get("your_avg_price", 0)
        
        evidence = []
        
        # Estimate saturation (simplified)
        if competitor_count > 10000:
            saturation = "high"
            evidence.append(Evidence(
                metric="competitor_listings",
                value=competitor_count,
                benchmark=5000,
                gap_percentage=100,
                source="api"
            ))
        elif competitor_count > 1000:
            saturation = "medium"
        else:
            saturation = "low"
        
        # Check pricing
        if avg_competitor_price > 0 and your_price > 0:
            price_ratio = your_price / avg_competitor_price
            evidence.append(Evidence(
                metric="price_ratio",
                value=price_ratio,
                benchmark=1.0,
                gap_percentage=abs(price_ratio - 1.0) * 100,
                source="api"
            ))
        
        if saturation == "high":
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=f"Niche '{niche}' appears saturated with {competitor_count}+ competitors",
                severity=Severity.HIGH,
                estimated_impact="High competition makes it difficult to stand out and may compress margins",
                evidence=evidence
            )
        elif saturation == "medium":
            return CheckResult(
                category=self.category,
                status=Severity.MEDIUM,
                description=f"Niche '{niche}' has moderate competition",
                severity=Severity.MEDIUM,
                estimated_impact="Differentiation required to capture market share",
                evidence=evidence
            )
        else:
            return CheckResult(
                category=self.category,
                status=Severity.HEALTHY,
                description=f"Niche '{niche}' appears to have room for new entrants",
                severity=Severity.HEALTHY,
                estimated_impact="Lower competition may allow faster initial growth",
                evidence=evidence
            )


class FulfillmentCheck(DiagnosticCheck):
    """Assess Printify/Etsy fulfillment status"""
    
    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.OPERATIONS
    
    @property
    def name(self) -> str:
        return "Fulfillment Operations"
    
    async def run(self, context: BusinessContext) -> CheckResult:
        """Check fulfillment health"""
        
        metrics = context.current_metrics
        
        # Check Printify connection
        printify_connected = metrics.get("printify_connected", False)
        sync_errors = metrics.get("sync_errors_last_30d", 0)
        avg_production_time = metrics.get("avg_production_days", 0)
        late_shipments = metrics.get("late_shipment_rate", 0)
        
        evidence = []
        issues = []
        
        if not printify_connected:
            evidence.append(Evidence(
                metric="printify_connected",
                value=0,
                benchmark=1,
                gap_percentage=100,
                source="api"
            ))
            issues.append("Printify not connected to Etsy")
        
        if sync_errors > 5:
            evidence.append(Evidence(
                metric="sync_errors_last_30d",
                value=sync_errors,
                benchmark=2,
                gap_percentage=((sync_errors - 2) / 2) * 100,
                source="api"
            ))
            issues.append(f"{sync_errors} sync errors in last 30 days")
        
        if avg_production_time > 5:
            evidence.append(Evidence(
                metric="avg_production_days",
                value=avg_production_time,
                benchmark=3,
                gap_percentage=((avg_production_time - 3) / 3) * 100,
                source="api"
            ))
            issues.append(f"Average production time {avg_production_time} days (target < 3)")
        
        if late_shipments > 0.05:  # 5%
            evidence.append(Evidence(
                metric="late_shipment_rate",
                value=late_shipments,
                benchmark=0.02,
                gap_percentage=((late_shipments - 0.02) / 0.02) * 100,
                source="api"
            ))
            issues.append(f"{late_shipments:.1%} late shipments (impacts reviews)")
        
        if not issues:
            return CheckResult(
                category=self.category,
                status=Severity.HEALTHY,
                description="Fulfillment operations running smoothly",
                severity=Severity.HEALTHY,
                estimated_impact="Reliable fulfillment supports positive reviews and repeat customers",
                evidence=evidence
            )
        elif len(issues) >= 2 or not printify_connected:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description="; ".join(issues[:2]),
                severity=Severity.HIGH,
                estimated_impact="Fulfillment issues risk negative reviews and account suspension",
                evidence=evidence
            )
        else:
            return CheckResult(
                category=self.category,
                status=Severity.MEDIUM,
                description=issues[0],
                severity=Severity.MEDIUM,
                estimated_impact="Address to maintain customer satisfaction",
                evidence=evidence
            )


class SeasonalTrendCheck(DiagnosticCheck):
    """Assess alignment with seasonal trends"""
    
    @property
    def category(self) -> BottleneckCategory:
        return BottleneckCategory.ACQUISITION
    
    @property
    def name(self) -> str:
        return "Seasonal Trend Alignment"
    
    async def run(self, context: BusinessContext) -> CheckResult:
        """Check if listings align with upcoming seasonal demand"""
        
        from datetime import datetime
        
        current_month = datetime.utcnow().month
        
        # Define key Etsy POD seasons
        upcoming_seasons = []
        
        if current_month in [7, 8, 9]:
            upcoming_seasons = ["Halloween (Oct)", "Christmas (Dec)", "Q4 Peak"]
        elif current_month in [10, 11]:
            upcoming_seasons = ["Christmas (Dec)", "New Year", "Valentine's Day"]
        elif current_month in [12, 1]:
            upcoming_seasons = ["Valentine's Day (Feb)", "Spring"]
        
        seasonal_listings = context.current_metrics.get("seasonal_listings_count", 0)
        total_listings = context.current_metrics.get("listing_count", 1)
        
        seasonal_ratio = seasonal_listings / total_listings if total_listings > 0 else 0
        
        evidence = [
            Evidence(
                metric="seasonal_listings_ratio",
                value=seasonal_ratio,
                benchmark=0.30,  # 30% seasonal recommended for Q4
                gap_percentage=max(0, (0.30 - seasonal_ratio) / 0.30 * 100),
                source="api"
            )
        ]
        
        if upcoming_seasons and seasonal_ratio < 0.20:
            return CheckResult(
                category=self.category,
                status=Severity.HIGH,
                description=f"Underprepared for upcoming seasons: {', '.join(upcoming_seasons[:2])}. Only {seasonal_ratio:.0%} seasonal listings.",
                severity=Severity.HIGH,
                estimated_impact="Missing peak demand periods significantly limits revenue potential",
                evidence=evidence
            )
        elif upcoming_seasons and seasonal_ratio < 0.30:
            return CheckResult(
                category=self.category,
                status=Severity.MEDIUM,
                description=f"Could strengthen seasonal lineup for {', '.join(upcoming_seasons[:2])}",
                severity=Severity.MEDIUM,
                estimated_impact="Additional seasonal listings would capture more peak demand",
                evidence=evidence
            )
        else:
            return CheckResult(
                category=self.category,
                status=Severity.HEALTHY,
                description="Adequate seasonal preparation" if upcoming_seasons else "No major seasons immediately upcoming",
                severity=Severity.HEALTHY,
                estimated_impact="Well-positioned for seasonal demand" if upcoming_seasons else "Can focus on evergreen optimization",
                evidence=evidence
            )


class EtsyPODModel(BusinessModel):
    """Etsy Print-on-Demand business model diagnostics and strategies"""
    
    model_id = "etsy_pod"
    display_name = "Etsy Print-on-Demand"
    icon = "🏪"
    description = "Print-on-demand products sold through Etsy marketplace"
    
    def _get_diagnostic_checks(self) -> List[DiagnosticCheck]:
        return [
            ListingQualityCheck(),
            NicheSaturationCheck(),
            FulfillmentCheck(),
            SeasonalTrendCheck()
        ]
    
    def _get_strategy_library(self) -> Dict[BottleneckCategory, List[Strategy]]:
        return {
            BottleneckCategory.CONVERSION: [
                Strategy(
                    name="Listing Title & Tags Optimization",
                    description="Rewrite titles with high-CTR keywords, expand tags to all 13 slots",
                    target_bottleneck=BottleneckCategory.CONVERSION,
                    effort_hours=8,
                    budget_required=0,
                    skill_requirements=["copywriting"],
                    expected_impact="15-30% improvement in search visibility and CTR",
                    success_metrics=["click_through_rate", "search_impressions", "ranking_position"],
                    steps=[
                        "Analyze current search terms bringing traffic",
                        "Research competitor titles in top 20",
                        "Rewrite titles: [Keyword] | [Benefit] | [Occasion/Gift]",
                        "Fill all 13 tags with relevant keywords",
                        "Update category attributes for better filtering",
                        "A/B test for 2 weeks, measure CTR change"
                    ],
                    time_to_result="2-4 weeks for full impact"
                ),
                Strategy(
                    name="Thumbnail & Mockup Refresh",
                    description="Upgrade product photography with lifestyle mockups and consistent styling",
                    target_bottleneck=BottleneckCategory.CONVERSION,
                    effort_hours=12,
                    budget_required=50,  # Mockup templates
                    skill_requirements=["design"],
                    expected_impact="20-40% improvement in click-through rate",
                    success_metrics=["click_through_rate", "favorites_per_view"],
                    steps=[
                        "Audit current thumbnails vs top competitors",
                        "Purchase/create lifestyle mockup templates",
                        "Establish consistent brand aesthetic (colors, fonts, layout)",
                        "Update top 20 listings first",
                        "Track favorites-to-view ratio",
                        "Roll out to remaining listings based on results"
                    ],
                    time_to_result="1-2 weeks for CTR improvement"
                ),
                Strategy(
                    name="Review Generation Campaign",
                    description="Systematically encourage reviews from past customers",
                    target_bottleneck=BottleneckCategory.CONVERSION,
                    effort_hours=6,
                    budget_required=0,
                    skill_requirements=[],
                    expected_impact="Social proof increases conversion 10-25%",
                    success_metrics=["review_count", "average_rating", "conversion_rate"],
                    steps=[
                        "Identify customers with 5-star experience (no issues)",
                        "Send personalized thank-you + review request (Etsy Message)",
                        "Follow up once after 7 days if no response",
                        "Never offer incentives (against Etsy ToS)",
                        "Respond to all reviews promptly",
                        "Track review velocity and conversion correlation"
                    ],
                    time_to_result="4-8 weeks for significant review increase"
                )
            ],
            
            BottleneckCategory.ACQUISITION: [
                Strategy(
                    name="Niche Expansion",
                    description="Identify and launch listings in adjacent underserved niches",
                    target_bottleneck=BottleneckCategory.ACQUISITION,
                    effort_hours=20,
                    budget_required=100,  # Sample products for photos
                    skill_requirements=["research", "design"],
                    expected_impact="Diversify traffic sources, reduce single-niche risk",
                    success_metrics=["new_niche_traffic", "total_impressions", "revenue_per_niche"],
                    steps=[
                        "Analyze current bestsellers and their niches",
                        "Research 3 adjacent niches with demand but lower competition",
                        "Create 5-10 designs per new niche",
                        "Launch with optimized listings (title/tags/thumbnails)",
                        "Track performance separately from core niche",
                        "Double down on niches showing traction"
                    ],
                    time_to_result="4-6 weeks to validate new niches"
                ),
                Strategy(
                    name="Seasonal Product Line",
                    description="Develop products for upcoming seasonal peaks",
                    target_bottleneck=BottleneckCategory.ACQUISITION,
                    effort_hours=24,
                    budget_required=150,
                    skill_requirements=["design", "trend_research"],
                    expected_impact="Capture 2-3x revenue during peak seasons",
                    success_metrics=["seasonal_listing_sales", "seasonal_revenue"],
                    steps=[
                        "Identify next 2 major seasons (e.g., Halloween, Christmas)",
                        "Research trending designs/themes for each",
                        "Create 15-20 seasonal designs per season",
                        "Launch 6-8 weeks before peak (for indexing)",
                        "Monitor early performance and adjust",
                        "Plan post-season clearance transition"
                    ],
                    time_to_result="6-8 weeks before seasonal peak for full impact"
                ),
                Strategy(
                    name="Etsy Ads Optimization",
                    description="Strategic use of Etsy Ads to boost visibility of proven listings",
                    target_bottleneck=BottleneckCategory.ACQUISITION,
                    effort_hours=4,
                    budget_required=300,  # Monthly ad budget
                    skill_requirements=["ads"],
                    expected_impact="2-3x visibility for listings with strong organic conversion",
                    success_metrics=["ad_roas", "ad_revenue", "cost_per_click"],
                    steps=[
                        "Identify listings with >2% organic conversion",
                        "Start with $5/day budget for top 5 listings",
                        "Monitor ROAS daily, pause if <2.0 for 3 days",
                        "Increase budget on ROAS >4.0 listings",
                        "Weekly review: kill losers, scale winners",
                        "Never advertise unproven new listings"
                    ],
                    time_to_result="1-2 weeks to identify winning ads"
                )
            ],
            
            BottleneckCategory.MONETIZATION: [
                Strategy(
                    name="Pricing Optimization",
                    description="Strategic pricing adjustments based on value and competition",
                    target_bottleneck=BottleneckCategory.MONETIZATION,
                    effort_hours=4,
                    budget_required=0,
                    skill_requirements=["analysis"],
                    expected_impact="10-20% revenue increase without volume loss",
                    success_metrics=["average_order_value", "conversion_rate", "profit_margin"],
                    steps=[
                        "Analyze current margins by product type",
                        "Research competitor pricing for similar items",
                        "Identify underpriced bestsellers (room to raise)",
                        "A/B test price increase on 20% of listings",
                        "Monitor conversion rate change",
                        "Roll out if conversion drop <5% for >10% price increase"
                    ],
                    time_to_result="2-3 weeks to validate price changes"
                ),
                Strategy(
                    name="Bundle & Upsell Offers",
                    description="Create product bundles to increase AOV",
                    target_bottleneck=BottleneckCategory.MONETIZATION,
                    effort_hours=8,
                    budget_required=0,
                    skill_requirements=["design", "listing_creation"],
                    expected_impact="25-40% increase in AOV for bundle buyers",
                    success_metrics=["average_order_value", "bundle_conversion", "units_per_transaction"],
                    steps=[
                        "Identify complementary products (mug + coaster, etc.)",
                        "Design bundle graphics showing value",
                        "Create bundle listings with 10-15% discount vs individual",
                        "Cross-promote in individual listings",
                        "Track bundle attach rate",
                        "Develop tiered bundles (Basic/Premium/Deluxe)"
                    ],
                    time_to_result="3-4 weeks to establish bundle sales"
                )
            ],
            
            BottleneckCategory.OPERATIONS: [
                Strategy(
                    name="Printify Provider Optimization",
                    description="Switch to faster/more reliable print providers",
                    target_bottleneck=BottleneckCategory.OPERATIONS,
                    effort_hours=6,
                    budget_required=50,
                    skill_requirements=[],
                    expected_impact="Faster shipping, fewer defects, better reviews",
                    success_metrics=["production_time", "defect_rate", "customer_rating"],
                    steps=[
                        "Review current provider performance (delivery times, quality)",
                        "Research alternative providers for your top products",
                        "Order samples from 2-3 alternatives",
                        "Compare quality, packaging, shipping speed",
                        "Switch bestsellers to best provider",
                        "Monitor customer feedback for 30 days"
                    ],
                    time_to_result="2-3 weeks to complete switchover"
                ),
                Strategy(
                    name="Listing Automation System",
                    description="Streamline listing creation and updates",
                    target_bottleneck=BottleneckCategory.OPERATIONS,
                    effort_hours=16,
                    budget_required=0,
                    skill_requirements=["tools"],
                    expected_impact="3x faster listing creation, consistent quality",
                    success_metrics=["listings_per_hour", "error_rate", "time_to_publish"],
                    steps=[
                        "Create listing templates for each product type",
                        "Build title/tag generators from keyword lists",
                        "Set up bulk editing workflows",
                        "Create design-to-listing pipeline",
                        "Document SOP for virtual assistant handoff",
                        "Track throughput and error rates"
                    ],
                    time_to_result="4-6 weeks to fully operationalize"
                )
            ]
        }
    
    def _get_kpi_definitions(self) -> List[KPITracking]:
        return [
            KPITracking(
                name="Revenue",
                description="Total sales revenue",
                calculation="sum(order_value)",
                target_range=(1000, 50000),
                frequency="daily",
                data_source="etsy_api"
            ),
            KPITracking(
                name="Orders",
                description="Number of orders",
                calculation="count(orders)",
                target_range=(10, 500),
                frequency="daily",
                data_source="etsy_api"
            ),
            KPITracking(
                name="Click-Through Rate",
                description="Search impressions to listing clicks",
                calculation="clicks / impressions",
                target_range=(0.02, 0.08),
                frequency="daily",
                data_source="etsy_api"
            ),
            KPITracking(
                name="Conversion Rate",
                description="Listing views to orders",
                calculation="orders / views",
                target_range=(0.01, 0.05),
                frequency="daily",
                data_source="etsy_api"
            ),
            KPITracking(
                name="Favorites per View",
                description="Engagement indicator",
                calculation="favorites / views",
                target_range=(0.05, 0.15),
                frequency="daily",
                data_source="etsy_api"
            ),
            KPITracking(
                name="Average Order Value",
                description="Revenue per order",
                calculation="revenue / orders",
                target_range=(20, 50),
                frequency="weekly",
                data_source="etsy_api"
            ),
            KPITracking(
                name="Review Rate",
                description="Orders that leave reviews",
                calculation="reviews / orders",
                target_range=(0.15, 0.30),
                frequency="weekly",
                data_source="etsy_api"
            ),
            KPITracking(
                name="Production Time",
                description="Days from order to shipment",
                calculation="printify_production_days",
                target_range=(1, 4),
                frequency="daily",
                data_source="printify_api"
            ),
            KPITracking(
                name="Listing Count",
                description="Active listings in shop",
                calculation="count(active_listings)",
                target_range=(50, 500),
                frequency="weekly",
                data_source="etsy_api"
            )
        ]
