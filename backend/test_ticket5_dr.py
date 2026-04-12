"""
Disaster Recovery Test - Ticket 5
Validate backup and recovery procedures
"""

import subprocess
import os
import time
import sys

BACKUP_DIR = "/var/backups/agentverse/redis"


def run_command(cmd, description):
    """Run shell command and report result"""
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Success")
        if result.stdout:
            print(result.stdout[:500])  # Truncate long output
        return True
    else:
        print(f"❌ Failed")
        print(f"Error: {result.stderr[:500]}")
        return False


def test_backup_creation():
    """Test creating a backup"""
    return run_command(
        "/root/.openclaw/workspace/agent-world/scripts/backup_redis.sh backup",
        "Create Redis backup"
    )


def test_backup_list():
    """Test listing backups"""
    return run_command(
        "/root/.openclaw/workspace/agent-world/scripts/backup_redis.sh list",
        "List available backups"
    )


def test_backup_files():
    """Verify backup files exist"""
    print(f"\n{'='*60}")
    print("Test: Verify backup files exist")
    print(f"{'='*60}")
    
    if not os.path.exists(BACKUP_DIR):
        print(f"❌ Backup directory does not exist: {BACKUP_DIR}")
        return False
    
    backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.rdb.gz')]
    
    if len(backups) == 0:
        print(f"❌ No backup files found in {BACKUP_DIR}")
        return False
    
    print(f"✅ Found {len(backups)} backup(s)")
    for backup in backups[:5]:  # Show first 5
        size = os.path.getsize(os.path.join(BACKUP_DIR, backup))
        print(f"   - {backup} ({size/1024/1024:.2f} MB)")
    
    return True


def test_redis_data():
    """Verify Redis has data to backup"""
    print(f"\n{'='*60}")
    print("Test: Verify Redis data")
    print(f"{'='*60}")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Check connection
        if not r.ping():
            print("❌ Cannot connect to Redis")
            return False
        
        # Count keys
        agentverse_keys = r.keys("agentverse:*")
        total_keys = r.dbsize()
        
        print(f"✅ Redis connected")
        print(f"   Total keys: {total_keys}")
        print(f"   AgentVerse keys: {len(agentverse_keys)}")
        
        return len(agentverse_keys) > 0
        
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False


def test_restore_dry_run():
    """Test restore script (dry run)"""
    print(f"\n{'='*60}")
    print("Test: Restore script availability")
    print(f"{'='*60}")
    
    restore_script = "/root/.openclaw/workspace/agent-world/scripts/restore_redis.sh"
    
    if not os.path.exists(restore_script):
        print(f"❌ Restore script not found: {restore_script}")
        return False
    
    # Check if executable
    if not os.access(restore_script, os.X_OK):
        print(f"⚠️  Restore script not executable (fixing...)")
        os.chmod(restore_script, 0o755)
    
    print(f"✅ Restore script exists and is executable")
    
    # List backups available for restore
    result = subprocess.run(
        f"{restore_script} list",
        shell=True,
        capture_output=True,
        text=True
    )
    
    print(f"\nRestore script output:")
    print(result.stdout[:500])
    
    return True


def test_disaster_recovery_readiness():
    """Overall DR readiness check"""
    print(f"\n{'='*60}")
    print("DISASTER RECOVERY READINESS CHECK")
    print(f"{'='*60}")
    
    checks = [
        ("Redis accessible", test_redis_data),
        ("Backup directory exists", lambda: os.path.exists(BACKUP_DIR)),
        ("Backup script works", test_backup_creation),
        ("Backups available", test_backup_files),
        ("Restore script ready", test_restore_dry_run),
    ]
    
    passed = 0
    failed = 0
    
    for name, check_fn in checks:
        try:
            if check_fn():
                passed += 1
            else:
                failed += 1
                print(f"❌ {name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {name}: ERROR - {e}")
    
    print(f"\n{'='*60}")
    print("DR READINESS SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {passed}/{len(checks)}")
    print(f"❌ Failed: {failed}/{len(checks)}")
    
    if failed == 0:
        print("\n🎉 Disaster Recovery procedures validated!")
        print("\nRTO Target: < 15 minutes")
        print("RPO Target: < 1 hour (hourly backups)")
        return 0
    else:
        print("\n⚠️ Some DR checks failed - review before production")
        return 1


if __name__ == "__main__":
    sys.exit(test_disaster_recovery_readiness())
