"""
Router Mock — Phase 5
Test mock for LLMRouter. Returns LLMMock for every call.
Tracks what tier was requested.
"""

from typing import Dict, List, Optional
from core.interfaces.base_llm_router import BaseLLMRouter
from core.routing.routing_rules import TaskTier
from tests.mocks.llm_mock import LLMMock


class RouterMock(BaseLLMRouter):
    """
    Test mock for LLMRouter.
    Returns LLMMock for every call.
    Tracks what tier was requested.
    """

    def __init__(self):
        self._mock = LLMMock()
        self.last_tier: Optional[TaskTier] = None
        self.last_agent: Optional[str] = None
        self.last_phase: Optional[str] = None
        self.call_count = 0
        self._providers = {"mock": self._mock}

    async def classify(self, task: str, agent: str = "", phase: str = "") -> str:
        return TaskTier.STANDARD.value

    def get(
        self,
        task: str = "",
        agent: str = "",
        phase: str = "",
        force_tier: Optional[str] = None,
        force_provider: str = "",
    ):
        self.last_tier = TaskTier(force_tier) if force_tier else TaskTier.STANDARD
        self.last_agent = agent
        self.last_phase = phase
        self.call_count += 1
        return self._mock

    def available_providers(self) -> List[str]:
        return ["mock"]

    def routing_table(self) -> Dict[str, str]:
        return {t.value: "mock" for t in TaskTier}

    def reload(self) -> None:
        pass

    def assert_routed_to_tier(self, expected_tier: TaskTier) -> None:
        assert self.last_tier == expected_tier, \
            f"Expected tier {expected_tier}, got {self.last_tier}"
