"""Week 8: BaseMiddleware interface."""
from abc import ABC, abstractmethod
from typing import Any


class BaseMiddleware(ABC):
    """Abstract middleware provider."""

    @abstractmethod
    async def process_request(self, request: Any) -> Any:
        ...

    @abstractmethod
    async def process_response(self, response: Any) -> Any:
        ...
