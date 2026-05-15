from abc import ABC, abstractmethod
from typing import Dict, List

class BaseLedger(ABC):
    @abstractmethod
    async def record(self, transaction: Dict) -> str:
        pass
    @abstractmethod
    async def query(self, filters: Dict) -> List[Dict]:
        pass
    @abstractmethod
    async def approve(self, transaction_id: str, approver_id: str) -> bool:
        pass
    @abstractmethod
    async def reject(self, transaction_id: str, reason: str) -> bool:
        pass
    @abstractmethod
    async def audit_trail(self, entity_id: str) -> List[Dict]:
        pass
    @abstractmethod
    async def balance(self, account_id: str) -> float:
        pass
