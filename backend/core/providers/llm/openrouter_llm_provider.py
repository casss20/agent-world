"""
OpenRouter LLM Provider — Phase 3
Access to frontier models via one key. OpenAI-compatible.

Swap via: LLM_PROVIDER=openrouter
"""

import os
import logging
from typing import List, Optional, Any, AsyncGenerator

from core.interfaces.base_llm_provider import BaseLLMProvider, ProviderCapability

logger = logging.getLogger(__name__)


class OpenRouterLLMProvider(BaseLLMProvider):
    """
    OpenRouter implementation of BaseLLMProvider.
    One key, many frontier models. OpenAI-compatible API.
    """

    def __init__(self):
        self.name = "openrouter"
        self.provider_type = "llm"
        self.version = "1.0.0"
        self.model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-70b-instruct")
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = None

    def initialize(self) -> bool:
        if not self.api_key:
            logger.debug("OpenRouter: no API key configured")
            return False
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info("✅ OpenRouter LLM initialized")
            return True
        except Exception as e:
            logger.warning(f"OpenRouter init failed: {e}")
            return False

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability.LLM

    async def complete(self, messages, **kwargs) -> str:
        if not self.client:
            raise RuntimeError("OpenRouter not initialized")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            extra_headers={"HTTP-Referer": "agentworld"},
            **kwargs,
        )
        return response.choices[0].message.content

    async def embed(self, text: str) -> List[float]:
        raise NotImplementedError("OpenRouter embeddings not yet implemented")

    async def stream(self, messages, **kwargs) -> AsyncGenerator[str, None]:
        if not self.client:
            raise RuntimeError("OpenRouter not initialized")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            extra_headers={"HTTP-Referer": "agentworld"},
            **kwargs,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def health_check(self) -> bool:
        if not self.client:
            return False
        try:
            await self.complete([{"role": "user", "content": "hi"}], max_tokens=5)
            return True
        except Exception as e:
            logger.warning(f"OpenRouter health check failed: {e}")
            return False
