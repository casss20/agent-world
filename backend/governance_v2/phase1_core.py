# Phase 1: Core Governance Implementation
## CapabilityIssuer + RiskClassifier + Feature Flags

import hashlib
import secrets
import time
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
from enum import Enum


class RiskLevel(Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    CRITICAL = "critical"


@dataclass
class CapabilityToken:
    """Scoped, time-bound capability token"""
    token: str
    agent_id: str
    action: str
    resource: str
    scope: List[str]
    expires_at: datetime
    constraints: Dict
    issued_at: datetime = field(default_factory=datetime.utcnow)
    used_count: int = 0
    max_uses: int = 1


class CapabilityIssuer:
    """
    Issues scoped, time-bound capability tokens.
    All agents must request tokens before executing actions.
    """
    
    def __init__(self, constitution_enforcer):
        self.constitution = constitution_enforcer
        self.active_tokens: Dict[str, CapabilityToken] = {}
        self.revoked_tokens: set = set()
        
    async def issue_token(
        self,
        agent_id: str,
        requested_action: str,
        target_resource: str,
        context: Dict,
        ttl_seconds: int = 3600
    ) -> Optional[CapabilityToken]:
        """
        Issue a capability token after constitution validation.
        
        Flow:
        1. Check constitution rules
        2. Validate context permissions
        3. Generate scoped token
        4. Log to audit
        """
        # Gate 1: Constitution check (instant)
        permitted, reason = await self.constitution.check_action(
            action=requested_action,
            resource=target_resource,
            context=context
        )
        
        if not permitted:
            return None
        
        # Determine scope based on action/resource
        scope = self._derive_scope(requested_action, target_resource)
        
        # Generate cryptographically secure token
        token_bytes = secrets.token_bytes(32)
        token_hash = hashlib.sha256(token_bytes).hexdigest()
        
        # Build constraints
        constraints = {
            "max_calls": self._get_max_calls(requested_action),
            "allowed_hours": list(range(24)),  # Default: all hours
            "require_dual_auth": self._requires_dual_auth(requested_action),
            "business_id": context.get("business_id"),
            "risk_level": self._classify_risk(requested_action)
        }
        
        token = CapabilityToken(
            token=token_hash,
            agent_id=agent_id,
            action=requested_action,
            resource=target_resource,
            scope=scope,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
            constraints=constraints,
            max_uses=constraints["max_calls"]
        )
        
        self.active_tokens[token_hash] = token
        
        # Log to audit
        await self._log_issuance(token)
        
        return token
    
    async def verify_token(self, token_str: str, action: str, resource: str) -> bool:
        """Verify token is valid, not expired, and matches action/resource."""
        if token_str in self.revoked_tokens:
            return False
        
        token = self.active_tokens.get(token_str)
        if not token:
            return False
        
        # Check expiry
        if datetime.utcnow() > token.expires_at:
            return False
        
        # Check action/resource match
        if token.action != action or token.resource != resource:
            return False
        
        # Check usage limit
        if token.used_count >= token.max_uses:
            return False
        
        # Check business hours constraint
        if not self._check_time_constraint(token.constraints.get("allowed_hours", [])):
            return False
        
        return True
    
    async def consume_token(self, token_str: str) -> bool:
        """Mark token as used. Returns True if consumption successful."""
        token = self.active_tokens.get(token_str)
        if not token:
            return False
        
        token.used_count += 1
        
        if token.used_count >= token.max_uses:
            # Auto-revoke after max uses
            await self.revoke_token(token_str, reason="max_uses_exceeded")
        
        return True
    
    async def revoke_token(self, token_str: str, reason: str = "manual"):
        """Emergency revocation of a token."""
        self.revoked_tokens.add(token_str)
        if token_str in self.active_tokens:
            del self.active_tokens[token_str]
        await self._log_revocation(token_str, reason)
    
    def _derive_scope(self, action: str, resource: str) -> List[str]:
        """Derive permission scope from action and resource."""
        scopes = [f"action:{action}"]
        
        # Parse resource type
        if ":" in resource:
            resource_type = resource.split(":")[0]
            scopes.append(f"resource:{resource_type}")
        
        # Add action category
        if action in ["read", "list", "search"]:
            scopes.append("category:read_only")
        elif action in ["write", "update", "create"]:
            scopes.append("category:write")
        elif action in ["delete", "destroy", "revoke"]:
            scopes.append("category:destructive")
        
        return scopes
    
    def _get_max_calls(self, action: str) -> int:
        """Determine max uses based on action sensitivity."""
        limits = {
            "read": 100,
            "search": 50,
            "create": 10,
            "update": 10,
            "delete": 1,
            "publish": 1,
            "execute": 5
        }
        return limits.get(action, 1)
    
    def _requires_dual_auth(self, action: str) -> bool:
        """Determine if action requires dual authorization."""
        return action in ["delete", "destroy", "revoke", "transfer_ownership"]
    
    def _classify_risk(self, action: str) -> RiskLevel:
        """Classify action risk level."""
        safe_actions = ["read", "list", "search", "get"]
        critical_actions = ["delete", "destroy", "revoke", "transfer_ownership", "execute"]
        
        if action in safe_actions:
            return RiskLevel.SAFE
        elif action in critical_actions:
            return RiskLevel.CRITICAL
        return RiskLevel.MEDIUM
    
    def _check_time_constraint(self, allowed_hours: List[int]) -> bool:
        """Check if current hour is within allowed hours."""
        current_hour = datetime.utcnow().hour
        return current_hour in allowed_hours
    
    async def _log_issuance(self, token: CapabilityToken):
        """Log token issuance to audit."""
        # Implementation would write to audit system
        pass
    
    async def _log_revocation(self, token_str: str, reason: str):
        """Log token revocation to audit."""
        pass


class RiskClassifier:
    """
    Classifies actions into risk levels and determines approval path.
    """
    
    CLASSIFICATION_MATRIX = {
        # (action_type, data_sensitivity) -> (risk_level, approval_path)
        ("read", "public"): (RiskLevel.SAFE, "auto"),
        ("read", "private"): (RiskLevel.MEDIUM, "ledger_check"),
        ("write", "public"): (RiskLevel.MEDIUM, "ledger_check"),
        ("write", "private"): (RiskLevel.CRITICAL, "human_required"),
        ("external", "any"): (RiskLevel.CRITICAL, "human_required"),
        ("irreversible", "any"): (RiskLevel.CRITICAL, "explicit_confirm"),
    }
    
    def __init__(self, constitution_enforcer):
        self.constitution = constitution_enforcer
    
    async def classify(
        self,
        action: str,
        resource: str,
        context: Dict
    ) -> tuple[RiskLevel, str, str]:
        """
        Classify action risk and determine approval path.
        
        Returns:
            (risk_level, approval_path, reasoning)
        """
        # Extract action type
        action_type = self._categorize_action(action)
        
        # Determine data sensitivity
        sensitivity = self._determine_sensitivity(resource, context)
        
        # Check constitution rules
        constitutional_risk = await self._check_constitution(action, context)
        
        # Look up in classification matrix
        key = (action_type, sensitivity)
        if key in self.CLASSIFICATION_MATRIX:
            risk_level, approval_path = self.CLASSIFICATION_MATRIX[key]
        else:
            risk_level = RiskLevel.MEDIUM
            approval_path = "ledger_check"
        
        # Constitution can escalate risk
        if constitutional_risk:
            risk_level = RiskLevel.CRITICAL
            approval_path = "human_required"
        
        reasoning = f"Action '{action}' on '{resource}' classified as {risk_level.value}"
        
        return risk_level, approval_path, reasoning
    
    def _categorize_action(self, action: str) -> str:
        """Categorize action into type."""
        read_actions = ["read", "list", "search", "get", "view", "fetch"]
        write_actions = ["write", "update", "create", "modify", "edit"]
        external_actions = ["send", "publish", "notify", "email", "post", "share"]
        destructive_actions = ["delete", "destroy", "revoke", "remove"]
        
        if action in read_actions:
            return "read"
        elif action in destructive_actions:
            return "irreversible"
        elif action in external_actions:
            return "external"
        elif action in write_actions:
            return "write"
        return "write"  # Default
    
    def _determine_sensitivity(self, resource: str, context: Dict) -> str:
        """Determine if resource contains sensitive data."""
        sensitive_patterns = ["user", "customer", "revenue", "financial", "private", "secret"]
        
        resource_lower = resource.lower()
        if any(pattern in resource_lower for pattern in sensitive_patterns):
            return "private"
        
        # Check context for sensitivity markers
        if context.get("contains_pii") or context.get("is_confidential"):
            return "private"
        
        return "public"
    
    async def _check_constitution(self, action: str, context: Dict) -> bool:
        """Check if action violates constitutional rules."""
        # This would integrate with Ledger constitution
        return False


class FeatureFlagController:
    """
    Dynamic feature flags with per-business rollout and kill switches.
    """
    
    def __init__(self):
        self.flags: Dict[str, Dict] = {}
        self._load_default_flags()
    
    def _load_default_flags(self):
        """Load default feature flag configuration."""
        self.flags = {
            "auto_governor": {
                "enabled": True,
                "rollout_percentage": 100,
                "allowed_businesses": [1, 2, 3, 4, 5, 6, 7, 8],
                "requires_ledger_approval": False
            },
            "memory_consolidation": {
                "enabled": True,
                "rollout_percentage": 100,
                "allowed_businesses": [1, 2, 3, 4, 5, 6, 7, 8],
                "requires_ledger_approval": False
            },
            "autonomous_repair": {
                "enabled": False,  # Kill switch ready
                "rollout_percentage": 0,
                "allowed_businesses": [],
                "requires_ledger_approval": True
            },
            "cross_business_memory": {
                "enabled": True,
                "rollout_percentage": 50,
                "allowed_businesses": [1, 2],  # A/B test
                "requires_ledger_approval": True
            },
            "affiliate_auto_insert": {
                "enabled": False,
                "rollout_percentage": 0,
                "allowed_businesses": [],
                "requires_ledger_approval": True
            }
        }
    
    def can_use(self, capability: str, business_id: int) -> bool:
        """
        Check if business can use a capability.
        
        Checks (in order):
        1. Is feature enabled?
        2. Is business in allowed list?
        3. Is business in rollout percentage?
        """
        flag = self.flags.get(capability)
        if not flag:
            return False
        
        # Check enabled
        if not flag["enabled"]:
            return False
        
        # Check allowed businesses
        if business_id not in flag["allowed_businesses"]:
            return False
        
        # Check rollout percentage (deterministic hash)
        if not self._in_rollout(business_id, flag["rollout_percentage"]):
            return False
        
        return True
    
    def _in_rollout(self, business_id: int, percentage: int) -> bool:
        """Deterministically check if business is in rollout percentage."""
        # Hash business_id to get consistent 0-99 value
        hash_val = int(hashlib.md5(str(business_id).encode()).hexdigest(), 16) % 100
        return hash_val < percentage
    
    def emergency_kill(self, capability: str, reason: str = "emergency"):
        """Emergency kill switch - instantly disable a capability."""
        if capability in self.flags:
            self.flags[capability]["enabled"] = False
            self.flags[capability]["rollout_percentage"] = 0
            # Log the kill
            print(f"🚨 Emergency kill for {capability}: {reason}")
    
    def enable_for_business(self, capability: str, business_id: int):
        """Enable a capability for a specific business."""
        if capability in self.flags:
            if business_id not in self.flags[capability]["allowed_businesses"]:
                self.flags[capability]["allowed_businesses"].append(business_id)
    
    def update_rollout(self, capability: str, percentage: int):
        """Update rollout percentage for gradual ramp-up."""
        if capability in self.flags:
            self.flags[capability]["rollout_percentage"] = max(0, min(100, percentage))
    
    def get_status(self) -> Dict:
        """Get current status of all feature flags."""
        return {
            capability: {
                "enabled": flag["enabled"],
                "rollout": flag["rollout_percentage"],
                "businesses": len(flag["allowed_businesses"])
            }
            for capability, flag in self.flags.items()
        }


# Integration with existing Ledger
class LedgerGovernanceV2:
    """
    Enhanced Ledger with Phase 1 governance components.
    """
    
    def __init__(self, ledger_sovereign):
        self.ledger = ledger_sovereign
        self.capability_issuer = CapabilityIssuer(ledger_sovereign)
        self.risk_classifier = RiskClassifier(ledger_sovereign)
        self.feature_flags = FeatureFlagController()
    
    async def execute_action(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: Dict
    ) -> Dict:
        """
        Execute an action with full governance pipeline.
        
        Flow:
        1. Check feature flags
        2. Classify risk
        3. Issue capability token
        4. Execute if approved
        5. Consume token
        6. Log to audit
        """
        business_id = context.get("business_id")
        
        # Check feature flag
        if not self.feature_flags.can_use(action, business_id):
            return {
                "status": "blocked",
                "reason": "Feature not enabled for this business"
            }
        
        # Classify risk
        risk_level, approval_path, reasoning = await self.risk_classifier.classify(
            action, resource, context
        )
        
        # Handle based on approval path
        if approval_path == "auto":
            # Issue token and execute
            token = await self.capability_issuer.issue_token(
                agent_id, action, resource, context
            )
            if token:
                return await self._execute_with_token(token, action, resource, context)
            
        elif approval_path == "ledger_check":
            # Check with Ledger constitution
            approved, reason = await self.ledger.check_command(
                f"{action} on {resource}", context
            )
            if approved:
                token = await self.capability_issuer.issue_token(
                    agent_id, action, resource, context
                )
                if token:
                    return await self._execute_with_token(token, action, resource, context)
            return {"status": "refused", "reason": reason}
            
        elif approval_path == "human_required":
            # Queue for human approval
            return {
                "status": "pending_approval",
                "risk_level": risk_level.value,
                "reasoning": reasoning,
                "approval_queue_position": await self._queue_for_approval(
                    agent_id, action, resource, context
                )
            }
        
        return {"status": "error", "reason": "Unknown approval path"}
    
    async def _execute_with_token(
        self,
        token: CapabilityToken,
        action: str,
        resource: str,
        context: Dict
    ) -> Dict:
        """Execute action with valid token."""
        # Verify token
        valid = await self.capability_issuer.verify_token(token.token, action, resource)
        if not valid:
            return {"status": "error", "reason": "Invalid token"}
        
        # Execute (this would call the actual action)
        result = {"status": "executed", "action": action, "resource": resource}
        
        # Consume token
        await self.capability_issuer.consume_token(token.token)
        
        return result
    
    async def _queue_for_approval(self, agent_id, action, resource, context) -> int:
        """Queue action for human approval."""
        # This would integrate with approval queue system
        return 1


# Export for use
__all__ = [
    'CapabilityIssuer',
    'CapabilityToken',
    'RiskClassifier',
    'RiskLevel',
    'FeatureFlagController',
    'LedgerGovernanceV2'
]
