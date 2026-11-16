import os
import logging
from typing import Optional

from infrastructure.interfaces.base_storage_provider import BaseStorageProvider

logger = logging.getLogger(__name__)

_active_provider: Optional[BaseStorageProvider] = None


def get_storage_provider() -> BaseStorageProvider:
    """
    Dependency injection for storage.
    Returns active provider based on config.
    Callers never import a specific DB directly.
    """
    global _active_provider

    if _active_provider is not None:
        return _active_provider

    database_url = os.getenv("DATABASE_URL", "")
    provider_name = os.getenv("STORAGE_PROVIDER", "auto")

    # Auto-detect from DATABASE_URL
    if provider_name == "auto":
        if database_url.startswith("sqlite"):
            provider_name = "sqlite"
        else:
            provider_name = "postgresql"

    providers = {
        "postgresql": "infrastructure.providers.storage.postgresql_provider.PostgreSQLProvider",
        "postgres": "infrastructure.providers.storage.postgresql_provider.PostgreSQLProvider",
        "sqlite": "infrastructure.providers.storage.sqlite_provider.SQLiteProvider",
        "mock": "infrastructure.providers.storage.mock_storage_provider.MockStorageProvider",
    }

    for name in [provider_name, "sqlite", "mock"]:
        if name not in providers:
            continue
        try:
            module_path, class_name = providers[name].rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            provider = cls()
            if name == "mock":
                _active_provider = provider
                logger.info("✅ Storage provider active: %s", name)
                return provider
            # Defer async health check — just instantiate and assume OK for now
            _active_provider = provider
            logger.info("✅ Storage provider active: %s", name)
            return provider
        except Exception as e:
            logger.warning("⚠️ Storage provider %s error: %s", name, e)

    # Fallback to mock (never fails)
    from infrastructure.providers.storage.mock_storage_provider import MockStorageProvider
    provider = MockStorageProvider()
    _active_provider = provider
    logger.info("✅ Storage provider active: mock (fallback)")
    return provider


def set_storage_provider(provider: BaseStorageProvider) -> None:
    """Manually set the active storage provider (useful for testing)."""
    global _active_provider
    _active_provider = provider


def reset_storage_provider() -> None:
    """Reset the active provider (forces re-initialization on next call)."""
    global _active_provider
    _active_provider = None
