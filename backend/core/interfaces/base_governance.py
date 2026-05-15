"""Week 6: BaseGovernance interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseGovernance(ABC):
    """Abstract governance provider."""

    @abstractmethod
    async def approve(self, action: Dict[str, Any]) -> bool:
        ...

    @abstractmethod
    async def audit(self, event: Dict[str, Any]) -> str:
        ...

    @abstractmethod
    async def validate(self, input: Dict[str, Any]) -> bool:
        ...

    @abstractmethod
    async def rollback(self, action_id: str) -> bool:
        ...

    @abstractmethod
    async def get_audit_trail(self, entity_id: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
