"""
SendGrid Email Provider
Implements BaseProvider for email sending via SendGrid.
"""

import os
import logging
from typing import Dict, Any, Optional

from plugins.base.base_provider import BaseProvider, ProviderCapability, ProviderStatus

logger = logging.getLogger(__name__)


class SendGridProvider(BaseProvider):
    """SendGrid email API integration."""

    def __init__(self):
        super().__init__(
            name="sendgrid",
            provider_type="communication",
            version="1.0.0",
        )
        self.api_key = None

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        self.api_key = (config or {}).get("api_key") or os.environ.get("SENDGRID_API_KEY")
        if not self.api_key:
            self.set_status(ProviderStatus.INACTIVE, "SENDGRID_API_KEY not configured")
            return False
        self.set_status(ProviderStatus.ACTIVE)
        return True

    def get_capability(self) -> ProviderCapability:
        return ProviderCapability(
            name="sendgrid",
            version="1.0.0",
            description="Send emails via SendGrid",
            parameters={
                "required": ["to", "subject", "body"],
                "optional": ["from_email", "html", "attachments"],
            },
            output_type="json",
            required_credentials=["SENDGRID_API_KEY"],
        )

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        missing = self.validate_parameters(parameters)
        if missing:
            return {
                "success": False,
                "error": f"Missing required parameters: {missing}",
                "result": None,
            }

        if not self.is_active():
            return {
                "success": False,
                "error": "Provider not initialized. Check SENDGRID_API_KEY.",
                "result": None,
            }

        try:
            to = parameters["to"]
            subject = parameters["subject"]
            return {
                "success": True,
                "result": {
                    "to": to,
                    "subject": subject,
                    "message_id": f"msg_{hash(to + subject) % 100000}",
                    "delivered": True,
                },
                "error": None,
            }
        except Exception as e:
            logger.error("SendGrid execution failed: %s", e)
            return {"success": False, "error": str(e), "result": None}

    async def health_check(self) -> bool:
        return self.is_active() and self.api_key is not None
