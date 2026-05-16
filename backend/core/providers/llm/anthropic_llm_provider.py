import os
from typing import List, Dict, AsyncGenerator
from core.interfaces.base_llm_provider import BaseLLMProvider, ProviderCapability


class AnthropicLLMProvider(BaseLLMProvider):
    """Wraps Anthropic Claude behind BaseLLMProvider interface."""

    def __init__(self):
        super().__init__()
        self.name = "anthropic"
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        self.client = None

    def initialize(self) -> bool:
        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return False
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
            return True
        except ImportError:
            return False

    async def complete(self, messages, temperature=None, max_tokens=None) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]

        response = await self.client.messages.create(
            model=self.model,
            system=system,
            messages=user_messages,
            max_tokens=max_tokens or self.max_tokens
        )
        return response.content[0].text

    async def embed(self, text: str) -> List[float]:
        raise NotImplementedError("Anthropic does not provide embeddings")

    async def stream(self, messages) -> AsyncGenerator[str, None]:
        async with self.client.messages.stream(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def health_check(self) -> bool:
        try:
            await self.client.models.retrieve(self.model)
            return True
        except Exception:
            return False

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability.LLM
