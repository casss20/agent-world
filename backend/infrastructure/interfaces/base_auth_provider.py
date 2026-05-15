from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseAuthProvider(ABC):
    """
    Interface for authentication and authorization.
    """

    @abstractmethod
    async def verify_token(self, token: str) -> Optional[Dict]:
        """Verify token. Return claims dict or None if invalid."""
        pass

    @abstractmethod
    async def create_token(self, user_id: str, claims: Dict = None, ttl: int = 3600) -> str:
        """Create new token for user."""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Invalidate a token."""
        pass

    @abstractmethod
    async def refresh_token(self, token: str) -> Optional[str]:
        """Create new token from existing valid token."""
        pass

    @abstractmethod
    async def hash_password(self, password: str) -> str:
        """Hash a password for storage."""
        pass

    @abstractmethod
    async def verify_password(self, password: str, hash: str) -> bool:
        """Verify a password against its hash."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check auth service health."""
        pass
