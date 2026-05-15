import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Optional
from infrastructure.interfaces.base_auth_provider import BaseAuthProvider

class JWTAuthProvider(BaseAuthProvider):
    def __init__(self):
        self.secret = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
        self.algorithm = "HS256"

    def initialize(self) -> bool:
        return True

    async def verify_token(self, token: str) -> Optional[Dict]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except Exception:
            return None

    async def create_token(self, user_id: str, claims: Dict = None, ttl: int = 3600) -> str:
        payload = {"sub": user_id, "exp": datetime.utcnow() + timedelta(seconds=ttl)}
        if claims:
            payload.update(claims)
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    async def revoke_token(self, token: str) -> bool:
        return True

    async def refresh_token(self, token: str) -> Optional[str]:
        payload = await self.verify_token(token)
        if payload:
            user_id = payload.get("sub")
            return await self.create_token(user_id)
        return None

    async def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    async def verify_password(self, password: str, hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), hash.encode())

    async def health_check(self) -> bool:
        return True
