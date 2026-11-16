"""BaseScout interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseScout(ABC):
    """Abstract scout/reconnaissance provider."""

    @abstractmethod
    async def explore(self, target: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def report(self, findings: List[Dict[str, Any]]) -> str:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
