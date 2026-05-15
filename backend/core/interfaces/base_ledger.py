"""Week 6: BaseLedger interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseLedger(ABC):
    """Abstract ledger provider."""

    @abstractmethod
    async def record(self, transaction: Dict[str, Any]) -> str:
        ...

    @abstractmethod
    async def query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def approve(self, transaction_id: str, approver_id: str) -> bool:
        ...

    @abstractmethod
    async def reject(self, transaction_id: str, reason: str) -> bool:
        ...

    @abstractmethod
    async def audit_trail(self, entity_id: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def balance(self, account_id: str) -> float:
        ...
