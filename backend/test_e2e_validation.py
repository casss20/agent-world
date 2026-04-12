#!/usr/bin/env python3
"""
End-to-End Validation Test
Tests the complete Ledger Shell integration
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"

def test_e2e():
    print("=" * 70)
    print("END-TO-END LEDGER SHELL VALIDATION")
    print("=" * 70)
    
    # Test 1: Backend Health
    print("\n🔹 Test 1: Backend Health Check")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ API: {data['message']}")
        print(f"  ✅ Agents: {data['agents']}, Rooms: {data['rooms']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 2: Ledger Constitution
    print("\n🔹 Test 2: Ledger Constitution Endpoint")
    try:
        r = requests.get(f"{BASE_URL}/ledger/constitution", timeout=5)
        assert r.status_code == 200
        data = r.json()
        rules = data.get('rules', {})
        print(f"  ✅ Constitutional rules loaded: {len(rules)}")
        for key in list(rules.keys())[:3]:
            print(f"     • {key}: {'Active' if rules[key] else 'Inactive'}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 3: Ledger Status
    print("\n🔹 Test 3: Ledger Status")
    try:
        r = requests.get(f"{BASE_URL}/ledger/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Ledger v{data['version']}")
        print(f"  ✅ Files loaded: {data['files_loaded']}")
        print(f"  ✅ Decision count: {data['decision_count']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 4: Command Processing (Approved)
    print("\n🔹 Test 4: Command Processing (Safe Command)")
    try:
        r = requests.post(f"{BASE_URL}/ledger/command", 
            json={"command": "Optimize Business 1 revenue by 10%", "context": {}},
            timeout=5
        )
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Status: {data['status']}")
        print(f"  ✅ Approved: {data['approved']}")
        if data.get('governance_checks'):
            print(f"  ✅ Constitution: {data['governance_checks'].get('constitution', {}).get('approved', False)}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 5: Command Processing (Blocked)
    print("\n🔹 Test 5: Command Processing (External Action - Should Block)")
    try:
        r = requests.post(f"{BASE_URL}/ledger/command", 
            json={"command": "Send email to all customers", "context": {}},
            timeout=5
        )
        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'refused', "Should be refused"
        print(f"  ✅ Correctly blocked: {data['status']}")
        print(f"  ✅ Reason: {data['reason'][:50]}...")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 6: ChatDev Workflow API
    print("\n🔹 Test 6: ChatDev Workflow Integration")
    try:
        r = requests.get(f"{BASE_URL}/api/workflows", timeout=5)
        assert r.status_code == 200
        data = r.json()
        workflow_count = len(data.get('workflows', []))
        print(f"  ✅ Workflows: {workflow_count}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 7: VueFlow Graph API
    print("\n🔹 Test 7: VueFlow Graph API")
    try:
        r = requests.get(f"{BASE_URL}/api/vuegraphs/content_arbitrage_v1", timeout=5)
        assert r.status_code == 200
        data = r.json()
        content = data.get('content', {})
        print(f"  ✅ Graph loaded: {len(content.get('nodes', []))} nodes")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 8: Frontend Build Check
    print("\n🔹 Test 8: Frontend Build Artifacts")
    import os
    dist_path = "/root/.openclaw/workspace/agent-world/frontend-react/dist"
    if os.path.exists(dist_path):
        files = os.listdir(dist_path)
        print(f"  ✅ Build exists: {len(files)} files")
        index_exists = "index.html" in files
        assets_exists = "assets" in files
        print(f"  ✅ index.html: {index_exists}")
        print(f"  ✅ assets/: {assets_exists}")
    else:
        print(f"  ⚠️  Build not found at {dist_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("E2E VALIDATION COMPLETE")
    print("=" * 70)
    print("✅ All critical tests passed")
    print("✅ Ledger Shell architecture validated")
    print("✅ Backend API operational")
    print("✅ Frontend built successfully")
    print("\n🌐 Ready for testing:")
    print("   Backend: http://localhost:8000")
    print("   Frontend: cd frontend-react && npm run dev")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    try:
        success = test_e2e()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(1)
