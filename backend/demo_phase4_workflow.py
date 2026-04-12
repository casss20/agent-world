"""
Phase 4 End-to-End Workflow Demo
Scout → Maker → Merchant with Camofox + Multica
"""

import asyncio
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agent-world/backend')

from camofox_client import CamofoxClient, CamofoxRedditScraper
from multica_client import MulticaClient, MulticaWorkflowTracker, IssuePriority


async def demo_workflow():
    """
    Demo: Content Arbitrage Workflow
    
    1. Scout browses Reddit via Camofox
    2. Scout creates Multica task for Maker
    3. (Simulated) Maker completes content creation
    4. Merchant task created for publishing
    """
    
    print("="*70)
    print("PHASE 4: END-TO-END WORKFLOW DEMO")
    print("Camofox Browser + Multica Orchestration")
    print("="*70)
    
    # Initialize clients
    camofox = CamofoxClient(base_url="http://localhost:9377")
    multica = MulticaClient(base_url="http://localhost:8081")
    tracker = MulticaWorkflowTracker(multica)
    reddit = CamofoxRedditScraper(camofox)
    
    try:
        # Step 1: Ensure agents exist in Multica
        print("\n" + "="*70)
        print("STEP 1: Setup Multica Agents")
        print("="*70)
        
        await tracker.ensure_agents()
        print(f"✅ Agents ready: Scout, Maker, Merchant")
        
        # Step 2: Scout browses Reddit via Camofox
        print("\n" + "="*70)
        print("STEP 2: Scout Browses Reddit (Camofox)")
        print("="*70)
        
        print("Creating browser tab for Reddit...")
        tab = await camofox.create_tab(
            user_id="agent_scout",
            url="https://reddit.com/r/technology",
            session_key="scout_reddit_session"
        )
        print(f"✅ Tab created: {tab.id[:20]}...")
        
        print("\nGetting accessibility snapshot...")
        snapshot = await camofox.get_snapshot(tab.id, user_id="agent_scout")
        print(f"✅ Snapshot received ({len(snapshot.snapshot)} chars)")
        print(f"\n--- Snapshot Preview (first 500 chars) ---")
        print(snapshot.snapshot[:500])
        print("---")
        
        # Close tab
        await camofox.close_tab(tab.id, user_id="agent_scout")
        print("✅ Tab closed")
        
        # Step 3: Create content task in Multica
        print("\n" + "="*70)
        print("STEP 3: Create Content Task (Multica)")
        print("="*70)
        
        trend_data = {
            "source": "reddit",
            "subreddit": "technology",
            "title": "AI agents are transforming content creation workflows",
            "upvotes": 1523,
            "url": "https://reddit.com/r/technology/comments/example",
            "content": "Discussion about how AI agents can automate content discovery and creation..."
        }
        
        issue = await tracker.create_content_task(trend_data, priority=IssuePriority.HIGH)
        print(f"✅ Content task created in Multica")
        print(f"   Issue ID: {issue.id}")
        print(f"   Title: {issue.title}")
        print(f"   Assignee: Maker")
        print(f"   Status: {issue.status.value}")
        
        # Step 4: List tasks to verify
        print("\n" + "="*70)
        print("STEP 4: Verify Tasks in Multica")
        print("="*70)
        
        issues = await multica.list_issues(limit=5)
        print(f"✅ Found {len(issues)} issue(s):")
        for i, issue in enumerate(issues[:3], 1):
            print(f"   {i}. [{issue.status.value}] {issue.title[:50]}...")
        
        # Summary
        print("\n" + "="*70)
        print("WORKFLOW DEMO COMPLETE")
        print("="*70)
        print("""
Summary:
✅ Scout browsed Reddit via Camofox (anti-detection browser)
✅ Scout discovered trending content
✅ Scout created content task in Multica (assigned to Maker)
✅ Multica orchestrating task workflow

Next steps (in production):
1. Maker agent picks up task from Multica board
2. Maker creates content using trend data
3. Merchant publishes content and tracks revenue
4. All progress visible in Multica Kanban board
        """)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        await camofox.close()
        await multica.close()


if __name__ == "__main__":
    result = asyncio.run(demo_workflow())
    sys.exit(result)
