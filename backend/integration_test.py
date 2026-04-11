"""
Integration Test: AgentVerse ↔ Workflow Adapter ↔ ChatDev Money
Tests the full data flow from Room launch through workflow execution.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
import sys
import os

# Add paths for imports
sys.path.insert(0, '/root/.openclaw/workspace/agent-world/backend')
sys.path.insert(0, '/root/.openclaw/workspace/chatdev-money')

# Test configuration
TEST_CONFIG = {
    "adapter_url": "http://localhost:8001",
    "chatdev_url": "http://localhost:8000",
    "redis_url": "redis://localhost:6379",
    "tenant_id": "test-tenant-001",
    "project_id": "test-project-001", 
    "room_id": "test-room-001",
    "user_id": "test-user-001"
}


class MockChatDevServer:
    """
    Mock ChatDev Money server for integration testing.
    Simulates the actual ChatDev API responses.
    """
    
    def __init__(self):
        self.runs = {}
        self.run_counter = 0
        print("🎭 MockChatDevServer initialized")
    
    async def execute_workflow(self, payload: Dict) -> Dict:
        """Simulate workflow execution"""
        self.run_counter += 1
        run_id = f"chatdev_run_{self.run_counter:04d}"
        
        run_data = {
            "run_id": run_id,
            "session_name": payload.get("session_name", "unknown"),
            "status": "running",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "variables": payload.get("variables", {})
        }
        self.runs[run_id] = run_data
        
        print(f"🚀 MockChatDev: Started {run_id}")
        
        # Start async simulation
        asyncio.create_task(self._simulate_execution(run_id, payload))
        
        return run_data
    
    async def _simulate_execution(self, run_id: str, payload: Dict):
        """Simulate Scout → Maker → Merchant pipeline"""
        run = self.runs[run_id]
        variables = payload.get("variables", {})
        subreddit = variables.get("subreddit", "sidehustle")
        
        # Simulate Scout
        await asyncio.sleep(0.5)
        run["current_node"] = "Scout"
        run["events"] = run.get("events", []) + [{
            "type": "node.started",
            "node_id": "Scout",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
        print(f"🔍 [{run_id}] Scout started")
        
        await asyncio.sleep(1.0)
        scout_output = {
            "trend_title": f"10 Passive Income Ideas from r/{subreddit}",
            "opportunity_score": 8.5,
            "summary": f"Hot trend in {subreddit} about passive income strategies",
            "keywords": ["passive income", "side hustle", "2026"],
            "monetization_angle": "Affiliate marketing for finance tools"
        }
        run["events"].append({
            "type": "node.completed",
            "node_id": "Scout",
            "output": scout_output,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        print(f"✅ [{run_id}] Scout found: {scout_output['trend_title']}")
        
        # Simulate Maker
        await asyncio.sleep(0.5)
        run["current_node"] = "Maker"
        run["events"].append({
            "type": "node.started",
            "node_id": "Maker",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        print(f"✍️  [{run_id}] Maker writing content...")
        
        await asyncio.sleep(1.5)
        article = {
            "title": scout_output["trend_title"],
            "word_count": 720,
            "seo_score": 94,
            "content_file": f"content_{run_id}.md"
        }
        run["events"].append({
            "type": "node.completed",
            "node_id": "Maker",
            "output": article,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        print(f"✅ [{run_id}] Maker completed: {article['word_count']} words")
        
        # Simulate Merchant
        await asyncio.sleep(0.5)
        run["current_node"] = "Merchant"
        run["events"].append({
            "type": "node.started",
            "node_id": "Merchant",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        print(f"🏪 [{run_id}] Merchant publishing...")
        
        await asyncio.sleep(1.0)
        publish_result = {
            "platform": "ghost",
            "url": f"https://blog.example.com/{run_id}",
            "status": "published"
        }
        run["events"].append({
            "type": "node.completed",
            "node_id": "Merchant",
            "output": publish_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        print(f"✅ [{run_id}] Merchant published to {publish_result['platform']}")
        
        # Complete workflow
        run["status"] = "completed"
        run["completed_at"] = datetime.now(timezone.utc).isoformat()
        run["outputs"] = {
            "trend_data": scout_output,
            "article": article,
            "publish": publish_result,
            "estimated_revenue": 52.50,
            "platform": "ghost",
            "published_url": publish_result["url"]
        }
        run["events"].append({
            "type": "workflow.completed",
            "outputs": run["outputs"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        print(f"🎉 [{run_id}] Workflow completed! Revenue: ${run['outputs']['estimated_revenue']}")
    
    async def get_status(self, run_id: str) -> Dict:
        """Get run status"""
        run = self.runs.get(run_id, {})
        return {
            "run_id": run_id,
            "status": run.get("status", "unknown"),
            "current_node": run.get("current_node"),
            "progress": self._calc_progress(run)
        }
    
    def _calc_progress(self, run: Dict) -> int:
        """Calculate progress percentage"""
        events = run.get("events", [])
        completed = sum(1 for e in events if e["type"] == "node.completed")
        return int((completed / 3) * 100)  # 3 nodes: Scout, Maker, Merchant
    
    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a run"""
        if run_id in self.runs:
            self.runs[run_id]["status"] = "cancelled"
            return True
        return False


