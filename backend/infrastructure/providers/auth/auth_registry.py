import logging
from typing import Optional
from infrastructure.interfaces.base_auth_provider import BaseAuthProvider

logger = logging.getLogger(__name__)
_auth_provider: Optional[BaseAuthProvider] = None

def get_auth_provider() -> BaseAuthProvider:
    global _auth_provider
    if _auth_provider is None:
        from infrastructure.providers.auth.jwt_auth_provider import JWTAuthProvider
        _auth_provider = JWTAuthProvider()
        _auth_provider.initialize()
        logger.info("✅ Auth provider: JWT")
    return _auth_provider

def set_auth_provider(provider: BaseAuthProvider) -> None:
    global _auth_provider
    _auth_provider = provider

def reset_auth_provider() -> None:
    global _auth_provider
    _auth_provider = None
