#!/usr/bin/env python3
"""
Ledger 2.0 Integration Tests
Tests all 4 phases end-to-end
"""

import requests
import json
import sys
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
GOVERNANCE_URL = f"{BASE_URL}/governance/v2"


def test_phase1_core_governance():
    """Test Phase 1: Core Governance"""
    print("\n" + "="*60)
    print("PHASE 1: CORE GOVERNANCE")
    print("="*60)
    
    # Test 1: Health check
    print("\n🔹 Test 1: Governance Health Check")
    try:
        r = requests.get(f"{GOVERNANCE_URL}/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Status: {data['status']}")
        print(f"  ✅ Version: {data['version']}")
        print(f"  ✅ Phases: {', '.join(data['phases'])}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 2: Risk Classification
    print("\n🔹 Test 2: Risk Classification")
    try:
        r = requests.post(
            f"{GOVERNANCE_URL}/classify",
            params={"action": "read", "resource": "workflow:123"},
            json={},
            timeout=5
        )
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Risk Level: {data['risk_level']}")
        print(f"  ✅ Approval Path: {data['approval_path']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 3: Feature Flags
    print("\n🔹 Test 3: Feature Flags")
    try:
        r = requests.get(f"{GOVERNANCE_URL}/flags", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Flags loaded: {len(data)}")
        for flag, config in list(data.items())[:3]:
            print(f"     • {flag}: {config['rollout']}% rollout")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 4: Feature Flag Check
    print("\n🔹 Test 4: Feature Flag Check (Business 1)")
    try:
        r = requests.get(
            f"{GOVERNANCE_URL}/flags/auto_governor",
            params={"business_id": 1},
            timeout=5
        )
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ auto_governor: {data['enabled']}")
        print(f"  ✅ Rollout: {data['rollout_percentage']}%")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    print("\n  ✅ Phase 1: All tests passed")
    return True


def test_phase2_orchestration():
    """Test Phase 2: Orchestration"""
    print("\n" + "="*60)
    print("PHASE 2: ORCHESTRATION")
    print("="*60)
    
    # Test 1: Agent Registration
    print("\n🔹 Test 1: Agent Registration")
    try:
        r = requests.post(
            f"{GOVERNANCE_URL}/agents/register",
            json={
                "agent_id": "test_scout_001",
                "agent_type": "scout",
                "business_id": 1,
                "capabilities": [
                    {
                        "name": "discover_trends",
                        "risk_level": "safe",
                        "requires_approval": False,
                        "rate_limit": 100,
                        "dependencies": [],
                        "estimated_duration": 30
                    }
                ],
                "max_load": 10
            },
            timeout=5
        )
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Agent registered: {data['agent_id']}")
        print(f"  ✅ Capabilities: {data['capabilities']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 2: List Agents
    print("\n🔹 Test 2: List Agents")
    try:
        r = requests.get(f"{GOVERNANCE_URL}/agents", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Agents found: {data['count']}")
        for agent in data['agents'][:3]:
            print(f"     • {agent['agent_id']} ({agent['agent_type']}) - {agent['health']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 3: Agent Heartbeat
    print("\n🔹 Test 3: Agent Heartbeat")
    try:
        r = requests.post(
            f"{GOVERNANCE_URL}/agents/test_scout_001/heartbeat",
            params={"health_status": "healthy"},
            timeout=5
        )
        assert r.status_code == 200
        print(f"  ✅ Heartbeat acknowledged")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 4: Business Health
    print("\n🔹 Test 4: Business Health Check")
    try:
        r = requests.get(f"{GOVERNANCE_URL}/businesses/1/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Status: {data['status']}")
        print(f"  ✅ Healthy agents: {data['healthy']}/{data['total']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 5: Queue Status
    print("\n🔹 Test 5: Task Queue Status")
    try:
        r = requests.get(f"{GOVERNANCE_URL}/tasks/queue", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Pending: {data['pending']}")
        print(f"  ✅ Active: {data['active']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    print("\n  ✅ Phase 2: All tests passed")
    return True


def test_phase3_memory():
    """Test Phase 3: Memory & Audit"""
    print("\n" + "="*60)
    print("PHASE 3: MEMORY & AUDIT")
    print("="*60)
    
    # Test 1: Query Events
    print("\n🔹 Test 1: Query Events")
    try:
        r = requests.get(f"{GOVERNANCE_URL}/events", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Events found: {data['count']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 2: Consolidation Status
    print("\n🔹 Test 2: Memory Consolidation Status")
    try:
        r = requests.get(f"{GOVERNANCE_URL}/consolidate/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Should run: {data['should_run']}")
        print(f"  ✅ Min hours: {data['min_hours']}")
        print(f"  ✅ Min decisions: {data['min_decisions']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    print("\n  ✅ Phase 3: All tests passed")
    return True


def test_phase4_hardening():
    """Test Phase 4: Hardening"""
    print("\n" + "="*60)
    print("PHASE 4: HARDENING")
    print("="*60)
    
    # Test 1: Degradation Status
    print("\n🔹 Test 1: Degradation Status")
    try:
        r = requests.get(f"{GOVERNANCE_URL}/degradation/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Current level: {data['current_level']}")
        print(f"  ✅ Queue length: {data['action_queue_length']}")
        print(f"  ✅ Requires human: {data['requires_human']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 2: Component Health Update
    print("\n🔹 Test 2: Component Health Update")
    try:
        r = requests.post(
            f"{GOVERNANCE_URL}/degradation/component/test_component",
            params={"healthy": True},
            timeout=5
        )
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Component: {data['component']}")
        print(f"  ✅ Healthy: {data['healthy']}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # Test 3: Kill Switches
    print("\n🔹 Test 3: Kill Switches Status")
    try:
        r = requests.get(f"{GOVERNANCE_URL}/killswitches", timeout=5)
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ Kill switches: {len(data)}")
        for name, status in data.items():
            print(f"     • {name}: {'ACTIVE' if status['active'] else 'inactive'}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    print("\n  ✅ Phase 4: All tests passed")
    return True


def test_full_system():
    """Test Full System Status"""
    print("\n" + "="*60)
    print("FULL SYSTEM STATUS")
    print("="*60)
    
    try:
        r = requests.get(f"{GOVERNANCE_URL}/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        
        print("\n📊 Phase 1: Core Governance")
        print(f"   Feature flags: {len(data['phase1_governance']['feature_flags'])}")
        
        print("\n📊 Phase 2: Orchestration")
        print(f"   Registered agents: {data['phase2_orchestration']['registered_agents']}")
        print(f"   Pending tasks: {data['phase2_orchestration']['queue_status']['pending']}")
        print(f"   Active tasks: {data['phase2_orchestration']['queue_status']['active']}")
        print(f"   Auto-governor jobs: {data['phase2_orchestration']['auto_governor']['jobs']}")
        
        print("\n📊 Phase 3: Memory")
        print(f"   Total consolidations: {data['phase3_memory']['consolidation_state'].get('total_consolidations', 0)}")
        
        print("\n📊 Phase 4: Hardening")
        print(f"   Degradation level: {data['phase4_hardening']['degradation_level']}")
        print(f"   Kill switches: {len(data['phase4_hardening']['kill_switches'])}")
        
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


def main():
    print("="*60)
    print("LEDGER 2.0 INTEGRATION TEST SUITE")
    print("="*60)
    print(f"\nTesting against: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    
    results = []
    
    # Run all phase tests
    results.append(("Phase 1: Core Governance", test_phase1_core_governance()))
    results.append(("Phase 2: Orchestration", test_phase2_orchestration()))
    results.append(("Phase 3: Memory & Audit", test_phase3_memory()))
    results.append(("Phase 4: Hardening", test_phase4_hardening()))
    results.append(("Full System", test_full_system()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Ledger 2.0 is operational.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test suite(s) failed.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted.")
        sys.exit(1)
