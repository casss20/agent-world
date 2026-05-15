from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseAgentBrain(ABC):
    @abstractmethod
    async def think(self, context: Dict) -> Dict:
        pass
    @abstractmethod
    async def plan(self, goal: str, constraints: List[str] = None) -> List[str]:
        pass
    @abstractmethod
    async def reflect(self, result: Dict) -> str:
        pass
    @abstractmethod
    async def decide(self, options: List[Dict]) -> Dict:
        pass
    @abstractmethod
    async def remember(self, key: str, value: Any) -> None:
        pass
    @abstractmethod
    async def recall(self, key: str) -> Any:
        pass
