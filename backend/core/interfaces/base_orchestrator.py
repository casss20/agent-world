"""Week 7: BaseOrchestrator interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseOrchestrator(ABC):
    """Abstract orchestrator provider."""

    @abstractmethod
    async def decompose(self, task: str, context: Dict = None) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def spawn(self, subtasks: List[Dict], framework: str = "native") -> str:
        ...

    @abstractmethod
    async def monitor(self, execution_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def aggregate(self, execution_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def cancel(self, execution_id: str) -> bool:
        ...
