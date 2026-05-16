"""
Tests for BaseLLMRouter interface contract
Phase 5 — Multi-LLM Router Architecture
"""

import pytest
from core.interfaces.base_llm_router import BaseLLMRouter
from core.routing.llm_router import LLMRouter
from tests.mocks.router_mock import RouterMock


def test_llm_router_satisfies_interface():
    """LLMRouter must implement all BaseLLMRouter methods."""
    assert issubclass(LLMRouter, BaseLLMRouter)


def test_router_mock_satisfies_interface():
    """RouterMock must implement all BaseLLMRouter methods."""
    assert issubclass(RouterMock, BaseLLMRouter)


def test_base_router_is_abstract():
    """BaseLLMRouter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseLLMRouter()
