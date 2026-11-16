"""
BaseProvider — Abstract Base Class for all plugin providers.

Java-style interface adapted for Python. Every provider (DALL-E, Runway,
Slack, SendGrid, etc.) inherits from this and implements the contract.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ProviderCapability:
    """Metadata describing what a provider can do."""

    name: str
    version: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    output_type: str = "text"  # text | image | video | audio | json | etc.
    required_credentials: List[str] = field(default_factory=list)
    rate_limit_per_minute: Optional[int] = None


class BaseProvider(ABC):
    """
    Abstract base class that every provider must implement.
    This is the contract — agents call BaseProvider, never a specific tool.
    """

    def __init__(
        self,
        name: str = "undefined",
        provider_type: str = "undefined",
        version: str = "1.0.0",
    ):
        self.name = name
        self.provider_type = provider_type
        self.version = version
        self.status: ProviderStatus = ProviderStatus.INACTIVE
        self.error_message: Optional[str] = None
        self.config: Dict[str, Any] = {}
        self._initialized = False

    # ── Lifecycle ────────────────────────────────────────────────────────

    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the provider with optional config dict.
        Return True if ready, False if not.
        """
        ...

    @abstractmethod
    def get_capability(self) -> ProviderCapability:
        """Return metadata about what this provider can do."""
        ...

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the provider's main function.
        Must return {"success": bool, "result": Any, "error": Optional[str]}.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Quick check if the provider is operational."""
        ...

    async def cleanup(self) -> None:
        """Cleanup resources. Override if needed."""
        pass

    # ── Status helpers ───────────────────────────────────────────────────

    def set_status(
        self, status: ProviderStatus, error_msg: Optional[str] = None
    ) -> None:
        self.status = status
        self.error_message = error_msg
        if status == ProviderStatus.ERROR:
            logger.warning("Provider %s error: %s", self.name, error_msg)

    def is_active(self) -> bool:
        return self.status == ProviderStatus.ACTIVE

    def is_healthy(self) -> bool:
        return self.status in (ProviderStatus.ACTIVE, ProviderStatus.INACTIVE)

    # ── Validation ───────────────────────────────────────────────────────

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """
        Validate that all required parameters are present.
        Returns list of missing parameter names (empty = valid).
        """
        capability = self.get_capability()
        required = set(capability.parameters.get("required", []))
        provided = set(parameters.keys())
        return list(required - provided)

    # ── Metadata ─────────────────────────────────────────────────────────

    def get_metadata(self) -> Dict[str, Any]:
        cap = self.get_capability()
        return {
            "name": self.name,
            "type": self.provider_type,
            "version": self.version,
            "status": self.status.value,
            "description": cap.description,
            "output_type": cap.output_type,
            "required_credentials": cap.required_credentials,
        }
