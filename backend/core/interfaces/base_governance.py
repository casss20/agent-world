from abc import ABC, abstractmethod
from typing import Dict, List

class BaseGovernance(ABC):
    @abstractmethod
    async def approve(self, action: Dict) -> bool:
        pass
    @abstractmethod
    async def audit(self, event: Dict) -> str:
        pass
    @abstractmethod
    async def validate(self, input: Dict) -> bool:
        pass
    @abstractmethod
    async def rollback(self, action_id: str) -> bool:
        pass
    @abstractmethod
    async def get_audit_trail(self, entity_id: str) -> List[Dict]:
        pass
    @abstractmethod
    async def health_check(self) -> bool:
        pass
