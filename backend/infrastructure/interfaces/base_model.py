from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseModel(ABC):
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        pass
    @abstractmethod
    def validate(self) -> bool:
        pass
