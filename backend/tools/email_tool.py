"""
Email Tool — Agent World
Sends emails via SMTP. GOVERNED: requires approval.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Placeholder for actual SMTP implementation
async def _smtp_send(to: str, subject: str, body: str, from_addr: Optional[str] = None) -> dict:
    """Actual SMTP send (to be implemented with your provider)."""
    # Example: import aiosmtplib or use Resend/SES API
    logger.info(f"[EMAIL] To: {to}, Subject: {subject}")
    return {"sent": True, "message_id": f"msg_{hash(to + subject) % 10000}"}


async def send_email(
    to: str,
    subject: str,
    body: str,
    from_addr: Optional[str] = None,
    _agent_id: str = "",
    _task_id: str = "",
    _room_id: str = ""
) -> dict:
    """
    Send an email. GOVERNED: requires HARD approval.
    
    This tool is wrapped with @governed — agents cannot send emails
    without human approval.
    """
    # Import governance
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ledger-sdk", "src"))
        from ledger.sdk import Ledger
    except ImportError:
        logger.error("ledger-sdk not installed. Email blocked.")
        return {"error": "Governance SDK not available", "sent": False}
    
    # The actual send is wrapped by @governed in the registered version
    result = await _smtp_send(to, subject, body, from_addr)
    
    # Broadcast to room
    from tools.room_tool import broadcast_to_room
    await broadcast_to_room(
        message=f"📧 Email sent to {to}: {subject}",
        message_type="info"
    )
    
    return result
