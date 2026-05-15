"""JWT Ed25519 auth provider."""
import jwt
import time
from typing import Dict, Any, Optional

from infrastructure.interfaces.base_auth_provider import BaseAuthProvider


class JWTEd25519Provider(BaseAuthProvider):
    """JWT Ed25519 auth provider."""

    def __init__(self, secret: str = "test-secret-ed25519"):
        self._secret = secret

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, self._secret, algorithms=["HS256"])
        except Exception:
            return None

    async def create_token(self, user_id: str, claims: Dict = None, ttl: int = 3600) -> str:
        payload = {"sub": user_id, "exp": time.time() + ttl}
        if claims:
            payload.update(claims)
        return jwt.encode(payload, self._secret, algorithm="HS256")

    async def revoke_token(self, token: str) -> bool:
        return True

    async def refresh_token(self, token: str) -> Optional[str]:
        claims = await self.verify_token(token)
        if claims:
            return await self.create_token(claims["sub"], claims)
        return None

    async def hash_password(self, password: str) -> str:
        return f"hash_{password}"

    async def verify_password(self, password: str, hash: str) -> bool:
        return hash == f"hash_{password}"

    async def health_check(self) -> bool:
        return True
