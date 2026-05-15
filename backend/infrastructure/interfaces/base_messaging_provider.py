from abc import ABC, abstractmethod
from typing import Dict, List, Callable

class BaseMessagingProvider(ABC):
    @abstractmethod
    async def send(self, channel: str, message: Dict) -> bool:
        pass
    @abstractmethod
    async def broadcast(self, channels: List[str], message: Dict) -> bool:
        pass
    @abstractmethod
    async def subscribe(self, channel: str, handler: Callable) -> str:
        pass
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        pass
    @abstractmethod
    async def get_channel_members(self, channel: str) -> List[str]:
        pass
    @abstractmethod
    async def health_check(self) -> bool:
        pass
