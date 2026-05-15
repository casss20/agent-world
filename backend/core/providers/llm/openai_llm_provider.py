import os
from typing import List, Dict, AsyncGenerator
from core.interfaces.base_llm_provider import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):
    """Wraps existing OpenAI calls behind the BaseLLMProvider interface."""

    def __init__(self):
        super().__init__()
        self.name = "openai"
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.client = None

    def initialize(self) -> bool:
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return False
            self.client = AsyncOpenAI(api_key=api_key)
            return True
        except ImportError:
            return False

    async def complete(self, messages, temperature=None, max_tokens=None) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens
        )
        return response.choices[0].message.content

    async def embed(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    async def stream(self, messages) -> AsyncGenerator[str, None]:
        async with self.client.chat.completions.stream(
            model=self.model,
            messages=messages
        ) as stream:
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

    async def generate_image(self, prompt, size="1024x1024", quality="standard", n=1) -> List[str]:
        """Generate images using DALL-E."""
        response = await self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            n=n
        )
        return [img.url for img in response.data]

    async def health_check(self) -> bool:
        try:
            await self.client.models.retrieve(self.model)
            return True
        except Exception:
            return False
