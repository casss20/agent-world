import os
from typing import List, Dict, AsyncGenerator
from core.interfaces.base_llm_provider import BaseLLMProvider


class LegacyLLMProviderAdapter(BaseLLMProvider):
    """
    Adapter that wraps the existing LLMProvider from llm_provider.py
    behind the new BaseLLMProvider interface.
    
    This is the strangler fig pattern — wrap existing code,
    don't rewrite it. The existing LLMProvider stays untouched.
    """

    def __init__(self):
        super().__init__()
        self.name = "legacy"
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        self._inner = None

    def initialize(self) -> bool:
        try:
            from llm_provider import LLMProvider, LLM_PROVIDER
            self._inner = LLMProvider()
            self.name = LLM_PROVIDER
            return True
        except ImportError:
            return False

    async def complete(self, messages, temperature=None, max_tokens=None) -> str:
        response = await self._inner.complete(
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )
        return response.content

    async def embed(self, text: str) -> List[float]:
        # Legacy provider doesn't expose embeddings directly
        # Use OpenAI embeddings as fallback
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "ollama"))
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception:
            return [0.0] * 1536

    async def stream(self, messages) -> AsyncGenerator[str, None]:
        # Legacy provider doesn't support streaming natively
        # Fall back to complete
        response = await self.complete(messages)
        for word in response.split():
            yield word + " "

    async def generate_image(self, prompt, size="1024x1024", quality="standard", n=1) -> List[str]:
        raise NotImplementedError("Legacy adapter does not support image generation")

    async def health_check(self) -> bool:
        return self._inner is not None
