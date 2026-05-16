from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional
from enum import Enum


class ProviderCapability(Enum):
    """Capability flags for LLM providers."""
    LLM = "llm"
    EMBEDDING = "embedding"
    IMAGE = "image"
    VISION = "vision"



class BaseLLMProvider(ABC):
    """
    Interface for all LLM providers.
    Swap providers by changing config — zero agent code changes needed.
    """

    def __init__(self):
        self.name: str = "undefined"
        self.model: str = "undefined"
        self.max_tokens: int = 4096
        self.temperature: float = 0.7

    @abstractmethod
    def initialize(self) -> bool:
        """Connect to LLM service. Return False if unavailable."""
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """Complete a conversation. Return the response text."""
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens as they arrive."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if LLM service is reachable and healthy."""
        pass

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1
    ) -> List[str]:
        """Generate images from prompt. Return list of URLs."""
        raise NotImplementedError("Image generation not supported by this provider")

    @abstractmethod
    def get_capability(self) -> ProviderCapability:
        """Return the primary capability of this provider."""
        pass

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
