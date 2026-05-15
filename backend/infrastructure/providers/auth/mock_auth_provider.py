from typing import Dict, Optional
from infrastructure.interfaces.base_auth_provider import BaseAuthProvider

class MockAuthProvider(BaseAuthProvider):
    def initialize(self) -> bool:
        return True

    async def verify_token(self, token: str) -> Optional[Dict]:
        if token and token != "invalid":
            return {"user_id": "mock_user", "role": "admin"}
        return None

    async def create_token(self, user_id: str, claims: Dict = None, ttl: int = 3600) -> str:
        return f"mock_token_{user_id}"

    async def revoke_token(self, token: str) -> bool:
        return True

    async def refresh_token(self, token: str) -> Optional[str]:
        return token + "_refreshed"

    async def hash_password(self, password: str) -> str:
        return f"hash_{password}"

    async def verify_password(self, password: str, hash: str) -> bool:
        return hash == f"hash_{password}"

    async def health_check(self) -> bool:
        return True
