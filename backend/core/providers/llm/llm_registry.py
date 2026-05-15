import os
import logging
from typing import Optional
from core.interfaces.base_llm_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

_active_provider: Optional[BaseLLMProvider] = None


def get_llm_provider() -> BaseLLMProvider:
    """
    Dependency injection for LLM.
    Returns active provider based on config.
    Callers never import a specific LLM directly.
    """
    global _active_provider

    if _active_provider is not None:
        return _active_provider

    provider_name = os.getenv("LLM_PROVIDER", "openai")

    providers = {
        "openai": "core.providers.llm.openai_llm_provider.OpenAILLMProvider",
        "anthropic": "core.providers.llm.anthropic_llm_provider.AnthropicLLMProvider",
        "ollama": "core.providers.llm.ollama_llm_provider.OllamaLLMProvider",
        "legacy": "core.providers.llm.legacy_adapter.LegacyLLMProviderAdapter",
    }

    for name in [provider_name, "legacy", "ollama", "openai"]:
        if name not in providers:
            continue
        try:
            module_path, class_name = providers[name].rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            provider = cls()
            if provider.initialize():
                _active_provider = provider
                logger.info("✅ LLM provider active: %s", name)
                return provider
            else:
                logger.warning("⚠️ LLM provider %s initialization failed", name)
        except Exception as e:
            logger.warning("⚠️ LLM provider %s error: %s", name, e)

    raise RuntimeError(
        "No LLM provider available. Set LLM_PROVIDER env var or install dependencies."
    )


def set_llm_provider(provider: BaseLLMProvider) -> None:
    """Manually set the active LLM provider (useful for testing)."""
    global _active_provider
    _active_provider = provider


def reset_llm_provider() -> None:
    """Reset the active provider (forces re-initialization on next call)."""
    global _active_provider
    _active_provider = None
