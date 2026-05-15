from abc import ABC, abstractmethod
from typing import Callable, Any, Dict

class BaseSelfHealing(ABC):
    @abstractmethod
    async def retry(self, fn: Callable, max_attempts: int = 3, backoff: float = 1.0) -> Any:
        pass
    @abstractmethod
    async def circuit_break(self, fn: Callable, failure_threshold: int = 5) -> Any:
        pass
    @abstractmethod
    async def recover(self, failure: Dict[str, Any]) -> bool:
        pass
    @abstractmethod
    def get_health(self) -> Dict[str, Any]:
        pass
