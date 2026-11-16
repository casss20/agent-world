import logging
from typing import Optional
from infrastructure.interfaces.base_storage_provider import BaseStorageProvider

logger = logging.getLogger(__name__)

_storage_provider: Optional[BaseStorageProvider] = None


def get_storage_provider() -> BaseStorageProvider:
    """
    Dependency injection for storage.
    Returns active provider based on config.
    """
    global _storage_provider

    if _storage_provider is not None:
        return _storage_provider

    # Initialize with existing database.py session factory
    try:
        from database import AsyncSessionLocal
        from infrastructure.providers.postgresql_provider import PostgreSQLProvider
        provider = PostgreSQLProvider(session_factory=AsyncSessionLocal)
        if provider.initialize():
            _storage_provider = provider
            logger.info("✅ Storage provider: PostgreSQL (from existing database.py)")
            return provider
    except Exception as e:
        logger.warning("PostgreSQL init failed, trying SQLite: %s", e)

    # Fallback to SQLite
    try:
        from infrastructure.providers.sqlite_provider import SQLiteProvider
        provider = SQLiteProvider()
        provider.initialize()
        _storage_provider = provider
        logger.info("✅ Storage provider: SQLite (fallback)")
        return provider
    except Exception as e:
        logger.error("Failed to initialize any storage provider: %s", e)
        # Return a mock for testing if nothing else works
        from tests.test_storage_provider import MockStorageProvider
        mock = MockStorageProvider()
        _storage_provider = mock
        logger.warning("⚠️ Storage provider: Mock (emergency fallback)")
        return mock


def set_storage_provider(provider: BaseStorageProvider) -> None:
    """Manually set the active storage provider (useful for testing)."""
    global _storage_provider
    _storage_provider = provider


def reset_storage_provider() -> None:
    """Reset the active provider."""
    global _storage_provider
    _storage_provider = None
