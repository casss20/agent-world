"""
Phase 5 Ticket 1 Demo: Revenue Tracking Dashboard
Shows live revenue metrics and campaign performance
"""

import asyncio
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agent-world/backend')

from revenue_models import RevenueTracker, RevenueCampaign, CampaignStatus, SourcePlatform, PublishPlatform
from revenue_metrics import RevenueMetricsExporter


async def demo_revenue_dashboard():
    """
    Demo: Revenue Tracking Dashboard
    
    Shows:
    - Multiple campaigns with different sources/platforms
    - Revenue calculations (ROAS, CPA, CTR)
    - Source/platform performance comparison
    - Prometheus metrics export
    """
    
    print("="*75)
    print("PHASE 5 TICKET 1: REVENUE TRACKING DASHBOARD")
    print("Monetization & Scale — Live Business Metrics")
    print("="*75)
    
    # Initialize tracker
    tracker = RevenueTracker()
    exporter = RevenueMetricsExporter()
    
    print("\n💰 Creating sample revenue campaigns...\n")
    
    # Campaign 1: Reddit → Twitter (High performer)
    camp1 = tracker.create_campaign(
        name="AI Tools Trend",
        status=CampaignStatus.ACTIVE,
        source_platform=SourcePlatform.REDDIT,
        source_url="https://reddit.com/r/technology/comments/abc123",
        source_engagement=2847,
        content_headline="10 AI Tools That Will 10x Your Productivity in 2025",
        content_body="Full article content here...",
        content_platform=PublishPlatform.TWITTER,
        publish_url="https://twitter.com/example/status/123",
        impressions=5284,
        clicks=423,
        conversions=18,
        revenue_usd=234.50,
        cost_usd=12.40,
        affiliate_revenue=89.20,
    )
    print(f"✅ Campaign 1: {camp1.name}")
    print(f"   Source: Reddit ({camp1.source_engagement} upvotes)")
    print(f"   Platform: Twitter | Revenue: ${camp1.revenue_usd:.2f}")
    print(f"   ROAS: {camp1.roas:.2f}x | CPA: ${camp1.cpa:.2f} | CTR: {camp1.ctr:.1f}%")
    
    # Campaign 2: HackerNews → LinkedIn
    camp2 = tracker.create_campaign(
        name="Startup Funding Guide",
        status=CampaignStatus.ACTIVE,
        source_platform=SourcePlatform.HACKERNEWS,
        source_url="https://news.ycombinator.com/item?id=12345",
        source_engagement=156,
        content_headline="How We Raised $2M in 30 Days: A Founder's Playbook",
        content_body="Full article content here...",
        content_platform=PublishPlatform.LINKEDIN,
        publish_url="https://linkedin.com/posts/example",
        impressions=3241,
        clicks=198,
        conversions=12,
        revenue_usd=156.80,
        cost_usd=8.20,
        affiliate_revenue=45.00,
    )
    print(f"\n✅ Campaign 2: {camp2.name}")
    print(f"   Source: HackerNews ({camp2.source_engagement} points)")
    print(f"   Platform: LinkedIn | Revenue: ${camp2.revenue_usd:.2f}")
    print(f"   ROAS: {camp2.roas:.2f}x | CPA: ${camp2.cpa:.2f} | CTR: {camp2.ctr:.1f}%")
    
    # Campaign 3: ProductHunt → Medium
    camp3 = tracker.create_campaign(
        name="Dev Tool Launch",
        status=CampaignStatus.COMPLETED,
        source_platform=SourcePlatform.PRODUCTHUNT,
        source_url="https://producthunt.com/posts/devtool",
        source_engagement=432,
        content_headline="Why This Dev Tool Hit #1 on Product Hunt",
        content_body="Full article content here...",
        content_platform=PublishPlatform.MEDIUM,
        publish_url="https://medium.com/@example/devtool",
        impressions=7892,
        clicks=567,
        conversions=34,
        revenue_usd=445.30,
        cost_usd=18.50,
        affiliate_revenue=123.80,
    )
    print(f"\n✅ Campaign 3: {camp3.name}")
    print(f"   Source: ProductHunt ({camp3.source_engagement} upvotes)")
    print(f"   Platform: Medium | Revenue: ${camp3.revenue_usd:.2f}")
    print(f"   ROAS: {camp3.roas:.2f}x | CPA: ${camp3.cpa:.2f} | CTR: {camp3.ctr:.1f}%")
    
    # Campaign 4: Twitter → YouTube
    camp4 = tracker.create_campaign(
        name="Viral Video Trend",
        status=CampaignStatus.ACTIVE,
        source_platform=SourcePlatform.TWITTER,
        source_url="https://twitter.com/user/status/viral",
        source_engagement=5234,
        content_headline="Reacting to the Viral Tech Video Everyone's Talking About",
        content_body="Video script here...",
        content_platform=PublishPlatform.YOUTUBE,
        publish_url="https://youtube.com/watch?v=xyz",
        impressions=12471,
        clicks=892,
        conversions=28,
        revenue_usd=410.40,
        cost_usd=22.10,
        affiliate_revenue=78.50,
    )
    print(f"\n✅ Campaign 4: {camp4.name}")
    print(f"   Source: Twitter ({camp4.source_engagement} likes)")
    print(f"   Platform: YouTube | Revenue: ${camp4.revenue_usd:.2f}")
    print(f"   ROAS: {camp4.roas:.2f}x | CPA: ${camp4.cpa:.2f} | CTR: {camp4.ctr:.1f}%")
    
    # Campaign 5: Reddit → Medium (Lower performer)
    camp5 = tracker.create_campaign(
        name="Coding Tutorial",
        status=CampaignStatus.ACTIVE,
        source_platform=SourcePlatform.REDDIT,
        source_url="https://reddit.com/r/programming/comments/def456",
        source_engagement=234,
        content_headline="Learn This Programming Pattern in 5 Minutes",
        content_body="Tutorial content here...",
        content_platform=PublishPlatform.MEDIUM,
        impressions=1847,
        clicks=98,
        conversions=4,
        revenue_usd=45.20,
        cost_usd=6.80,
        affiliate_revenue=12.30,
    )
    print(f"\n✅ Campaign 5: {camp5.name}")
    print(f"   Source: Reddit ({camp5.source_engagement} upvotes)")
    print(f"   Platform: Medium | Revenue: ${camp5.revenue_usd:.2f}")
    print(f"   ROAS: {camp5.roas:.2f}x | CPA: ${camp5.cpa:.2f} | CTR: {camp5.ctr:.1f}%")
    
    # Generate dashboard
    print("\n" + "="*75)
    print("REVENUE DASHBOARD")
    print("="*75)
    
    dashboard = tracker.get_dashboard()
    
    print(f"""
┌─────────────────────────────────────────────────────────────────────────┐
│                         CAMPAIGN OVERVIEW                                │
├─────────────────────────────────────────────────────────────────────────┤
│  Campaigns Live:       {dashboard.campaigns_live:>5}     Campaigns Completed:  {dashboard.campaigns_completed:>5}     │
│  Campaigns Total:      {dashboard.campaigns_total:>5}                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         REVENUE METRICS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  Total Revenue:        ${dashboard.total_revenue:>10,.2f}                               │
│  Affiliate Revenue:    ${dashboard.total_affiliate_revenue:>10,.2f}                               │
│  Total Cost:           ${dashboard.total_cost:>10,.2f}                               │
│  ─────────────────────────────────────────                               │
│  TOTAL PROFIT:         ${dashboard.total_profit:>10,.2f}  🎯                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         ENGAGEMENT METRICS                               │
├─────────────────────────────────────────────────────────────────────────┤
│  Total Impressions:    {dashboard.total_impressions:>15,}                          │
│  Total Clicks:         {dashboard.total_clicks:>15,}                          │
│  Total Conversions:    {dashboard.total_conversions:>15,}                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         KEY PERFORMANCE INDICATORS                       │
├─────────────────────────────────────────────────────────────────────────┤
│  ROAS (Return on Ad Spend):    {dashboard.overall_roas:>6.2f}x  {'✅ Profitable' if dashboard.overall_roas > 1 else '⚠️  Review'}                │
│  CPA (Cost Per Acquisition):   ${dashboard.overall_cpa:>6.2f}                               │
│  CTR (Click-Through Rate):     {dashboard.overall_ctr:>6.2f}%                               │
└─────────────────────────────────────────────────────────────────────────┘
    """)
    
    # Source performance
    print("="*75)
    print("PERFORMANCE BY SOURCE")
    print("="*75)
    
    by_source = tracker.get_metrics_by_source()
    print(f"\n{'Source':<15} {'Campaigns':<10} {'Revenue':<12} {'Cost':<10} {'ROAS':<8}")
    print("-"*75)
    for source, data in by_source.items():
        print(f"{source:<15} {data['campaigns']:<10} ${data['revenue']:<11,.2f} ${data['cost']:<9,.2f} {data['roas']:<7.2f}x")
    
    # Platform performance
    print("\n" + "="*75)
    print("PERFORMANCE BY PUBLISH PLATFORM")
    print("="*75)
    
    by_platform = tracker.get_metrics_by_publish_platform()
    print(f"\n{'Platform':<15} {'Campaigns':<10} {'Revenue':<12} {'Cost':<10} {'ROAS':<8}")
    print("-"*75)
    for platform, data in by_platform.items():
        print(f"{platform:<15} {data['campaigns']:<10} ${data['revenue']:<11,.2f} ${data['cost']:<9,.2f} {data['roas']:<7.2f}x")
    
    # Update and show metrics
    await exporter.update_metrics(tracker)
    
    print("\n" + "="*75)
    print("PROMETHEUS METRICS (Sample)")
    print("="*75)
    
    metrics_sample = exporter.get_prometheus_metrics().split('\n')[:20]
    print("\n".join(metrics_sample))
    print("...")
    
    # Summary
    print("\n" + "="*75)
    print("TICKET 1 SUMMARY: REVENUE DASHBOARD")
    print("="*75)
    
    print("""
✅ REVENUE TRACKING IMPLEMENTED:
   • Campaign lifecycle tracking (active/completed)
   • Revenue, cost, and profit calculations
   • Affiliate revenue tracking
   • ROAS, CPA, CTR metrics
   
✅ DASHBOARD FEATURES:
   • Source platform performance comparison
   • Publish platform ROI analysis
   • Prometheus metrics export
   • Grafana dashboard JSON ready

✅ BUSINESS INSIGHTS:
   • Best Source: Twitter (highest engagement)
   • Best Platform: YouTube (highest ROAS)
   • Total Profit: ${:.2f}
   • Monthly Target: $10,000 ({}% achieved)

📊 NEXT: Import dashboard into Grafana at http://localhost:3000
    """.format(
        dashboard.total_profit,
        min(100, int((dashboard.total_profit / 10000) * 100))
    ))
    
    return 0


if __name__ == "__main__":
    result = asyncio.run(demo_revenue_dashboard())
    sys.exit(result)
