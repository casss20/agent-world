"""
Governance v2 Authentication & RBAC
Minimal JWT + role dependency for agent control plane
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Optional
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()

# JWT Configuration - In production, load from environment
JWT_SECRET = "governance-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


class UserPrincipal(BaseModel):
    """Authenticated user principal"""
    sub: str  # user ID or name
    roles: List[str]
    business_id: Optional[int] = None
    exp: Optional[datetime] = None


class TokenRequest(BaseModel):
    """Token generation request"""
    username: str
    password: str  # In production, hash this
    role: str = "operator"  # viewer, operator, governor, admin


def create_token(sub: str, roles: List[str], business_id: Optional[int] = None) -> str:
    """Create JWT token for user"""
    exp = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    payload = {
        "sub": sub,
        "roles": roles,
        "business_id": business_id,
        "exp": exp,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserPrincipal:
    """
    FastAPI dependency to get current authenticated user
    
    Usage:
        @app.post("/protected")
        async def protected(user: UserPrincipal = Depends(get_current_user)):
            ...
    """
    token = credentials.credentials
    
    # Try JWT decode first
    payload = decode_token(token)
    
    if payload:
        return UserPrincipal(
            sub=payload.get("sub", "unknown"),
            roles=payload.get("roles", []),
            business_id=payload.get("business_id"),
            exp=payload.get("exp")
        )
    
    # Fallback: Simple API key pattern (for quick testing)
    # Remove this in production and use only JWT
    if token == "governance-admin-key-123":
        return UserPrincipal(
            sub="admin",
            roles=["admin", "governor", "operator", "viewer"],
            business_id=None
        )
    elif token.startswith("operator-"):
        return UserPrincipal(
            sub=token,
            roles=["operator", "viewer"],
            business_id=None
        )
    elif token.startswith("viewer-"):
        return UserPrincipal(
            sub=token,
            roles=["viewer"],
            business_id=None
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )


# Role checker helpers
def require_roles(*required_roles: str):
    """
    Dependency factory to require specific roles
    
    Usage:
        @app.post("/admin-only")
        async def admin_action(
            user: UserPrincipal = Depends(require_roles("admin"))
        ):
            ...
    """
    async def role_checker(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        user_roles = set(user.roles)
        required = set(required_roles)
        
        if not required.intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {required_roles}"
            )
        return user
    return role_checker


# Pre-configured role requirements
require_admin = require_roles("admin")
require_governor = require_roles("admin", "governor")
require_operator = require_roles("admin", "governor", "operator")
require_viewer = require_roles("admin", "governor", "operator", "viewer")


# Permission checking helper
def has_permission(user: UserPrincipal, permission: str) -> bool:
    """Check if user has specific permission based on roles"""
    # Map roles to permissions
    role_permissions = {
        "viewer": ["agents:read", "memory:read"],
        "operator": ["agents:read", "agents:write", "tasks:submit"],
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