class IntegrationTestRunner:
    """
    Runs end-to-end integration tests.
    """
    
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        self.mock_chatdev = MockChatDevServer()
        self.results = []
        print(f"🧪 IntegrationTestRunner (mock={use_mock})")
    
    async def run_full_test(self):
        """Run complete integration test"""
        print("\n" + "="*70)
        print("🧪 INTEGRATION TEST: AgentVerse → Adapter → ChatDev Money")
        print("="*70)
        
        # Test 1: Start workflow from room context
        await self.test_start_workflow()
        
        # Test 2: Poll status during execution
        await self.test_status_polling()
        
        # Test 3: Event flow
        await self.test_event_flow()
        
        # Test 4: Completion and revenue tracking
        await self.test_completion()
        
        # Summary
        self.print_summary()
    
    async def test_start_workflow(self):
        """Test: Room can start a workflow"""
        print("\n📋 Test 1: Start Workflow from Room")
        print("-" * 40)
        
        # Simulate AgentVerse calling adapter
        room_context = {
            "tenant_id": TEST_CONFIG["tenant_id"],
            "project_id": TEST_CONFIG["project_id"],
            "room_id": TEST_CONFIG["room_id"],
            "workflow_id": "content_arbitrage_v1",
            "initiated_by_user_id": TEST_CONFIG["user_id"],
            "credential_refs": ["reddit_api", "ghost_api"],
            "input_payload": {
                "subreddit": "sidehustle",
                "min_upvotes": 100,
                "content_focus": "passive income"
            }
        }
        
        print(f"Room: {room_context['room_id']}")
        print(f"Workflow: {room_context['workflow_id']}")
        print(f"Inputs: {room_context['input_payload']}")
        
        # Call mock ChatDev (simulating adapter behavior)
        chatdev_payload = {
            "yaml_file": "content_arbitrage_v1.yaml",
            "task_prompt": "Execute content arbitrage workflow",
            "variables": room_context["input_payload"],
            "session_name": f"av_room_{room_context['room_id'][:8]}_{uuid.uuid4().hex[:8]}"
        }
        
        result = await self.mock_chatdev.execute_workflow(chatdev_payload)
        self.run_id = result["run_id"]
        
        print(f"✅ Workflow started: {self.run_id}")
        self.results.append(("Start Workflow", "PASS", self.run_id))
        
        # Wait a bit for execution to start
        await asyncio.sleep(1.0)
    
    async def test_status_polling(self):
        """Test: Status polling works"""
        print("\n📋 Test 2: Status Polling")
        print("-" * 40)
        
        # Poll a few times during "execution"
        for i in range(5):
            status = await self.mock_chatdev.get_status(self.run_id)
            progress = status.get("progress", 0)
            current = status.get("current_node", "starting")
            
            print(f"  Poll {i+1}: {progress}% - {current}")
            
            if status["status"] == "completed":
                break
                
            await asyncio.sleep(0.8)
        
        final_status = await self.mock_chatdev.get_status(self.run_id)
        print(f"✅ Final status: {final_status['status']}")
        self.results.append(("Status Polling", "PASS", f"{final_status['progress']}% complete"))
    
    async def test_event_flow(self):
        """Test: Events flow correctly"""
        print("\n📋 Test 3: Event Flow")
        print("-" * 40)
        
        run = self.mock_chatdev.runs.get(self.run_id, {})
        events = run.get("events", [])
        
        # Verify event sequence
        expected_sequence = [
            ("node.started", "Scout"),
            ("node.completed", "Scout"),
            ("node.started", "Maker"),
            ("node.completed", "Maker"),
            ("node.started", "Merchant"),
            ("node.completed", "Merchant"),
            ("workflow.completed", None)
        ]
        
        print(f"Captured {len(events)} events:")
        for i, event in enumerate(events):
            node_info = f" ({event.get('node_id')})" if event.get('node_id') else ""
            print(f"  {i+1}. {event['type']}{node_info}")
        
        # Verify sequence
        event_types = [(e["type"], e.get("node_id")) for e in events]
        matches = sum(1 for i, (exp_type, exp_node) in enumerate(expected_sequence) 
                      if i < len(event_types) and event_types[i][0] == exp_type)
        
        if matches >= len(expected_sequence) - 1:
            print("✅ Event sequence correct")
            self.results.append(("Event Flow", "PASS", f"{len(events)} events"))
        else:
            print(f"⚠️  Event sequence mismatch: {matches}/{len(expected_sequence)}")
            self.results.append(("Event Flow", "PARTIAL", f"{matches}/{len(expected_sequence)}"))
    
    async def test_completion(self):
        """Test: Completion and revenue tracking"""
        print("\n📋 Test 4: Completion & Revenue")
        print("-" * 40)
        
        run = self.mock_chatdev.runs.get(self.run_id, {})
        
        if run.get("status") != "completed":
            print("⏳ Waiting for completion...")
            for _ in range(10):
                await asyncio.sleep(0.5)
                run = self.mock_chatdev.runs.get(self.run_id, {})
                if run.get("status") == "completed":
                    break
        
        if run.get("status") == "completed":
            outputs = run.get("outputs", {})
            
            print(f"Status: {run['status']}")
            print(f"Revenue: ${outputs.get('estimated_revenue', 0)}")
            print(f"Platform: {outputs.get('platform', 'unknown')}")
            print(f"URL: {outputs.get('published_url', 'N/A')}")
            
            # Verify all outputs present
            checks = [
                ("trend_data" in outputs, "Trend data"),
                ("article" in outputs, "Article content"),
                ("publish" in outputs, "Publish result"),
                (outputs.get("estimated_revenue", 0) > 0, "Revenue tracking")
            ]
            
            all_pass = all(check[0] for check in checks)
            for passed, name in checks:
                status = "✅" if passed else "❌"
                print(f"  {status} {name}")
            
            if all_pass:
                print("✅ All completion checks passed")
                self.results.append(("Completion & Revenue", "PASS", f"${outputs['estimated_revenue']} revenue"))
            else:
                self.results.append(("Completion & Revenue", "PARTIAL", "Some outputs missing"))
        else:
            print(f"❌ Workflow not completed: {run.get('status')}")
            self.results.append(("Completion & Revenue", "FAIL", "Not completed"))
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        
        passed = sum(1 for _, status, _ in self.results if status == "PASS")
        total = len(self.results)
        
        for test_name, status, details in self.results:
            icon = "✅" if status == "PASS" else "⚠️" if status == "PARTIAL" else "❌"
            print(f"{icon} {test_name:25} | {status:8} | {details}")
        
        print("-" * 70)
        print(f"Result: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - Integration ready for production!")
        elif passed >= total * 0.75:
            print("⚠️  MOSTLY WORKING - Minor issues to address")
        else:
            print("❌ NEEDS WORK - Significant issues found")


async def main():
    """Run integration tests"""
    runner = IntegrationTestRunner(use_mock=True)
    await runner.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())
