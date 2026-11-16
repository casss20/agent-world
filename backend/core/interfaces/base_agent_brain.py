"""Week 7: BaseAgentBrain interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseAgentBrain(ABC):
    """Abstract agent brain provider."""

    @abstractmethod
    async def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def plan(self, goal: str, constraints: List[str] = None) -> List[str]:
        ...

    @abstractmethod
    async def reflect(self, result: Dict[str, Any]) -> str:
        ...

    @abstractmethod
    async def decide(self, options: List[Dict[str, Any]]) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def remember(self, key: str, value: Any) -> None:
        ...

    @abstractmethod
    async def recall(self, key: str) -> Any:
        ...
