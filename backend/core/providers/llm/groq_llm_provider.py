"""
Groq LLM Provider — Phase 3
Fast inference via Groq API. OpenAI-compatible.

Swap via: LLM_PROVIDER=groq
"""

import os
import logging
from typing import List, Optional, Any, AsyncGenerator

from core.interfaces.base_llm_provider import BaseLLMProvider, ProviderCapability

logger = logging.getLogger(__name__)


class GroqLLMProvider(BaseLLMProvider):
    """
    Groq implementation of BaseLLMProvider.
    Ultra-fast inference. OpenAI-compatible API.
    """

    def __init__(self):
        self.name = "groq"
        self.provider_type = "llm"
        self.version = "1.0.0"
        self.model = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
        self.api_key = os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = None

    def initialize(self) -> bool:
        if not self.api_key:
            logger.debug("Groq: no API key configured")
            return False
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info("✅ Groq LLM initialized")
            return True
        except Exception as e:
            logger.warning(f"Groq init failed: {e}")
            return False

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability.LLM

    async def complete(self, messages, **kwargs) -> str:
        if not self.client:
            raise RuntimeError("Groq not initialized")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content

    async def embed(self, text: str) -> List[float]:
        raise NotImplementedError("Groq embeddings not yet implemented")

    async def stream(self, messages, **kwargs) -> AsyncGenerator[str, None]:
        if not self.client:
            raise RuntimeError("Groq not initialized")
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
            logger.warning(f"Groq health check failed: {e}")
            return False
