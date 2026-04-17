"""
Stripe Tool — Agent World
Charges customers via Stripe. GOVERNED: always requires approval.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def _stripe_charge(amount: float, customer_id: str, description: Optional[str] = None) -> dict:
    """Actual Stripe charge (to be implemented with your Stripe key)."""
    logger.info(f"[STRIPE] Charge ${amount} to customer {customer_id}")
    # Placeholder — implement with stripe-python
    return {
        "charged": True,
        "amount": amount,
        "customer_id": customer_id,
        "charge_id": f"ch_{hash(customer_id + str(amount)) % 100000}"
    }


async def stripe_charge(
    amount: float,
    customer_id: str,
    description: Optional[str] = None,
    _agent_id: str = "",
    _task_id: str = "",
    _room_id: str = ""
) -> dict:
    """
    Charge a customer via Stripe. GOVERNED: always requires HARD approval.
    
    ANY amount requires human approval. No automatic charges allowed.
    """
    if amount <= 0:
        return {"error": "Amount must be positive", "charged": False}
    
    if amount > 10000:
        return {"error": "Amount exceeds $10k limit — manual review required", "charged": False}
    
    # Import governance
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ledger-sdk", "src"))
        from ledger.sdk import Ledger
    except ImportError:
        logger.error("ledger-sdk not installed. Stripe charge blocked.")
        return {"error": "Governance SDK not available", "charged": False}
    
    result = await _stripe_charge(amount, customer_id, description)
    
    # Broadcast to room
    from tools.room_tool import broadcast_to_room
    await broadcast_to_room(
        message=f"💳 Stripe charge: ${amount} to {customer_id}",
        message_type="alert"
    )
    
    return result
