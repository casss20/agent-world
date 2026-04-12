"""
Test Real LLM Execution - Ticket 4
Verify end-to-end workflow with real OpenAI API
"""

import httpx
import asyncio
import json
from datetime import datetime

CHATDEV_URL = "http://localhost:8000"
AGENTVERSE_URL = "http://localhost:8003"


async def test_real_execution():
    """Test one real workflow execution with OpenAI"""
    print("="*60)
    print("TICKET 4: REAL LLM EXECUTION TEST")
    print("="*60)
    
    # 1. Check services
    print("\n1. Checking services...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CHATDEV_URL}/api/health")
        print(f"   ChatDev: {resp.status_code}")
        
        resp = await client.get(f"{AGENTVERSE_URL}/webhooks/health")
        print(f"   AgentVerse: {resp.status_code}")
    
    # 2. List available workflows
    print("\n2. Available workflows:")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CHATDEV_URL}/api/workflows")
        workflows = resp.json().get("workflows", [])
        for w in workflows:
            print(f"   - {w}")
    
    # 3. Start a real workflow execution (using demo workflow for simplicity)
    print("\n3. Starting real workflow execution (demo workflow)...")
    session_name = f"real_test_{datetime.now().strftime('%H%M%S')}"
    room_id = "room_real_test"
    webhook_url = f"{AGENTVERSE_URL}/webhooks/chatdev/events"
    
    payload = {
        "yaml_file": "demo_simple_memory.yaml",  # Simpler workflow
        "task_prompt": "Write a short poem about AI agents working together",
        "session_name": session_name,
        "webhook_url": webhook_url,
        "room_id": room_id,
        "variables": {
            "BASE_URL": "https://api.openai.com/v1",
            "API_KEY": "sk-your-api-key-here"  # Set in chatdev-money/.env
        }
    }
    
    print(f"   Session: {session_name}")
    print(f"   Room: {room_id}")
    print(f"   Webhook: {webhook_url}")
    print(f"   Using model: gpt-4o-mini (default)")
    print(f"   Workflow: demo_simple_memory.yaml")
    
    print("\n   ⚠️  This will call OpenAI API and cost ~$0.05-0.10")
    print("   Executing in 5 seconds... (Ctrl+C to cancel)")
    await asyncio.sleep(5)
    
    print("\n   🚀 Executing workflow...")
    start_time = datetime.now()
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{CHATDEV_URL}/api/workflow/run",
            json=payload
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"   Response: {resp.status_code}")
        print(f"   Elapsed: {elapsed:.1f}s")
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"\n   ✅ Workflow completed!")
            print(f"   Session: {result.get('meta', {}).get('session_name')}")
            print(f"   Token usage: {result.get('meta', {}).get('token_usage')}")
            
            # Show final output preview
            final_output = result.get('final_output', {})
            content = final_output.get('content', '')
            if content:
                print(f"\n   Output preview:")
                print(f"   {content[:200]}..." if len(content) > 200 else f"   {content}")
            
            return session_name, True
        else:
            print(f"\n   ❌ Failed: {resp.text}")
            return session_name, False


if __name__ == "__main__":
    session_name, success = asyncio.run(test_real_execution())
    if success:
        print(f"\n✅ Ticket 4 COMPLETE: Real LLM execution successful ({session_name})")
    else:
        print(f"\n❌ Ticket 4 FAILED: ({session_name})")
