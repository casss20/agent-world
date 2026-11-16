"""Redis queue provider."""
import json
import logging
from typing import Dict, Any, Optional, List

from infrastructure.interfaces.base_queue_provider import BaseQueueProvider

logger = logging.getLogger(__name__)


class RedisQueueProvider(BaseQueueProvider):
    """Redis-backed queue provider for production use."""

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._dead: List[Dict[str, Any]] = []

    async def enqueue(self, task: Dict[str, Any], priority: int = 0, queue_name: str = "default") -> str:
        if self._redis is None:
            logger.warning("Redis not available, task dropped")
            return "dropped"
        task_id = f"task_{queue_name}_{await self._redis.incr(f'queue:{queue_name}:counter')}"
        payload = json.dumps({"id": task_id, **task, "priority": priority})
        await self._redis.zadd(f"queue:{queue_name}", {payload: priority})
        return task_id

    async def dequeue(self, queue_name: str = "default") -> Optional[Dict[str, Any]]:
        if self._redis is None:
            return None
        items = await self._redis.zrange(f"queue:{queue_name}", 0, 0)
        if items:
            await self._redis.zrem(f"queue:{queue_name}", items[0])
            return json.loads(items[0])
        return None

    async def acknowledge(self, task_id: str) -> bool:
        return True

    async def dead_letter(self, task_id: str, reason: str) -> bool:
        self._dead.append({"id": task_id, "reason": reason})
        return True

    async def queue_depth(self, queue_name: str = "default") -> int:
        if self._redis is None:
            return 0
        return await self._redis.zcard(f"queue:{queue_name}")

    async def health_check(self) -> bool:
        if self._redis is None:
            return False
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False
