"""Week 9: BaseModel interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseModel(ABC):
    """Abstract base model for serialization."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        ...

    @abstractmethod
    def validate(self) -> bool:
        ...
