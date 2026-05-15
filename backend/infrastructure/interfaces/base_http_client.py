from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseHTTPClient(ABC):
    @abstractmethod
    async def get(self, url: str, headers: Dict = None, params: Dict = None, timeout: int = 30) -> Dict:
        pass
    @abstractmethod
    async def post(self, url: str, body: Any = None, headers: Dict = None, timeout: int = 30) -> Dict:
        pass
    @abstractmethod
    async def put(self, url: str, body: Any = None, headers: Dict = None, timeout: int = 30) -> Dict:
        pass
    @abstractmethod
    async def delete(self, url: str, headers: Dict = None, timeout: int = 30) -> Dict:
        pass
    @abstractmethod
    async def health_check(self, url: str) -> bool:
        pass
