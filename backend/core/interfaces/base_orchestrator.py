from abc import ABC, abstractmethod
from typing import Dict, List

class BaseOrchestrator(ABC):
    @abstractmethod
    async def decompose(self, task: str, context: Dict = None) -> List[Dict]:
        pass
    @abstractmethod
    async def spawn(self, subtasks: List[Dict], framework: str = "native") -> str:
        pass
    @abstractmethod
    async def monitor(self, execution_id: str) -> Dict:
        pass
    @abstractmethod
    async def aggregate(self, execution_id: str) -> Dict:
        pass
    @abstractmethod
    async def cancel(self, execution_id: str) -> bool:
        pass
