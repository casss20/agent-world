"""OAuth2 auth provider."""
from typing import Dict, Any, Optional

from infrastructure.interfaces.base_auth_provider import BaseAuthProvider


class OAuth2Provider(BaseAuthProvider):
    """OAuth2 auth provider stub for testing and local dev."""

    def __init__(self, token_url: str = "http://localhost/oauth/token"):
        self._token_url = token_url
        self._tokens: Dict[str, Dict[str, Any]] = {}

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        return self._tokens.get(token)

    async def create_token(self, user_id: str, claims: Dict = None, ttl: int = 3600) -> str:
        token = f"oauth_token_{user_id}_{len(self._tokens)}"
        self._tokens[token] = {"sub": user_id, **(claims or {})}
        return token

    async def revoke_token(self, token: str) -> bool:
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    async def refresh_token(self, token: str) -> Optional[str]:
        claims = self._tokens.get(token)
        if claims:
            user_id = claims.get("sub", "")
            return await self.create_token(user_id, claims)
        return None

    async def hash_password(self, password: str) -> str:
        return f"hash_{password}"

    async def verify_password(self, password: str, hash: str) -> bool:
        return hash == f"hash_{password}"

    async def health_check(self) -> bool:
        return True
