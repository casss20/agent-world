import asyncio
from typing import Callable, Any, Dict
from infrastructure.interfaces.base_self_healing import BaseSelfHealing

class DefaultSelfHealing(BaseSelfHealing):
    def initialize(self) -> bool:
        return True

    async def retry(self, fn: Callable, max_attempts: int = 3, backoff: float = 1.0) -> Any:
        for attempt in range(max_attempts):
            try:
                return await fn()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(backoff * (2 ** attempt))

    async def circuit_break(self, fn: Callable, failure_threshold: int = 5) -> Any:
        return await fn()

    async def recover(self, failure: Dict[str, Any]) -> bool:
        return True

    def get_health(self) -> Dict[str, Any]:
        return {"status": "healthy", "failures": 0}
