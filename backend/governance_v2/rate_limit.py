"""
Governance v2 Rate Limiting
Protects against common abuse patterns
"""

from functools import wraps
from fastapi import HTTPException, Request, status
from typing import Callable, Optional
import time
from datetime import datetime, timedelta

# In-memory rate limit store (use Redis in production)
# Structure: {key: [(timestamp, count), ...]}
_rate_limit_store = {}

# Rate limit configurations
RATE_LIMITS = {
    # Public endpoints - generous limits
    "public": {"requests": 100, "window": 60},  # 100/minute
    
    # Authentication - strict to prevent brute force
    "auth": {"requests": 10, "window": 60},  # 10/minute
    
    # Agent registration - anti-spam
    "agent_register": {"requests": 5, "window": 60},  # 5/minute
    
    # Token issuance - moderate
    "token": {"requests": 20, "window": 60},  # 20/minute
    
    # Execute actions - controlled
    "execute": {"requests": 10, "window": 60},  # 10/minute
    
    # Kill switches - very strict (admin only but still protect)
    "killswitch": {"requests": 5, "window": 300},  # 5 per 5 minutes
    
    # General API - default
    "default": {"requests": 60, "window": 60},  # 60/minute
}


def get_rate_limit_key(request: Request, identifier: Optional[str] = None) -> str:
    """
    Generate rate limit key based on request
    
    Uses:
    1. Authenticated user ID if available
    2. API key if provided
    3. IP address as fallback
    """
    # Try to get user from request state (set by auth middleware)
    user_id = None
    if hasattr(request.state, 'user'):
        user = request.state.user
        if user and hasattr(user, 'sub'):
            user_id = user.sub
    
    # Use provided identifier or user_id or IP
    client_id = identifier or user_id or request.client.host if request.client else "unknown"
    
    return f"{request.method}:{request.url.path}:{client_id}"


def is_rate_limited(key: str, limit_type: str = "default") -> tuple[bool, dict]:
    """
    Check if request is rate limited
    
    Returns: (is_limited, rate_limit_info)
    """
    config = RATE_LIMITS.get(limit_type, RATE_LIMITS["default"])
    max_requests = config["requests"]
    window_seconds = config["window"]
    
    now = time.time()
    window_start = now - window_seconds
    
    # Get or create rate limit entry
    if key not in _rate_limit_store:
        _rate_limit_store[key] = []
    
    # Clean old entries outside window
    entries = _rate_limit_store[key]
    entries = [t for t in entries if t > window_start]
    _rate_limit_store[key] = entries
    
    # Check if limit exceeded
    current_count = len(entries)
    
    if current_count >= max_requests:
        # Calculate retry after
        if entries:
            oldest = min(entries)
            retry_after = int(oldest + window_seconds - now) + 1
        else:
            retry_after = window_seconds
        
        return True, {
            "limit": max_requests,
            "remaining": 0,
            "reset": int(now + retry_after),
            "retry_after": retry_after
        }
    
    # Add current request timestamp
    entries.append(now)
    _rate_limit_store[key] = entries
    
    return False, {
        "limit": max_requests,
        "remaining": max_requests - current_count - 1,
        "reset": int(now + window_seconds)
    }


def rate_limit(limit_type: str = "default"):
    """
    Rate limiting decorator for FastAPI endpoints
    
    Usage:
        @app.post("/agents/register")
        @rate_limit("agent_register")
        async def register_agent(request: Request, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args/kwargs
            request = kwargs.get('request')
            if not request and args:
                # Check first few args for Request
                for arg in args[:3]:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                # No request object - skip rate limiting
                return await func(*args, **kwargs)
            
            # Get rate limit key
            key = get_rate_limit_key(request)
            
            # Check rate limit
            is_limited, info = is_rate_limited(key, limit_type)
            
            if is_limited:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit_type": limit_type,
                        "retry_after": info["retry_after"]
                    },
                    headers={
                        "Retry-After": str(info["retry_after"]),
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset"])
                    }
                )
            
            # Store rate limit info in request state for response headers
            request.state.rate_limit = info
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# FastAPI dependency for rate limiting (alternative to decorator)
async def check_rate_limit(request: Request, limit_type: str = "default"):
    """
    FastAPI dependency for rate limiting
    
    Usage:
        @app.post("/agents/register")
        async def register_agent(
            request: Request,
            _: None = Depends(lambda r: check_rate_limit(r, "agent_register"))
        ):
            ...
    """
    key = get_rate_limit_key(request)
    is_limited, info = is_rate_limited(key, limit_type)
    
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {info['retry_after']} seconds.",
            headers={"Retry-After": str(info["retry_after"])}
        )
    
    request.state.rate_limit = info
    return info


# Middleware for global rate limiting headers
class RateLimitHeadersMiddleware:
    """
    Starlette middleware to add rate limit headers to responses
    """
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Store original send
        original_send = send
        
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                # Get rate limit info from request state if available
                # Note: This requires access to request object
                pass
            await original_send(message)
        
        await self.app(scope, receive, send_with_headers)


# Convenience decorators for common limit types
def public_rate_limit(func: Callable) -> Callable:
    """Rate limit for public endpoints"""
    return rate_limit("public")(func)

def auth_rate_limit(func: Callable) -> Callable:
    """Rate limit for authentication endpoints"""
    return rate_limit("auth")(func)

def agent_register_rate_limit(func: Callable) -> Callable:
    """Rate limit for agent registration"""
    return rate_limit("agent_register")(func)

def token_rate_limit(func: Callable) -> Callable:
    """Rate limit for token issuance"""
    return rate_limit("token")(func)

def execute_rate_limit(func: Callable) -> Callable:
    """Rate limit for execute actions"""
    return rate_limit("execute")(func)

def killswitch_rate_limit(func: Callable) -> Callable:
    """Rate limit for kill switch operations"""
    return rate_limit("killswitch")(func)


# Cleanup function (call periodically to prevent memory growth)
def cleanup_old_entries(max_age_seconds: int = 3600):
    """Remove old rate limit entries to prevent memory growth"""
    now = time.time()
    keys_to_remove = []
    
    for key, entries in _rate_limit_store.items():
        # Remove entries older than max_age
        entries = [t for t in entries if t > now - max_age_seconds]
        if entries:
            _rate_limit_store[key] = entries
        else:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del _rate_limit_store[key]
    
    return len(keys_to_remove)


# Get current rate limit status for a key
def get_rate_limit_status(key: str, limit_type: str = "default") -> dict:
    """Get current rate limit status for a key"""
    config = RATE_LIMITS.get(limit_type, RATE_LIMITS["default"])
    max_requests = config["requests"]
    window_seconds = config["window"]
    
    now = time.time()
    window_start = now - window_seconds
    
    entries = _rate_limit_store.get(key, [])
    entries = [t for t in entries if t > window_start]
    
    current_count = len(entries)
    remaining = max(0, max_requests - current_count)
    
    reset_time = now + window_seconds
    if entries:
        oldest = min(entries)
        reset_time = oldest + window_seconds
    
    return {
        "limit": max_requests,
        "remaining": remaining,
        "used": current_count,
        "reset": int(reset_time),
        "window": window_seconds
    }
