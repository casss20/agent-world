"""
Base LLM Router Interface
Phase 1 — Multi-LLM Router Architecture

All router implementations must inherit this ABC.
Swappable routing strategies without touching agent code.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from core.interfaces.base_llm_provider import BaseLLMProvider


class BaseLLMRouter(ABC):
    """
    Interface for all LLM routing implementations.

    Java equivalent:
        public abstract class BaseLLMRouter {
            public abstract BaseLLMProvider route(
                String task, String agent, String phase
            );
            public abstract TaskTier classify(
                String task, String agent, String phase
            );
        }

    Implement this to swap routing strategies without
    changing any agent or harness code.
    """

    @abstractmethod
    async def classify(
        self,
        task: str,
        agent: str = "",
        phase: str = "",
    ) -> str:
        """Classify a task into a routing tier."""
        pass

    @abstractmethod
    def get(
        self,
        task: str = "",
        agent: str = "",
        phase: str = "",
        force_tier: Optional[str] = None,
        force_provider: str = "",
    ) -> BaseLLMProvider:
        """Return the correct provider for this task."""
        pass

    @abstractmethod
    def available_providers(self) -> List[str]:
        """List all configured and healthy providers."""
        pass

    @abstractmethod
    def routing_table(self) -> Dict[str, str]:
        """Return current tier → provider mapping."""
        pass

    @abstractmethod
    def reload(self) -> None:
        """Reload providers (e.g. after new key added at runtime)."""
        pass
