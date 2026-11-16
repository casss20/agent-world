"""Auth provider registry."""
from typing import Optional

from infrastructure.interfaces.base_auth_provider import BaseAuthProvider

_active_provider: Optional[BaseAuthProvider] = None


def get_auth_provider() -> BaseAuthProvider:
    """Get active auth provider."""
    global _active_provider
    if _active_provider is not None:
        return _active_provider
    from infrastructure.providers.auth.jwt_auth_provider import JWTAuthProvider
    _active_provider = JWTAuthProvider()
    return _active_provider


def set_auth_provider(provider: BaseAuthProvider) -> None:
    """Set active auth provider."""
    global _active_provider
    _active_provider = provider


def reset_auth_provider() -> None:
    """Reset active auth provider."""
    global _active_provider
    _active_provider = None
