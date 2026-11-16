"""
security_lite.py — Agent World Lite

Minimal auth for the lite build. One optional API key via X-API-Key header.
No JWT, no jose, no RBAC tables.

Set AGENTWORLD_API_KEY env var to require a key. If unset, every request
gets a default demo user — correct for a public demo, NOT for production
with real user data.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from fastapi import Depends, Header, HTTPException


@dataclass
class TokenPayload:
    sub: str = "demo_user"
    business_id: Optional[str] = "default"
    role: str = "admin"
    scopes: List[str] = field(default_factory=list)


async def get_current_user(
    x_api_key: Optional[str] = Header(default=None),
) -> TokenPayload:
    """Validate API key if one is configured; otherwise allow demo user."""
    expected = os.getenv("AGENTWORLD_API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return TokenPayload()


def require_roles(allowed_roles: List[str]):
    """Dependency factory: require one of the given roles."""
    async def role_checker(
        user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role}' not in {allowed_roles}",
            )
        return user
    return role_checker


require_admin = require_roles(["admin"])
require_governor = require_roles(["governor", "admin"])
