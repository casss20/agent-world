"""
DeepSeek LLM Provider — Phase 3
OpenAI-compatible API wrapper.

Swap via: LLM_PROVIDER=deepseek
"""

import os
import logging
from typing import List, Optional, Any, AsyncGenerator

from core.interfaces.base_llm_provider import BaseLLMProvider, ProviderCapability

logger = logging.getLogger(__name__)


class DeepSeekLLMProvider(BaseLLMProvider):
    """
    DeepSeek implementation of BaseLLMProvider.
    OpenAI-compatible API.
    """

    def __init__(self):
        self.name = "deepseek"
        self.provider_type = "llm"
        self.version = "1.0.0"
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.client = None

    def initialize(self) -> bool:
        if not self.api_key:
            logger.debug("DeepSeek: no API key configured")
            return False
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info("✅ DeepSeek LLM initialized")
            return True
        except Exception as e:
            logger.warning(f"DeepSeek init failed: {e}")
            return False

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability.LLM

    async def complete(self, messages, **kwargs) -> str:
        if not self.client:
            raise RuntimeError("DeepSeek not initialized")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content

    async def embed(self, text: str) -> List[float]:
        raise NotImplementedError("DeepSeek embeddings not yet implemented")

    async def stream(self, messages, **kwargs) -> AsyncGenerator[str, None]:
        if not self.client:
            raise RuntimeError("DeepSeek not initialized")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
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
            logger.warning(f"DeepSeek health check failed: {e}")
            return False
