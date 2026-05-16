"""
Router Registry — Phase 2
Singleton registry for LLM router. Swappable strategy via env var.
"""

import os
import logging
from typing import Optional
from core.interfaces.base_llm_router import BaseLLMRouter

logger = logging.getLogger(__name__)

_active_router: Optional[BaseLLMRouter] = None


def get_router() -> BaseLLMRouter:
    """
    Returns active router. Singleton.
    Router type driven by ROUTER_STRATEGY env var.
    Swappable without touching any agent code.

    Strategies:
        rule_based -> LLMRouter (keyword + agent + phase rules)
        cost_based -> CostRouter (minimize spend at quality threshold)
    """
    global _active_router

    if _active_router:
        return _active_router

    strategy = os.getenv("ROUTER_STRATEGY", "rule_based")

    if strategy == "rule_based":
        from core.routing.llm_router import LLMRouter
        _active_router = LLMRouter()
        logger.info(f"✅ LLM Router: rule_based (LLMRouter)")
        return _active_router

    # Future: cost-based strategy
    if strategy == "cost_based":
        from core.routing.cost_router import CostRouter
        _active_router = CostRouter()
        logger.info(f"✅ LLM Router: cost_based (CostRouter)")
        return _active_router

    # Default fallback
    from core.routing.llm_router import LLMRouter
    _active_router = LLMRouter()
    logger.info(f"✅ LLM Router: {strategy} not found, using rule_based")
    return _active_router


def get_llm(task="", agent="", phase="", force_tier=None, force_provider=""):
    """Single entry point. All agents call this."""
    return get_router().get(task, agent, phase, force_tier, force_provider)


def reload_router() -> None:
    """Force router reload (e.g. after provider config changes)."""
    global _active_router
    _active_router = None
    get_router().reload()
