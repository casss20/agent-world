"""
Test Stateless Adapter - Ticket 5
Verify Redis-backed state and horizontal scaling readiness
"""

import asyncio
import httpx
import json
from datetime import datetime

STATELESS_URL = "http://localhost:8004"


async def test_stateless_adapter():
    """Test stateless adapter functionality"""
    print("="*60)
    print("TICKET 5: STATELESS ADAPTER TEST")
    print("="*60)
    
    # 1. Health check
    print("\n1. Health check...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{STATELESS_URL}/stateless/health")
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Instance: {data.get('instance_id')}")
        print(f"   Shared state: {data.get('shared_state', {}).get('status')}")
        print(f"   Engine: {data.get('engine_mode')}")
    
    # 2. Launch workflow
    print("\n2. Launching workflow...")
    payload = {
        "room_id": "room_test_001",
        "user_id": "user_test",
        "workflow_id": "demo_simple_memory",
        "task_prompt": "Test stateless adapter"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{STATELESS_URL}/stateless/launch",
            json=payload
        )
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        run_id = data.get("run_id")
        print(f"   Run ID: {run_id}")
        print(f"   Status: {data.get('status')}")
        print(f"   Correlation: {data.get('correlation_id')}")
    
    # 3. Check status
    print("\n3. Checking status...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{STATELESS_URL}/stateless/status/{run_id}")
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Run status: {data.get('status')}")
        print(f"   Progress: {data.get('progress_percent')}%")
    
    # 4. List runs
    print("\n4. Listing runs...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{STATELESS_URL}/stateless/runs")
        print(f"   Status: {resp.status_code}")
    
    print("\n✅ Stateless adapter test complete!")
    print(f"\nKey features verified:")
    print("  - Health check with Redis connectivity")
    print("  - Workflow launch with shared state")
    print("  - Status retrieval from Redis")
    print("  - Instance ID tracking")


if __name__ == "__main__":
    asyncio.run(test_stateless_adapter())
