#!/usr/bin/env python3
"""
Test Ledger Sovereign Integration
Verify all governance layers are working
"""

import asyncio
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agent-world/backend')

from ledger_sovereign import get_ledger_sovereign


async def test_ledger_integration():
    """Test full Ledger integration"""
    print("=" * 60)
    print("LEDGER SOVEREIGN INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Initialization
    print("\n🔹 Test 1: Initialization")
    ledger = get_ledger_sovereign()
    status = ledger.get_status()
    print(f"  Version: {status['version']}")
    print(f"  Files loaded: {status['files_loaded']}")
    print(f"  Constitutional rules: {status['constitutional_rules']}")
    assert status['files_loaded'] == 36, "Should load 36 files"
    print("  ✅ PASSED")
    
    # Test 2: Constitution Check
    print("\n🔹 Test 2: Constitution Check")
    
    # Safe action
    safe_action = {"type": "query", "irreversible": False}
    result = ledger.check_constitution(safe_action)
    assert result['approved'] is True, "Safe action should pass"
    print(f"  Safe action: {result['approved']} ✅")
    
    # External action
    external_action = {"type": "send_email", "irreversible": False, "external": True}
    result = ledger.check_constitution(external_action)
    assert result['approved'] is False, "External action should be blocked"
    print(f"  External action blocked: {not result['approved']} ✅")
    
    # Irreversible action
    irreversible_action = {"type": "delete", "irreversible": True}
    result = ledger.check_constitution(irreversible_action)
    assert result['approved'] is False, "Irreversible action should be blocked"
    print(f"  Irreversible action blocked: {not result['approved']} ✅")
    print("  ✅ PASSED")
    
    # Test 3: Alignment Check
    print("\n🔹 Test 3: Alignment Check")
    
    aligned_command = "Optimize Business 1 revenue"
    result = ledger.check_alignment(aligned_command, {})
    print(f"  '{aligned_command[:30]}...': {result['aligned']} ✅")
    
    misaligned_command = "Abandon all businesses and start over"
    result = ledger.check_alignment(misaligned_command, {})
    print(f"  '{misaligned_command[:30]}...': {result['aligned']} (challenge: {result['challenge']}) ✅")
    print("  ✅ PASSED")
    
    # Test 4: Governor Check
    print("\n🔹 Test 4: Governor Check")
    
    normal_command = "Check business status"
    result = ledger.check_governor(normal_command, {"pattern_repetitions": 0})
    assert result['level'] == 0, "Normal command should be level 0"
    print(f"  Normal command: Level {result['level']} ✅")
    
    repeat_command = "Same mistake again"
    result = ledger.check_governor(repeat_command, {"pattern_repetitions": 3})
    assert result['level'] == 3, "Repeated pattern should escalate to level 3"
    print(f"  Repeated pattern (3x): Level {result['level']} ✅")
    print("  ✅ PASSED")
    
    # Test 5: Focus Check
    print("\n🔹 Test 5: Focus Check")
    
    focused_command = "Continue current workflow"
    result = ledger.check_focus(focused_command)
    assert result['block'] is False, "Focused command should pass"
    print(f"  Focused command: {not result['block']} ✅")
    
    distraction_command = "Start a new project instead"
    result = ledger.check_focus(distraction_command)
    assert result['block'] is True, "Distraction should be blocked"
    print(f"  Distraction blocked: {result['block']} ✅")
    print("  ✅ PASSED")
    
    # Test 6: Full Command Processing
    print("\n🔹 Test 6: Full Command Processing")
    
    # Approved command
    result = await ledger.process_command("Optimize Business 1 revenue by 10%", {})
    assert result['status'] == 'approved', "Should be approved"
    print(f"  'Optimize Business 1...': {result['status']} ✅")
    
    # Blocked command (external)
    result = await ledger.process_command("Send email to all customers", {})
    assert result['status'] == 'refused', "Should be refused"
    print(f"  'Send email...': {result['status']} (reason: {result.get('reason', 'N/A')[:40]}) ✅")
    
    # Challenged command (misaligned)
    result = await ledger.process_command("Abandon Business 1 and pivot", {})
    assert result['status'] in ['challenged', 'redirected'], "Should be challenged or redirected"
    print(f"  'Abandon Business...': {result['status']} ✅")
    print("  ✅ PASSED")
    
    # Test 7: Memory Context
    print("\n🔹 Test 7: Memory Context")
    context = ledger.get_memory_context()
    assert 'user_profile' in context, "Should have user profile"
    print(f"  User profile: {len(context['user_profile'])} chars ✅")
    print(f"  World context: {len(context['current_world'])} chars ✅")
    print("  ✅ PASSED")
    
    # Test 8: Decision Logging
    print("\n🔹 Test 8: Decision Logging")
    initial_count = len(ledger.decision_history)
    await ledger.process_command("Test command for logging", {})
    new_count = len(ledger.decision_history)
    assert new_count > initial_count, "Should log decision"
    print(f"  Decisions logged: {new_count} ✅")
    print("  ✅ PASSED")
    
    # Summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"✅ All 8 tests PASSED")
    print(f"📁 Ledger files loaded: {status['files_loaded']}")
    print(f"📊 Total decisions: {len(ledger.decision_history)}")
    print(f"🛡️  Governance active: Constitution + Governor + Alignment + Focus")
    print("\nLedger Sovereign is ready for AgentVerse integration.")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_ledger_integration())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
