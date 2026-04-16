"""
Governance v2 Authentication - DEPRECATED

This module is deprecated. All authentication functionality has been merged into
security_middleware.py to prevent JWT implementation drift.

Use security_middleware instead:
  - TokenPayload instead of UserPrincipal
  - require_admin(), require_governor(), etc. (callable) instead of require_roles
  - get_current_user from security_middleware

This file is kept for backward compatibility during transition but will be removed.
"""

import warnings
warnings.warn(
    "governance_v2.auth is deprecated. Use security_middleware instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from security_middleware for backward compatibility
from security_middleware import (
    get_current_user,
    require_admin,
    require_governor, 
    require_operator,
    TokenPayload as UserPrincipal
)
        "governor": ["agents:read", "agents:write", "governance:execute", "governance:classify"],
        "admin": ["*"]  # Wildcard permission
    }
    
    for role in user.roles:
        if role in role_permissions:
            perms = role_permissions[role]
            if "*" in perms or permission in perms:
                return True
    return False


# Audit logging helper
async def audit_log(
    action: str,
    actor: str,
    resource: str,
    result: str,
    metadata: Optional[Dict] = None
):
    """
    Log access control decisions
    
    In production, write to database or external logging system
    """
    from datetime import datetime
    import json
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "actor": actor,
        "resource": resource,
        "result": result,
        "metadata": metadata or {}
    }
    
    # For now, print to stdout. In production, write to DB
    print(f"[AUDIT] {json.dumps(log_entry)}")
    return log_entry
