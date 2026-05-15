from abc import ABC, abstractmethod
from typing import Optional

class BaseFileProvider(ABC):
    @abstractmethod
    async def upload(self, file: bytes, path: str, mime_type: str = None) -> str:
        pass
    @abstractmethod
    async def download(self, path: str) -> bytes:
        pass
    @abstractmethod
    async def delete(self, path: str) -> bool:
        pass
    @abstractmethod
    async def get_url(self, path: str, expiry: int = None) -> str:
        pass
    @abstractmethod
    async def exists(self, path: str) -> bool:
        pass
    @abstractmethod
    async def health_check(self) -> bool:
        pass
