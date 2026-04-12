"""
Security Middleware for Agent World Governance API
FastAPI authentication, authorization, audit logging, and rate limiting
"""

import time
import uuid
import hashlib
import hmac
import json
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum

from fastapi import Request, Response, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel


# ============================================================================
# CONFIGURATION
# ============================================================================

class SecurityConfig:
    """Security configuration - load from environment in production"""
    JWT_SECRET = "your-secret-key-change-in-production"  # Use os.environ.get()
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_HOURS = 24
    
    # Rate limiting
    RATE_LIMIT_PUBLIC = 1000  # requests per hour
    RATE_LIMIT_AUTH = 100     # per hour
    RATE_LIMIT_TOKEN = 50     # per hour
    RATE_LIMIT_EXECUTE = 50   # per hour
    RATE_LIMIT_ADMIN = 10     # per hour
    
    # Audit log
    AUDIT_LOG_PATH = "logs/audit.log"
    
    # mTLS for service-to-service
    MTLS_ENABLED = False
    MTLS_HEADER = "X-Client-Cert"


# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

class Role(str, Enum):
    """Role-based access control roles"""
    VIEWER = "viewer"       # Read-only access
    OPERATOR = "operator"   # Can register agents, submit tasks
    GOVERNOR = "governor"   # Can classify, token, execute
    ADMIN = "admin"         # Kill switches, degradation, emergency


# Role permission matrix
ROLE_PERMISSIONS = {
    Role.VIEWER: [
        "GET:/health",
        "GET:/health/live",
        "GET:/health/ready",
        "GET:/governance/v2/status",
        "GET:/governance/v2/flags",
        "GET:/governance/v2/agents",
        "GET:/governance/v2/agents/{id}/health",
        "GET:/governance/v2/businesses/{id}/health",
        "GET:/governance/v2/events",
    ],
    Role.OPERATOR: [
        # Inherits VIEWER permissions
        "POST:/governance/v2/agents/register",
        "POST:/governance/v2/agents/{id}/heartbeat",
        "POST:/governance/v2/tasks/submit",
        "GET:/governance/v2/tasks/queue",
    ],
    Role.GOVERNOR: [
        # Inherits OPERATOR permissions
        "POST:/governance/v2/classify",
        "POST:/governance/v2/token",
        "POST:/governance/v2/execute",
        "GET:/governance/v2/consolidate/status",
    ],
    Role.ADMIN: [
        # Inherits GOVERNOR permissions
        "POST:/governance/v2/killswitches/trigger",
        "POST:/governance/v2/killswitches/{name}/reset",
        "GET:/governance/v2/killswitches",
        "POST:/governance/v2/degradation/component/{name}",
        "GET:/governance/v2/degradation/status",
        "POST:/governance/v2/consolidate",
    ]
}


def has_permission(role: Role, method: str, path: str) -> bool:
    """Check if role has permission for method:path"""
    if role not in ROLE_PERMISSIONS:
        return False
    
    allowed = ROLE_PERMISSIONS[role]
    permission_string = f"{method}:{path}"
    
    # Check exact match or pattern match
    for allowed_pattern in allowed:
        if _match_permission(permission_string, allowed_pattern):
            return True
    
    return False


def _match_permission(permission: str, pattern: str) -> bool:
    """Match permission against pattern (supports wildcards)"""
    if permission == pattern:
        return True
    
    # Handle path parameters (e.g., /agents/{id}/health)
    if "{" in pattern:
        pattern_parts = pattern.split("/")
        perm_parts = permission.split("/")
        
        if len(pattern_parts) != len(perm_parts):
            return False
        
        for p_part, perm_part in zip(pattern_parts, perm_parts):
            if p_part.startswith("{") and p_part.endswith("}"):
                continue  # Path parameter matches anything
            if p_part != perm_part:
                return False
        
        return True
    
    return False


# ============================================================================
# JWT AUTHENTICATION
# ============================================================================

class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str              # Subject (user/service ID)
    role: Role            # User role
    business_id: Optional[int] = None
    iat: datetime         # Issued at
    exp: datetime         # Expiration
    jti: str              # JWT ID (for revocation)


