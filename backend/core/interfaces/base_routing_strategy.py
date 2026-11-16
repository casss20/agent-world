"""
Base Routing Strategy Interface
Phase 1 — Multi-LLM Router Architecture

Swappable routing decision logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class BaseRoutingStrategy(ABC):
    """
    Interface for routing decision logic.
    Swap strategies without touching LLMRouter.
    """

    @abstractmethod
    def classify(
        self,
        task: str,
        agent: str,
        phase: str,
        available_providers: List[str],
    ) -> str:
        """Classify task into tier string."""
        pass

    @abstractmethod
    def name(self) -> str:
        """Strategy identifier."""
        pass

    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass
