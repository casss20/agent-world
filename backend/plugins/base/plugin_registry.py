"""
PluginRegistry — Service Locator for provider instances.

Singleton registry that holds all loaded providers.
Agents request providers by type or name — they never import tools directly.
"""

import logging
from typing import Any, Dict, List, Optional

from plugins.base.base_provider import BaseProvider, ProviderCapability, ProviderStatus

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for all provider plugins.
    Provides get-by-name and get-by-type lookups with graceful degradation.
    """

    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._capabilities: Dict[str, ProviderCapability] = {}
        self._by_type: Dict[str, List[str]] = {}
        self._failed: List[Dict[str, str]] = []

    # ── Registration ────────────────────────────────────────────────────

    def register(
        self,
        name: str,
        provider: BaseProvider,
        capability: Optional[ProviderCapability] = None,
    ) -> None:
        """Register a provider in the registry."""
        self._providers[name] = provider
        if capability:
            self._capabilities[name] = capability
        ptype = provider.provider_type
        if ptype not in self._by_type:
            self._by_type[ptype] = []
        if name not in self._by_type[ptype]:
            self._by_type[ptype].append(name)
        logger.info("✅ Registered provider: %s (type=%s)", name, ptype)

    def unregister(self, name: str) -> None:
        """Remove a provider from the registry."""
        provider = self._providers.pop(name, None)
        self._capabilities.pop(name, None)
        if provider:
            ptype = provider.provider_type
            if ptype in self._by_type:
                self._by_type[ptype] = [n for n in self._by_type[ptype] if n != name]
        logger.info("🗑️  Unregistered provider: %s", name)

    def mark_failed(self, name: str, error: str) -> None:
        """Record a plugin that failed to load."""
        self._failed.append({"name": name, "error": error})
        logger.warning("⚠️  Plugin failed: %s — %s", name, error)

    # ── Retrieval ───────────────────────────────────────────────────────

    def get_provider(self, name: str) -> BaseProvider:
        """Get a provider by exact name. Raises KeyError if not found."""
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' not found in registry")
        return self._providers[name]

    def get_providers_by_type(self, provider_type: str) -> List[BaseProvider]:
        """Get all active providers of a given type."""
        names = self._by_type.get(provider_type, [])
        return [
            self._providers[n]
            for n in names
            if n in self._providers and self._providers[n].is_active()
        ]

    def get_provider_names(self) -> List[str]:
        return list(self._providers.keys())

    def get_provider_types(self) -> List[str]:
        return list(self._by_type.keys())

    def get_failed_plugins(self) -> List[Dict[str, str]]:
        return list(self._failed)

    def has_provider(self, name: str) -> bool:
        return name in self._providers

    # ── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "total": len(self._providers),
            "by_type": {
                t: len([n for n in names if self._providers.get(n) and self._providers[n].is_active()])
                for t, names in self._by_type.items()
            },
            "failed": len(self._failed),
            "failed_details": self._failed,
        }

    # ── Bulk operations ─────────────────────────────────────────────────

    def health_check_all(self) -> Dict[str, bool]:
        """Run health_check on all active providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                import asyncio
                # If we're in async context, use async health_check
                # Otherwise skip — health checks are meant to be async
                results[name] = False  # Will be called async externally
            except Exception:
                results[name] = False
        return results

    async def health_check_all_async(self) -> Dict[str, bool]:
        """Async health check for all providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                healthy = await provider.health_check()
                results[name] = healthy
            except Exception as e:
                logger.warning("Health check failed for %s: %s", name, e)
                results[name] = False
        return results

    def shutdown_all(self) -> None:
        """Cleanup all providers."""
        for name, provider in list(self._providers.items()):
            try:
                provider.cleanup()
            except Exception as e:
                logger.warning("Cleanup error for %s: %s", name, e)
        self._providers.clear()
        self._capabilities.clear()
        self._by_type.clear()
        self._failed.clear()
