"""
LLM Mock — for testing
Provides a fake LLM provider that doesn't need API keys.
"""

from typing import List, Dict, Any, AsyncGenerator
from core.interfaces.base_llm_provider import BaseLLMProvider, ProviderCapability


class LLMMock(BaseLLMProvider):
    """
    Test mock LLM provider.
    Returns predictable responses without API calls.
    """

    def __init__(self):
        super().__init__()
        self.name = "mock"
        self.model = "mock-model"
        self.last_messages = None
        self.call_count = 0

    def initialize(self) -> bool:
        return True

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability.LLM

    async def complete(self, messages, temperature=None, max_tokens=None) -> str:
        self.last_messages = messages
        self.call_count += 1
        return "Mock response"

    async def embed(self, text: str) -> List[float]:
        return [0.0] * 1536

    async def stream(self, messages) -> AsyncGenerator[str, None]:
        yield "Mock"
        yield " response"

    async def generate_image(self, prompt, size="1024x1024", quality="standard", n=1) -> List[str]:
        return ["https://mock.image/url.png"]

    async def health_check(self) -> bool:
        return True
