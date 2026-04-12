"""
Authentication Middleware - Ticket 3: Security Hardening
JWT token validation for API endpoints
"""

import os
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from passlib.context import CryptContext

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


class AuthMiddleware:
    """JWT Authentication middleware for FastAPI"""
    
    def __init__(self, protected_paths: list = None):
        self.protected_paths = protected_paths or [
            "/stateless/launch",
            "/stateless/cancel",
        ]
        self.public_paths = [
            "/stateless/health",
            "/metrics",
            "/docs",
            "/openapi.json",
        ]
    
    async def __call__(self, request: Request, call_next):
        """Process request authentication"""
        path = request.url.path
        
        # Skip auth for public paths
        if any(path.startswith(p) for p in self.public_paths):
            return await call_next(request)
        
        # Check for protected paths
        if any(path.startswith(p) for p in self.protected_paths):
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                raise HTTPException(401, "Missing authorization header")
            
            try:
                scheme, token = auth_header.split()
                if scheme.lower() != "bearer":
                    raise HTTPException(401, "Invalid authorization scheme")
                
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                request.state.user = payload
                
            except jwt.ExpiredSignatureError:
                raise HTTPException(401, "Token expired")
            except jwt.InvalidTokenError:
                raise HTTPException(401, "Invalid token")
        
        return await call_next(request)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token from request"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def hash_password(password: str) -> str:
    """Hash password for storage"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


class APIKeyManager:
    """Simple API key management"""
    
    def __init__(self):
        self._keys = {}  # In production, use Redis/database
    
    def create_key(self, user_id: str, name: str) -> str:
        """Create new API key"""
        import secrets
        key = f"ak_{secrets.token_urlsafe(32)}"
        self._keys[key] = {
            "user_id": user_id,
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None
        }
        return key
    
    def validate_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Validate API key"""
        if key in self._keys:
            self._keys[key]["last_used"] = datetime.now(timezone.utc).isoformat()
            return self._keys[key]
        return None


# Global API key manager
api_key_manager = APIKeyManager()
