from abc import ABC, abstractmethod
from fastapi import Request, Response
from typing import Callable

class BaseMiddleware(ABC):
    @abstractmethod
    async def process_request(self, request: Request) -> Request:
        pass
    @abstractmethod
    async def process_response(self, response: Response) -> Response:
        pass
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        request = await self.process_request(request)
        response = await call_next(request)
        response = await self.process_response(response)
        return response
