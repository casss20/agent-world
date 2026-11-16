"""
Cost Router — Stub
Future implementation: minimize spend at quality threshold.
"""

import logging
from typing import Dict, List, Optional
from core.interfaces.base_llm_router import BaseLLMRouter
from core.interfaces.base_llm_provider import BaseLLMProvider
from core.routing.routing_rules import TaskTier

logger = logging.getLogger(__name__)


class CostRouter(BaseLLMRouter):
    """
    Cost-optimized router (stub — full implementation in future).
    Routes to cheapest provider that meets quality threshold.
    """

    def __init__(self):
        self._providers = {}
        logger.warning("CostRouter is a stub — not yet implemented")

    async def classify(self, task: str, agent: str = "", phase: str = "") -> str:
        return TaskTier.STANDARD.value

    def get(
        self,
        task: str = "",
        agent: str = "",
        phase: str = "",
        force_tier: Optional[str] = None,
        force_provider: str = "",
    ) -> BaseLLMProvider:
        # Stub: delegate to first available
        if self._providers:
            return next(iter(self._providers.values()))
        raise RuntimeError("No providers configured")

    def available_providers(self) -> List[str]:
        return list(self._providers.keys())

    def routing_table(self) -> Dict[str, str]:
        return {t.value: "stub" for t in TaskTier}

    def reload(self) -> None:
        pass
