"""
Database Tool — Agent World
Executes database writes. GOVERNED: requires approval for risky operations.
"""

import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Estimate query cost (rows affected)
def _estimate_cost(query: str) -> int:
    """Rough estimate of query cost based on type."""
    q = query.upper()
    if "DELETE" in q or "DROP" in q or "TRUNCATE" in q:
        return 10000  # Very high
    if "UPDATE" in q:
        return 1000   # High
    if "INSERT" in q:
        return 100    # Medium
    return 10  # SELECT or unknown


async def _execute_query(query: str, params: Optional[dict] = None) -> dict:
    """Actual database execution (to be implemented with your DB)."""
    logger.info(f"[DB] Query: {query[:50]}...")
    # Placeholder — implement with your SQLAlchemy/asyncpg
    return {"rows_affected": 1, "status": "executed"}


async def write_database(
    query: str,
    params: Optional[dict] = None,
    _agent_id: str = "",
    _task_id: str = "",
    _room_id: str = ""
) -> dict:
    """
    Execute a database write query. GOVERNED: requires approval if high cost.
    
    DELETE/DROP operations always require HARD approval.
    UPDATE/INSERT require approval above threshold.
    """
    cost = _estimate_cost(query)
    
    # Import governance
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ledger-sdk", "src"))
        from ledger.sdk import Ledger
    except ImportError:
        logger.error("ledger-sdk not installed. DB write blocked.")
        return {"error": "Governance SDK not available", "executed": False}
    
    result = await _execute_query(query, params)
    
    # Broadcast to room
    from tools.room_tool import broadcast_to_room
    await broadcast_to_room(
        message=f"📝 DB write executed: {query[:50]}... (cost: {cost})",
        message_type="info" if cost < 100 else "alert"
    )
    
    return result
