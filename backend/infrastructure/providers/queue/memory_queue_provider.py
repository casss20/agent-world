"""Memory queue provider."""
from typing import Dict, Any, Optional, List

from infrastructure.interfaces.base_queue_provider import BaseQueueProvider


class MemoryQueueProvider(BaseQueueProvider):
    """In-memory queue provider for testing and local dev."""

    def __init__(self):
        self._queues: Dict[str, List[Dict[str, Any]]] = {}
        self._dead: List[Dict[str, Any]] = []

    async def enqueue(self, task: Dict[str, Any], priority: int = 0, queue_name: str = "default") -> str:
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        task_id = f"task_{len(self._queues[queue_name])}"
        self._queues[queue_name].append({"id": task_id, **task, "priority": priority})
        self._queues[queue_name].sort(key=lambda x: x["priority"])
        return task_id

    async def dequeue(self, queue_name: str = "default") -> Optional[Dict[str, Any]]:
        if queue_name in self._queues and self._queues[queue_name]:
            return self._queues[queue_name].pop(0)
        return None

    async def acknowledge(self, task_id: str) -> bool:
        return True

    async def dead_letter(self, task_id: str, reason: str) -> bool:
        self._dead.append({"id": task_id, "reason": reason})
        return True

    async def queue_depth(self, queue_name: str = "default") -> int:
        return len(self._queues.get(queue_name, []))

    async def health_check(self) -> bool:
        return True
