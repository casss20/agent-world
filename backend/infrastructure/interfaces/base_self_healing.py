"""BaseSelfHealing interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseSelfHealing(ABC):
    """Abstract self-healing provider."""

    @abstractmethod
    async def diagnose(self, symptoms: Dict[str, Any]) -> str:
        ...

    @abstractmethod
    async def heal(self, diagnosis: str) -> bool:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
