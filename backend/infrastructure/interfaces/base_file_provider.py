"""BaseFileProvider interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseFileProvider(ABC):
    """Abstract file provider."""

    @abstractmethod
    async def upload(self, file_data: bytes, filename: str, metadata: Dict = None) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def download(self, file_id: str) -> Optional[bytes]:
        ...

    @abstractmethod
    async def delete(self, file_id: str) -> bool:
        ...

    @abstractmethod
    async def list_files(self, prefix: str = "") -> list:
        ...
