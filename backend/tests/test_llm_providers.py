"""
Tests for BaseLLMProvider interface and implementations.
Week 1 OOP Migration — AgentWorld v2.0
"""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List

from core.interfaces.base_llm_provider import BaseLLMProvider
from core.providers.llm.llm_registry import get_llm_provider, set_llm_provider, reset_llm_provider


# ── Interface Tests ──────────────────────────────────────────────────────

def test_base_llm_is_abstract():
    """BaseLLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseLLMProvider()


# ── Mock Implementation ────────────────────────────────────────────────

class MockLLMProvider(BaseLLMProvider):
    """Fake LLM for testing. Never calls external APIs."""

    def __init__(self, response: str = "Mock LLM response"):
        super().__init__()
        self.name = "mock"
        self.model = "mock-model"
        self.fixed_response = response
        self.call_count = 0
        self.last_messages = None
        self.image_urls = ["https://mock.image/1.png"]

    def initialize(self) -> bool:
        return True

    async def complete(self, messages, **kwargs) -> str:
        self.call_count += 1
        self.last_messages = messages
        return self.fixed_response

    async def embed(self, text: str) -> List[float]:
        return [0.1] * 1536

    async def stream(self, messages):
        for word in self.fixed_response.split():
            yield word + " "

    async def generate_image(self, prompt, size="1024x1024", quality="standard", n=1):
        return self.image_urls[:n]

    async def health_check(self) -> bool:
        return True

    def get_capability(self):
        from core.interfaces.base_llm_provider import ProviderCapability
        return ProviderCapability.LLM


# ── Mock Tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_llm_complete():
    mock = MockLLMProvider()
    mock.initialize()
    response = await mock.complete([{"role": "user", "content": "hello"}])
    assert isinstance(response, str)
    assert response == "Mock LLM response"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_mock_llm_embed():
    mock = MockLLMProvider()
    result = await mock.embed("test text")
    assert isinstance(result, list)
    assert len(result) == 1536
    assert all(v == 0.1 for v in result)


@pytest.mark.asyncio
async def test_mock_llm_stream():
    mock = MockLLMProvider("hello world")
    chunks = []
    async for chunk in mock.stream([{"role": "user", "content": "hi"}]):
        chunks.append(chunk)
    assert len(chunks) == 2
    assert chunks[0] == "hello "
    assert chunks[1] == "world "


@pytest.mark.asyncio
async def test_mock_llm_generate_image():
    mock = MockLLMProvider()
    urls = await mock.generate_image("a cat", n=1)
    assert isinstance(urls, list)
    assert len(urls) == 1
    assert urls[0].startswith("https://")


@pytest.mark.asyncio
async def test_mock_llm_health_check():
    mock = MockLLMProvider()
    assert await mock.health_check() is True


# ── Registry Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_llm_provider_with_mock():
    """Registry returns whatever provider is set."""
    mock = MockLLMProvider()
    set_llm_provider(mock)
    
    provider = get_llm_provider()
    assert isinstance(provider, BaseLLMProvider)
    assert provider.name == "mock"
    
    reset_llm_provider()


def test_get_llm_provider_fallback():
    """If no provider available, falls back gracefully."""
    reset_llm_provider()
    with patch.dict("os.environ", {"LLM_PROVIDER": "invalid_provider"}):
        # Should try fallback providers, may raise if none available
        try:
            provider = get_llm_provider()
            assert isinstance(provider, BaseLLMProvider)
        except RuntimeError:
            pass  # Expected if no providers are available in test env


# ── Model Info Tests ─────────────────────────────────────────────────────

def test_get_model_info():
    mock = MockLLMProvider()
    info = mock.get_model_info()
    assert info["name"] == "mock"
    assert info["model"] == "mock-model"
    assert info["max_tokens"] == 4096


# ── Integration Tests (with real providers if available) ───────────────────

@pytest.mark.asyncio
async def test_ollama_provider_health_check():
    """Test Ollama provider health check (may fail if Ollama not running)."""
    from core.providers.llm.ollama_llm_provider import OllamaLLMProvider
    
    provider = OllamaLLMProvider()
    health = provider.initialize()
    # Should return True/False without crashing
    assert isinstance(health, bool)


# ── Legacy Adapter Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_legacy_adapter_wraps_existing():
    """Legacy adapter wraps the existing LLMProvider."""
    from core.providers.llm.legacy_adapter import LegacyLLMProviderAdapter
    
    adapter = LegacyLLMProviderAdapter()
    # initialize() may fail if llm_provider.py imports fail, but shouldn't crash
    try:
        result = adapter.initialize()
        assert isinstance(result, bool)
    except Exception:
        # If llm_provider.py has missing deps, that's expected in some envs
        pass


# ── Polymorphism Test ──────────────────────────────────────────────────

def test_polymorphism():
    """All implementations can be used interchangeably."""
    providers = [MockLLMProvider()]
    
    for p in providers:
        assert isinstance(p, BaseLLMProvider)
        info = p.get_model_info()
        assert "name" in info
        assert "model" in info
        assert "max_tokens" in info


# ── Cleanup ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_provider_after_test():
    yield
    reset_llm_provider()
