"""Week 8: BaseRouter interface."""
from abc import ABC, abstractmethod
from typing import List


class BaseRouter(ABC):
    """Abstract router provider."""

    @abstractmethod
    def get_prefix(self) -> str:
        ...

    @abstractmethod
    def get_tags(self) -> List[str]:
        ...

    @abstractmethod
    def register_routes(self) -> None:
        ...
