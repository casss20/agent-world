"""
PluginLoader — Dynamic provider discovery and loading via importlib.

Scans plugin directories at startup, loads providers dynamically,
gracefully handles syntax errors / import failures without crashing.
"""

import asyncio
import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from plugins.base.base_provider import BaseProvider, ProviderCapability
from plugins.base.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Scans a directory tree for *_provider.py files,
    dynamically imports them, instantiates providers, and registers them.
    """

    _registry: Optional[PluginRegistry] = None

    @classmethod
    def get_registry(cls) -> PluginRegistry:
        if cls._registry is None:
            cls._registry = PluginRegistry()
        return cls._registry

    @classmethod
    def reset_registry(cls) -> None:
        cls._registry = PluginRegistry()

    # ── Core: Load all plugins ─────────────────────────────────────────

    @classmethod
    def load_all_plugins(
        cls,
        plugins_dir: Optional[Path] = None,
        config_overrides: Optional[Dict[str, Dict[str, any]]] = None,
    ) -> PluginRegistry:
        """
        Scan plugins_dir (defaults to ./plugins/providers/) and load all providers.
        Returns the populated registry.
        """
        if plugins_dir is None:
            plugins_dir = Path(__file__).parent.parent / "providers"
        else:
            plugins_dir = Path(plugins_dir)

        registry = cls.get_registry()
        config_overrides = config_overrides or {}

        if not plugins_dir.exists():
            logger.warning("Plugins directory not found: %s", plugins_dir)
            return registry

        for category_dir in sorted(plugins_dir.iterdir()):
            if not category_dir.is_dir():
                continue
            category = category_dir.name
            for provider_file in sorted(category_dir.glob("*_provider.py")):
                cls._load_file(
                    registry, category, provider_file, config_overrides
                )

        logger.info(
            "PluginLoader finished: %d loaded, %d failed",
            len(registry._providers),
            len(registry._failed),
        )
        return registry

    # ── Single-file loader ────────────────────────────────────────────

    @classmethod
    def _load_file(
        cls,
        registry: PluginRegistry,
        category: str,
        file_path: Path,
        config_overrides: Dict[str, Dict[str, any]],
    ) -> None:
        """Load a single *_provider.py file."""
        module_name = f"agentworld_provider_{category}_{file_path.stem}"
        provider_name = file_path.stem.replace("_provider", "")
        full_name = f"{category}/{provider_name}"

        try:
            # Dynamic import
            spec = importlib.util.spec_from_file_location(
                module_name, file_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot create spec for {file_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find BaseProvider subclass
            provider_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseProvider)
                    and attr is not BaseProvider
                ):
                    provider_class = attr
                    break

            if provider_class is None:
                raise ValueError(f"No BaseProvider subclass found in {file_path}")

            # Instantiate
            provider = provider_class()

            # Inject config if available
            config = config_overrides.get(full_name) or config_overrides.get(
                provider_name
            )
            initialized = provider.initialize(config)

            if not initialized:
                raise RuntimeError(f"Provider {full_name} initialization returned False")

            # Register
            capability = provider.get_capability()
            registry.register(full_name, provider, capability)

        except SyntaxError as e:
            registry.mark_failed(full_name, f"SyntaxError: {e}")
        except ImportError as e:
            registry.mark_failed(full_name, f"ImportError: {e}")
        except Exception as e:
            registry.mark_failed(full_name, f"{type(e).__name__}: {e}")

    # ── Convenience helpers ───────────────────────────────────────────

    @classmethod
    def get_provider(cls, name: str) -> BaseProvider:
        return cls.get_registry().get_provider(name)

    @classmethod
    def get_providers_by_type(cls, provider_type: str) -> List[BaseProvider]:
        return cls.get_registry().get_providers_by_type(provider_type)

    @classmethod
    def get_status(cls) -> Dict[str, any]:
        return cls.get_registry().get_status()
