"""
Ledger Client for Agent World
Provides governance checks, permission validation, and audit logging
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib
import json
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

class LedgerClient:
    """Client for interacting with Ledger governance system"""
    
    def __init__(self, db_session: Session, redis_client=None):
        self.db = db_session
        self.redis = redis_client
        self._capability_cache = {}
    
    async def check_permission(
        self,
        actor_id: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if actor has permission to perform action on resource.
        
        This is a simplified implementation. In production, this would:
        - Query the Ledger governance system
        - Check role assignments
        - Evaluate policies
        - Return allow/deny decision
        """
        context = context or {}
        
        # For now, allow all (replace with real governance checks)
        # TODO: Integrate with actual Ledger governance_v2 system
        
        # Example policy checks:
        # - Admin can do anything
        # - Governor can execute, classify
        # - Operator can register agents
        # - Viewer can only read
        
        # Extract role from context if provided
        role = context.get("role", "viewer")
        
        # Simple role-based access control
        role_permissions = {
            "admin": ["*"],
            "governor": [
                "governance:execute",
                "governance:classify",
                "agent:status:modify",
                "room:join:governor_approved",
                "blackboard:write:governor",
            ],
            "operator": [
                "agent:register",
                "agent:assign",
                "task:claim",
                "room:join",
            ],
            "viewer": [
                "agent:read",
                "room:read",
                "blackboard:read",
            ],
        }
        
        allowed_actions = role_permissions.get(role, [])
        
        # Check wildcard
        if "*" in allowed_actions:
            return True
        
        # Check exact match
        if action in allowed_actions:
            return True
        
        # Check wildcard prefix (e.g., "agent:*" matches "agent:register")
        for allowed in allowed_actions:
            if allowed.endswith("*") and action.startswith(allowed[:-1]):
                return True
        
        return False
    
    async def validate_capability(self, capability: str) -> bool:
        """Validate that a capability exists in the registry"""
        # Valid capabilities for Agent World
        valid_capabilities = {
            # Discovery
            "discover_trends",
            "analyze_sentiment",
            "scrape_reddit",
            "scrape_hackernews",
            "scrape_producthunt",
            
            # Content creation
            "write_article",
            "generate_image",
            "create_video",
            "edit_content",
            
            # Publishing
            "publish_blog",
            "publish_social",
            "schedule_post",
            "cross_post",
            
            # Analysis
            "track_revenue",
            "analyze_metrics",
            "generate_report",
            
            # Governance
            "classify_risk",
            "issue_token",
            "execute_action",
            "trigger_killswitch",
        }
        
        return capability in valid_capabilities
    
    async def audit_log(
        self,
        actor_type: str,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """
        Write immutable audit log entry.
        
        Returns the event_id of the created log entry.
        """
        from models import AuditLog
        
        # Get previous hash for chain
        last_log = self.db.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).first()
        
        prev_hash = last_log.event_hash if last_log else "0" * 64
        
        # Create event data for hashing
        event_data = {
            "actor_type": actor_type,
            "actor_id": actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "prev_hash": prev_hash,
        }
        
        # Calculate event hash
        event_hash = hashlib.sha256(
            json.dumps(event_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Create audit log entry
        log_entry = AuditLog(
            id=uuid.uuid4(),
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            decision=result,
            prev_hash=prev_hash,
            event_hash=event_hash,
            details=metadata or {},
            request_id=request_id,
            created_at=datetime.utcnow(),
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        return str(log_entry.id)
    
    async def get_audit_chain(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries with integrity verification"""
        from models import AuditLog
        
        logs = self.db.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": str(log.id),
                "actor_type": log.actor_type,
                "actor_id": log.actor_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "decision": log.decision,
                "event_hash": log.event_hash,
                "prev_hash": log.prev_hash,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    
    async def verify_audit_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of the entire audit chain"""
        from models import AuditLog
        
        logs = self.db.query(AuditLog).order_by(
            AuditLog.created_at.asc()
        ).all()
        
        if not logs:
            return {
                "total_events": 0,
                "verified_events": 0,
                "failed_events": 0,
                "chain_intact": True,
            }
        
        verified = 0
        failed = 0
        prev_hash = "0" * 64
        
        for log in logs:
            # Verify prev_hash matches
            if log.prev_hash != prev_hash:
                failed += 1
                continue
            
            # Recalculate hash
            event_data = {
                "actor_type": log.actor_type,
                "actor_id": log.actor_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "result": log.decision,
                "timestamp": log.created_at.isoformat(),
                "prev_hash": log.prev_hash,
            }
            
            calculated_hash = hashlib.sha256(
                json.dumps(event_data, sort_keys=True).encode()
            ).hexdigest()
            
            if calculated_hash == log.event_hash:
                verified += 1
            else:
                failed += 1
            
            prev_hash = log.event_hash
        
        return {
            "total_events": len(logs),
            "verified_events": verified,
            "failed_events": failed,
            "chain_intact": failed == 0,
            "first_event_id": str(logs[0].id),
            "last_event_id": str(logs[-1].id),
            "last_hash": logs[-1].event_hash if logs else None,
        }


# Singleton instance for dependency injection
_ledger_client = None

def get_ledger_client(db_session: Session, redis_client=None) -> LedgerClient:
    """Get or create Ledger client instance"""
    global _ledger_client
    if _ledger_client is None:
        _ledger_client = LedgerClient(db_session, redis_client)
    return _ledger_client
