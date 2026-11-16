"""BaseMessagingProvider interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseMessagingProvider(ABC):
    """Abstract messaging provider."""

    @abstractmethod
    async def send(self, recipient: str, message: str, metadata: Dict = None) -> str:
        ...

    @abstractmethod
    async def receive(self, queue: str = "default") -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def broadcast(self, channel: str, message: str) -> int:
        ...
