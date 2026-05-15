"""Week 3: BaseQueueProvider interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseQueueProvider(ABC):
    """Abstract queue provider for task queuing."""

    @abstractmethod
    async def enqueue(self, task: Dict[str, Any], priority: int = 0, queue_name: str = "default") -> str:
        ...

    @abstractmethod
    async def dequeue(self, queue_name: str = "default") -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def acknowledge(self, task_id: str) -> bool:
        ...

    @abstractmethod
    async def dead_letter(self, task_id: str, reason: str) -> bool:
        ...

    @abstractmethod
    async def queue_depth(self, queue_name: str = "default") -> int:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
