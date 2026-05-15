"""Week 4: BaseAuthProvider interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAuthProvider(ABC):
    """Abstract auth provider for token and password management."""

    @abstractmethod
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def create_token(self, user_id: str, claims: Dict = None, ttl: int = 3600) -> str:
        ...

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        ...

    @abstractmethod
    async def refresh_token(self, token: str) -> Optional[str]:
        ...

    @abstractmethod
    async def hash_password(self, password: str) -> str:
        ...

    @abstractmethod
    async def verify_password(self, password: str, hash: str) -> bool:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
