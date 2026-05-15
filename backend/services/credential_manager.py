"""
Credential Manager — Secure API key and secrets management

Manages provider credentials (OpenAI, Runway, Slack, SendGrid, etc.)
Supports: environment variables, encrypted storage, vault integration
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CredentialRequirement:
    """Required credential for a provider."""

    name: str
    description: str
    env_var: str
    required: bool = True
    example: str = ""


class CredentialManager:
    """
    Central credential management for external providers.
    - Reads from environment variables
    - Supports encrypted storage (placeholder)
    - Validates credential presence
    - Provides secure access patterns
    """

    KNOWN_CREDENTIALS = {
        "OPENAI_API_KEY": CredentialRequirement(
            name="OPENAI_API_KEY",
            description="OpenAI API key for DALL-E / GPT",
            env_var="OPENAI_API_KEY",
            example="sk-...",
        ),
        "RUNWAY_API_KEY": CredentialRequirement(
            name="RUNWAY_API_KEY",
            description="Runway ML API key for video generation",
            env_var="RUNWAY_API_KEY",
            example="key_...",
        ),
        "SLACK_BOT_TOKEN": CredentialRequirement(
            name="SLACK_BOT_TOKEN",
            description="Slack Bot User OAuth Token",
            env_var="SLACK_BOT_TOKEN",
            example="xoxb-...",
        ),
        "SENDGRID_API_KEY": CredentialRequirement(
            name="SENDGRID_API_KEY",
            description="SendGrid API key for email",
            env_var="SENDGRID_API_KEY",
            example="SG.abc123...",
        ),
        "STRIPE_SECRET_KEY": CredentialRequirement(
            name="STRIPE_SECRET_KEY",
            description="Stripe secret key for billing",
            env_var="STRIPE_SECRET_KEY",
            example="sk_test_...",
        ),
    }

    def __init__(self):
        self._cache: Dict[str, Optional[str]] = {}

    def get(self, name: str) -> Optional[str]:
        """Get a credential value (from env or cache)."""
        if name in self._cache:
            return self._cache[name]

        value = os.environ.get(name)
        if value:
            self._cache[name] = value
        return value

    def set(self, name: str, value: str) -> None:
        """Set a credential (memory only, not persisted)."""
        self._cache[name] = value
        logger.info("Credential set in memory: %s", name)

    def has(self, name: str) -> bool:
        """Check if a credential is available."""
        return self.get(name) is not None

    def validate_provider_credentials(
        self, provider_name: str, required: List[str]
    ) -> Dict[str, Any]:
        """Validate that all required credentials for a provider are present."""
        missing = []
        present = []

        for cred_name in required:
            if self.has(cred_name):
                present.append(cred_name)
            else:
                missing.append(cred_name)

        return {
            "provider": provider_name,
            "valid": len(missing) == 0,
            "present": present,
            "missing": missing,
        }

    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all known credentials."""
        return {
            name: {
                "available": self.has(name),
                "description": req.description,
                "example": req.example,
            }
            for name, req in self.KNOWN_CREDENTIALS.items()
        }

    def get_provider_for_credential(self, credential_name: str) -> Optional[str]:
        """Get the provider name associated with a credential."""
        mapping = {
            "OPENAI_API_KEY": "dalle",
            "RUNWAY_API_KEY": "runway",
            "SLACK_BOT_TOKEN": "slack",
            "SENDGRID_API_KEY": "sendgrid",
            "STRIPE_SECRET_KEY": "stripe",
        }
        return mapping.get(credential_name)


# ── Singleton ───────────────────────────────────────────────────────────

_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
