from abc import ABC, abstractmethod
from fastapi import FastAPI, APIRouter
from typing import List

class BaseRouter(ABC):
    def __init__(self):
        self.router = APIRouter()
    @abstractmethod
    def get_prefix(self) -> str:
        pass
    @abstractmethod
    def get_tags(self) -> List[str]:
        pass
    @abstractmethod
    def register_routes(self) -> None:
        pass
    def mount(self, app: FastAPI) -> None:
        self.register_routes()
        app.include_router(self.router, prefix=self.get_prefix(), tags=self.get_tags())
