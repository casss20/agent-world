"""
Tests for DeepSeek, Groq, OpenRouter Providers — Phase 5
Contract tests: all new providers satisfy BaseLLMProvider.
"""

import pytest
from core.interfaces.base_llm_provider import BaseLLMProvider
from core.providers.llm.deepseek_llm_provider import DeepSeekLLMProvider
from core.providers.llm.groq_llm_provider import GroqLLMProvider
from core.providers.llm.openrouter_llm_provider import OpenRouterLLMProvider


# ── Interface Contract Tests ─────────────────────────────────────────────

def test_deepseek_is_base_llm_provider():
    assert issubclass(DeepSeekLLMProvider, BaseLLMProvider)


def test_groq_is_base_llm_provider():
    assert issubclass(GroqLLMProvider, BaseLLMProvider)


def test_openrouter_is_base_llm_provider():
    assert issubclass(OpenRouterLLMProvider, BaseLLMProvider)


# ── Instantiation ─────────────────────────────────────────────────────────

def test_deepseek_instantiation():
    provider = DeepSeekLLMProvider()
    assert provider.name == "deepseek"
    assert provider.provider_type == "llm"


def test_groq_instantiation():
    provider = GroqLLMProvider()
    assert provider.name == "groq"
    assert provider.provider_type == "llm"


def test_openrouter_instantiation():
    provider = OpenRouterLLMProvider()
    assert provider.name == "openrouter"
    assert provider.provider_type == "llm"


# ── Initialization (without API keys) ───────────────────────────────────────

def test_deepseek_initialize_no_key():
    provider = DeepSeekLLMProvider()
    # Without DEEPSEEK_API_KEY, should return False
    result = provider.initialize()
    assert result is False


def test_groq_initialize_no_key():
    provider = GroqLLMProvider()
    result = provider.initialize()
    assert result is False


def test_openrouter_initialize_no_key():
    provider = OpenRouterLLMProvider()
    result = provider.initialize()
    assert result is False


# ── Capability ────────────────────────────────────────────────────────────

def test_deepseek_capability():
    provider = DeepSeekLLMProvider()
    cap = provider.get_capability()
    assert cap.value == "llm"


def test_groq_capability():
    provider = GroqLLMProvider()
    cap = provider.get_capability()
    assert cap.value == "llm"


def test_openrouter_capability():
    provider = OpenRouterLLMProvider()
    cap = provider.get_capability()
    assert cap.value == "llm"


# ── Health Check (uninitialized) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_deepseek_health_uninitialized():
    provider = DeepSeekLLMProvider()
    assert await provider.health_check() is False


@pytest.mark.asyncio
async def test_groq_health_uninitialized():
    provider = GroqLLMProvider()
    assert await provider.health_check() is False


@pytest.mark.asyncio
async def test_openrouter_health_uninitialized():
    provider = OpenRouterLLMProvider()
    assert await provider.health_check() is False


# ── Embed NotImplemented ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deepseek_embed_raises():
    provider = DeepSeekLLMProvider()
    with pytest.raises(NotImplementedError):
        await provider.embed("test")


@pytest.mark.asyncio
async def test_groq_embed_raises():
    provider = GroqLLMProvider()
    with pytest.raises(NotImplementedError):
        await provider.embed("test")


@pytest.mark.asyncio
async def test_openrouter_embed_raises():
    provider = OpenRouterLLMProvider()
    with pytest.raises(NotImplementedError):
        await provider.embed("test")
