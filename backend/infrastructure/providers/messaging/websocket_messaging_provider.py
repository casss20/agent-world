from typing import Dict, List, Callable
from infrastructure.interfaces.base_messaging_provider import BaseMessagingProvider

class WebSocketMessagingProvider(BaseMessagingProvider):
    def __init__(self):
        self._handlers: Dict[str, List[tuple]] = {}

    def initialize(self) -> bool:
        return True

    async def send(self, channel: str, message: Dict) -> bool:
        return True

    async def broadcast(self, channels: List[str], message: Dict) -> bool:
        return True

    async def subscribe(self, channel: str, handler: Callable) -> str:
        if channel not in self._handlers:
            self._handlers[channel] = []
        sid = f"{channel}_{len(self._handlers[channel])}"
        self._handlers[channel].append((sid, handler))
        return sid

    async def unsubscribe(self, subscription_id: str) -> bool:
        return True

    async def get_channel_members(self, channel: str) -> List[str]:
        return []

    async def health_check(self) -> bool:
        return True