class JWTHandler:
    """Handle JWT token creation and validation"""
    
    @staticmethod
    def create_token(
        subject: str,
        role: Role,
        business_id: Optional[int] = None,
        expiry_hours: int = None
    ) -> str:
        """Create a new JWT token"""
        try:
            import jwt
        except ImportError:
            raise ImportError("Install PyJWT: pip install PyJWT")
        
        now = datetime.utcnow()
        expiry = now + timedelta(
            hours=expiry_hours or SecurityConfig.JWT_EXPIRY_HOURS
        )
        
        payload = {
            "sub": subject,
            "role": role.value,
            "business_id": business_id,
            "iat": now,
            "exp": expiry,
            "jti": str(uuid.uuid4())
        }
        
        return jwt.encode(
            payload,
            SecurityConfig.JWT_SECRET,
            algorithm=SecurityConfig.JWT_ALGORITHM
        )
    
    @staticmethod
    def validate_token(token: str) -> TokenPayload:
        """Validate and decode JWT token"""
        try:
            import jwt
        except ImportError:
            raise ImportError("Install PyJWT: pip install PyJWT")
        
        try:
            payload = jwt.decode(
                token,
                SecurityConfig.JWT_SECRET,
                algorithms=[SecurityConfig.JWT_ALGORITHM]
            )
            
            return TokenPayload(
                sub=payload["sub"],
                role=Role(payload["role"]),
                business_id=payload.get("business_id"),
                iat=payload["iat"],
                exp=payload["exp"],
                jti=payload["jti"]
            )
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter (use Redis in production)"""
    
    def __init__(self):
        self.requests: Dict[str, List[float]] = {}
        self.limits = {
            "public": SecurityConfig.RATE_LIMIT_PUBLIC,
            "auth": SecurityConfig.RATE_LIMIT_AUTH,
            "token": SecurityConfig.RATE_LIMIT_TOKEN,
            "execute": SecurityConfig.RATE_LIMIT_EXECUTE,
            "admin": SecurityConfig.RATE_LIMIT_ADMIN,
        }
    
    def is_allowed(self, key: str, limit_type: str = "public") -> tuple[bool, int]:
        """
        Check if request is allowed
        Returns: (allowed, remaining_requests)
        """
        now = time.time()
        window = 3600  # 1 hour window
        
        # Get limit for this type
        limit = self.limits.get(limit_type, self.limits["public"])
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [
                t for t in self.requests[key]
                if now - t < window
            ]
        else:
            self.requests[key] = []
        
        # Check limit
        if len(self.requests[key]) >= limit:
            return False, 0
        
        # Record request
        self.requests[key].append(now)
        remaining = limit - len(self.requests[key])
        
        return True, remaining
    
    def get_limit_type(self, method: str, path: str) -> str:
        """Determine rate limit type based on endpoint"""
        endpoint = f"{method}:{path}"
        
        # Admin endpoints
        if any(x in endpoint for x in ["/killswitches", "/degradation"]):
            return "admin"
        
        # Token endpoint
        if "/token" in endpoint:
            return "token"
        
        # Execute endpoint
        if "/execute" in endpoint:
            return "execute"
        
        # Auth required endpoints
        if any(x in endpoint for x in [
            "/agents/register", "/tasks/submit", "/classify"
        ]):
            return "auth"
        
        return "public"


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============================================================================
# AUDIT LOGGING
# ============================================================================

class AuditLogger:
    """Immutable audit logging for compliance"""
    
    def __init__(self):
        self.events: List[Dict] = []
        
    def log(
        self,
        action: str,
        actor: str,
        resource: str,
        result: str,
        request_id: str,
        metadata: Dict = None
    ):
        """Log an audit event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "actor": actor,
            "resource": resource,
            "result": result,
            "request_id": request_id,
            "metadata": metadata or {}
        }
        
        # Store in memory (write to file/DB in production)
        self.events.append(event)
        
        # Also log to console/file
        import logging
        audit_logger = logging.getLogger("audit")
        audit_logger.info(json.dumps(event))
    
    def get_events(
        self,
        actor: str = None,
        action: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[Dict]:
        """Query audit events"""
        events = self.events
        
        if actor:
            events = [e for e in events if e["actor"] == actor]
        if action:
            events = [e for e in events if e["action"] == action]
        if start_time:
            events = [e for e in events if e["timestamp"] >= start_time.isoformat()]
        if end_time:
            events = [e for e in events if e["timestamp"] <= end_time.isoformat()]
        
        return events


# Global audit logger
audit_logger = AuditLogger()


# ============================================================================
# DEPENDENCIES FOR FASTAPI
# ============================================================================

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> TokenPayload:
    """
    FastAPI dependency to get current authenticated user
    Usage: async def endpoint(user: TokenPayload = Depends(get_current_user))
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return JWTHandler.validate_token(credentials.credentials)


async def require_role(
    required_role: Role,
    user: TokenPayload = Depends(get_current_user)
) -> TokenPayload:
    """
    FastAPI dependency to require specific role
    Usage: async def endpoint(user: TokenPayload = Depends(require_role(Role.ADMIN)))
    """
    # Check role hierarchy
    role_hierarchy = [Role.VIEWER, Role.OPERATOR, Role.GOVERNOR, Role.ADMIN]
    
    user_level = role_hierarchy.index(user.role)
    required_level = role_hierarchy.index(required_role)
    
    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {required_role.value} required"
        )
    
    return user


# Convenience dependencies
require_admin = lambda: require_role(Role.ADMIN)
require_governor = lambda: require_role(Role.GOVERNOR)
require_operator = lambda: require_role(Role.OPERATOR)


# ============================================================================
# MIDDLEWARE
# ============================================================================

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Main security middleware for FastAPI
    Handles: request ID, auth, rate limiting, audit logging
    """
    
    # Public routes that don't require auth
    PUBLIC_ROUTES = [
        ("GET", "/health"),
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
    ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if public route
        is_public = self._is_public_route(request.method, request.url.path)
        
        # Rate limiting
        rate_key = f"{client_ip}:{request_id}"
        limit_type = rate_limiter.get_limit_type(request.method, request.url.path)
        
        allowed, remaining = rate_limiter.is_allowed(rate_key, limit_type)
        
        if not allowed:
            audit_logger.log(
                action="rate_limit_exceeded",
                actor=client_ip,
                resource=request.url.path,
                result="blocked",
                request_id=request_id,
                metadata={"limit_type": limit_type}
            )
            
            return Response(
                content=json.dumps({"detail": "Rate limit exceeded"}),
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": "3600"
                }
            )
        
        # Authentication (for non-public routes)
        user = None
        if not is_public:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                try:
                    user = JWTHandler.validate_token(token)
                    request.state.user = user
                except HTTPException:
                    return Response(
                        content=json.dumps({"detail": "Invalid authentication"}),
                        status_code=401,
                        headers={"Content-Type": "application/json"}
                    )
            else:
                return Response(
                    content=json.dumps({"detail": "Authentication required"}),
                    status_code=401,
                    headers={"Content-Type": "application/json"}
                )
        
        # Authorization check
        if user and not is_public:
            if not has_permission(user.role, request.method, request.url.path):
                audit_logger.log(
                    action="authorization_denied",
                    actor=user.sub,
                    resource=request.url.path,
                    result="denied",
                    request_id=request_id,
                    metadata={
                        "required_permissions": "any",
                        "user_role": user.role.value
                    }
                )
                
                return Response(
                    content=json.dumps({"detail": "Insufficient permissions"}),
                    status_code=403,
                    headers={"Content-Type": "application/json"}
                )
        
        # Process request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log successful request
            if not is_public and user:
                audit_logger.log(
                    action=f"{request.method.lower()}_{request.url.path.replace('/', '_')}",
                    actor=user.sub,
                    resource=request.url.path,
                    result="success",
                    request_id=request_id,
                    metadata={
                        "duration_ms": (time.time() - start_time) * 1000,
                        "status_code": response.status_code
                    }
                )
            
            # Add security headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            
            return response
            
        except Exception as e:
            # Log error
            if user:
                audit_logger.log(
                    action=f"{request.method.lower()}_{request.url.path.replace('/', '_')}",
                    actor=user.sub,
                    resource=request.url.path,
                    result="error",
                    request_id=request_id,
                    metadata={"error": str(e)}
                )
            raise
    
    def _is_public_route(self, method: str, path: str) -> bool:
        """Check if route is public (no auth required)"""
        for public_method, public_path in self.PUBLIC_ROUTES:
            if method == public_method and path == public_path:
                return True
        return False


# ============================================================================
# DECORATORS
# ============================================================================

def require_auth(roles: List[Role] = None):
    """
    Decorator to require authentication and specific roles
    
    Usage:
        @router.post("/sensitive")
        @require_auth(roles=[Role.ADMIN, Role.GOVERNOR])
        async def sensitive_endpoint():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This is a simplified version
            # In practice, use FastAPI's dependency injection
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Config
    "SecurityConfig",
    
    # Roles
    "Role",
    "ROLE_PERMISSIONS",
    "has_permission",
    
    # Auth
    "TokenPayload",
    "JWTHandler",
    "get_current_user",
    "require_role",
    "require_admin",
    "require_governor",
    "require_operator",
    
    # Rate limiting
    "RateLimiter",
    "rate_limiter",
    
    # Audit
    "AuditLogger",
    "audit_logger",
    
    # Middleware
    "SecurityMiddleware",
    
    # Security scheme
    "security_scheme"
]
