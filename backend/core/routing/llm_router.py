"""
LLM Router — Phase 2
Selects the right LLM provider for every task.

Usage (replaces get_llm_provider()):
    router = LLMRouter()
    llm = router.get(task="Analyze Q3 strategy", agent="ceo")
    response = await llm.complete(messages)

The router:
1. Classifies the task into a tier
2. Picks first available configured provider for that tier
3. Falls back to any available provider if preferred not configured
4. Logs every routing decision for cost attribution
"""

import logging
import os
from typing import Dict, List, Optional, Any

from core.interfaces.base_llm_provider import BaseLLMProvider
from core.interfaces.base_llm_router import BaseLLMRouter
from core.routing.routing_rules import TaskTier, RoutingRule, ROUTING_RULES, TIER_PROVIDERS

logger = logging.getLogger(__name__)


# ── Rule-Based Strategy ─────────────────────────────────────────────────

class RuleBasedStrategy:
    """Keyword + agent + phase rules. Current default."""

    def name(self) -> str:
        return "rule_based"

    def description(self) -> str:
        return "Routes tasks using keyword + agent + phase rules"

    def classify(
        self,
        task: str,
        agent: str,
        phase: str,
        available_providers: List[str],
    ) -> TaskTier:
        task_lower = task.lower()
        agent_lower = agent.lower()

        for rule in ROUTING_RULES:
            keyword_match = any(k in task_lower for k in rule.keywords)
            agent_match = (not rule.agents) or any(a in agent_lower for a in rule.agents)
            phase_match = (not rule.phases) or (not phase) or (phase in rule.phases)

            if keyword_match and agent_match and phase_match:
                return rule.tier

            # Agent + phase match without keywords also routes
            # Only if phase actually matches (not empty wildcard)
            if (rule.agents or rule.phases) and agent_match and phase_match and not rule.keywords and phase:
                return rule.tier

        return TaskTier.STANDARD


# ── LLMRouter ─────────────────────────────────────────────────────────

class LLMRouter(BaseLLMRouter):
    """Routes tasks to the optimal LLM provider."""

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._strategy = RuleBasedStrategy()
        self._load_configured_providers()

    def _load_configured_providers(self):
        """Load all providers that have API keys configured."""
        candidates = self._get_provider_classes()

        for name, cls in candidates.items():
            try:
                provider = cls()
                if provider.initialize():
                    self._providers[name] = provider
                    logger.info(f"✅ LLMRouter: {name} available")
            except Exception as e:
                logger.debug(f"⚪ LLMRouter: {name} not configured ({e})")

        if not self._providers:
            logger.warning("No LLM providers configured. Router will fail on get().")

    def _get_provider_classes(self) -> Dict[str, Any]:
        """Lazy import to avoid circular deps + startup overhead."""
        from core.providers.llm.openai_llm_provider import OpenAILLMProvider
        from core.providers.llm.anthropic_llm_provider import AnthropicLLMProvider
        from core.providers.llm.ollama_llm_provider import OllamaLLMProvider

        candidates = {
            "openai": OpenAILLMProvider,
            "anthropic": AnthropicLLMProvider,
            "ollama": OllamaLLMProvider,
        }

        # Try to import new providers (Phase 3)
        try:
            from core.providers.llm.deepseek_llm_provider import DeepSeekLLMProvider
            candidates["deepseek"] = DeepSeekLLMProvider
        except ImportError:
            pass

        try:
            from core.providers.llm.groq_llm_provider import GroqLLMProvider
            candidates["groq"] = GroqLLMProvider
        except ImportError:
            pass

        try:
            from core.providers.llm.openrouter_llm_provider import OpenRouterLLMProvider
            candidates["openrouter"] = OpenRouterLLMProvider
        except ImportError:
            pass

        return candidates

    # ── BaseLLMRouter contract ──────────────────────────────────────

    async def classify(
        self,
        task: str,
        agent: str = "",
        phase: str = "",
    ) -> str:
        tier = self._strategy.classify(task, agent, phase, self.available_providers())
        return tier.value

    def get(
        self,
        task: str = "",
        agent: str = "",
        phase: str = "",
        force_tier: Optional[str] = None,
        force_provider: str = "",
    ) -> BaseLLMProvider:
        """
        Get the right LLM provider for this task.

        Args:
            task: Task description (used for keyword routing)
            agent: Calling agent name (e.g. "ceo", "nova")
            phase: Harness phase (e.g. "plan", "execute", "verify")
            force_tier: Override routing — use specific tier
            force_provider: Override everything — use specific provider
        """
        # Hard override
        if force_provider:
            if force_provider in self._providers:
                logger.info(f"🔀 Forced provider: {force_provider}")
                return self._providers[force_provider]
            logger.warning(f"Forced provider {force_provider} not available")

        # Determine tier
        if force_tier:
            tier = TaskTier(force_tier)
        else:
            tier = self._strategy.classify(task, agent, phase, self.available_providers())

        # Get preferred provider list for this tier
        preferred = TIER_PROVIDERS.get(tier, [])

        # Find first available configured provider
        for provider_id in preferred:
            if provider_id in self._providers:
                logger.info(
                    f"🔀 Routing: agent={agent} phase={phase} "
                    f"tier={tier.value} → {provider_id}"
                )
                return self._providers[provider_id]

        # Fallback: return any available provider
        if self._providers:
            fallback = next(iter(self._providers.values()))
            fallback_name = fallback.name if hasattr(fallback, "name") else "unknown"
            logger.warning(
                f"⚠️ No preferred provider for tier {tier.value}, "
                f"falling back to {fallback_name}"
            )
            return fallback

        raise RuntimeError(
            "No LLM providers configured. "
            "Run the initialization screen to add at least one."
        )

    def available_providers(self) -> List[str]:
        return list(self._providers.keys())

    def routing_table(self) -> Dict[str, str]:
        """Return current tier → provider mapping."""
        table = {}
        for tier in TaskTier:
            preferred = TIER_PROVIDERS.get(tier, [])
            for pid in preferred:
                if pid in self._providers:
                    table[tier.value] = pid
                    break
            else:
                table[tier.value] = "none_available"
        return table

    def reload(self) -> None:
        """Reload providers (e.g. after new key added at runtime)."""
        self._providers.clear()
        self._load_configured_providers()
        logger.info("🔄 Router reloaded")

    # ── Convenience ───────────────────────────────────────────────────

    def get_for_pev(self, phase: str) -> BaseLLMProvider:
        """
        Convenience method for PEV harness.
        Plan + Verify → HEAVYWEIGHT
        Execute + Recover → STANDARD
        """
        tier = (
            TaskTier.HEAVYWEIGHT
            if phase in ["plan", "verify"]
            else TaskTier.STANDARD
        )
        return self.get(phase=phase, force_tier=tier.value)


# ── Singleton ───────────────────────────────────────────────────────────

_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def get_llm(
    task: str = "",
    agent: str = "",
    phase: str = "",
    force_tier: Optional[str] = None,
    force_provider: str = "",
) -> BaseLLMProvider:
    """
    Main entry point. Replaces get_llm_provider().

    Before: llm = get_llm_provider()
    After:  llm = get_llm(task=task, agent=agent_id, phase="execute")
    """
    return get_router().get(task, agent, phase, force_tier, force_provider)
