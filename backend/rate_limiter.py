"""
Rate Limiter - Ticket 3: Security Hardening
Token bucket rate limiting per user/IP
"""

import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
from fastapi import Request, HTTPException
import asyncio


class TokenBucket:
    """Token bucket for rate limiting"""
    
    def __init__(self, rate: int, capacity: int):
        """
        Args:
            rate: Tokens added per second
            capacity: Maximum bucket size
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            # Check if we can consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time until tokens available"""
        async with self._lock:
            if self.tokens >= tokens:
                return 0.0
            needed = tokens - self.tokens
            return needed / self.rate


class RateLimiter:
    """Rate limiter with per-user and per-IP buckets"""
    
    def __init__(self):
        # Rate limits: (requests per second, burst capacity)
        self.limits = {
            "default": (10, 20),      # 10/sec, burst 20
            "authenticated": (50, 100), # 50/sec, burst 100
            "health": (100, 200),     # 100/sec for health checks
        }
        
        self.buckets: Dict[str, TokenBucket] = {}
        self.blocked_ips: Dict[str, float] = {}  # IP -> unblock time
        self._cleanup_task = None
    
    def _get_bucket_key(self, request: Request, user_id: Optional[str] = None) -> str:
        """Generate bucket key from request"""
        if user_id:
            return f"user:{user_id}"
        
        # Use X-Forwarded-For if behind proxy, else direct IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    def _get_limit(self, request: Request, user_id: Optional[str] = None) -> Tuple[int, int]:
        """Get rate limit for request"""
        path = request.url.path
        
        # Health checks get higher limits
        if path in ["/stateless/health", "/health", "/metrics"]:
            return self.limits["health"]
        
        # Authenticated users get higher limits
        if user_id:
            return self.limits["authenticated"]
        
        return self.limits["default"]
    
    def _check_blocked(self, key: str) -> bool:
        """Check if key is currently blocked"""
        if key in self.blocked_ips:
            if time.time() < self.blocked_ips[key]:
                return True
            # Unblock if time expired
            del self.blocked_ips[key]
        return False
    
    async def check_rate_limit(self, request: Request, user_id: Optional[str] = None):
        """Check and enforce rate limit for request"""
        key = self._get_bucket_key(request, user_id)
        
        # Check if blocked
        if self._check_blocked(key):
            raise HTTPException(
                429,
                "Rate limit exceeded - temporarily blocked",
                headers={"Retry-After": str(int(self.blocked_ips[key] - time.time()))}
            )
        
        # Get or create bucket
        if key not in self.buckets:
            rate, capacity = self._get_limit(request, user_id)
            self.buckets[key] = TokenBucket(rate, capacity)
        
        bucket = self.buckets[key]
        
        # Try to consume token
        if not await bucket.consume():
            # Block for 60 seconds after exceeding limit
            self.blocked_ips[key] = time.time() + 60
            raise HTTPException(
                429,
                "Rate limit exceeded",
                headers={"Retry-After": "60"}
            )
    
    async def cleanup_old_buckets(self):
        """Remove old buckets to prevent memory leak"""
        while True:
            await asyncio.sleep(3600)  # Run every hour
            
            now = time.time()
            to_remove = []
            
            for key, bucket in self.buckets.items():
                # Remove if idle for 1 hour
                if now - bucket.last_update > 3600:
                    to_remove.append(key)
            
            for key in to_remove:
                del self.buckets[key]
            
            # Clean up blocked IPs
            expired_blocks = [
                ip for ip, unblock_time in self.blocked_ips.items()
                if now > unblock_time
            ]
            for ip in expired_blocks:
                del self.blocked_ips[ip]


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, limiter: RateLimiter):
        self.app = app
        self.limiter = limiter
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Get user from auth if available
        user_id = None
        if hasattr(request.state, "user"):
            user_id = request.state.user.get("sub")
        
        # Check rate limit
        await self.limiter.check_rate_limit(request, user_id)
        
        await self.app(scope, receive, send)


# Global rate limiter instance
rate_limiter = RateLimiter()
