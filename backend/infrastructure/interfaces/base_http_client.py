"""BaseHTTPClient interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseHTTPClient(ABC):
    """Abstract HTTP client provider."""

    @abstractmethod
    async def get(self, url: str, headers: Dict = None) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def post(self, url: str, data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def put(self, url: str, data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def delete(self, url: str, headers: Dict = None) -> Dict[str, Any]:
        ...
