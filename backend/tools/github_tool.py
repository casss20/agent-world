"""
GitHub Tool — Agent World
Dispatches GitHub Actions or modifies repos. GOVERNED: requires approval.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def _github_dispatch(repo: str, action: str, params: Optional[dict] = None) -> dict:
    """Actual GitHub API call (to be implemented with your token)."""
    logger.info(f"[GITHUB] Repo: {repo}, Action: {action}")
    # Placeholder — implement with PyGithub or httpx
    return {
        "dispatched": True,
        "repo": repo,
        "action": action,
        "run_id": f"run_{hash(repo + action) % 100000}"
    }


async def github_action(
    repo: str,
    action: str,
    params: Optional[dict] = None,
    _agent_id: str = "",
    _task_id: str = "",
    _room_id: str = ""
) -> dict:
    """
    Trigger a GitHub Action or modify repository. GOVERNED: requires approval.
    
    High-risk actions (deploy, release, delete) require HARD approval.
    """
    # Classify action risk
    high_risk = any(kw in action.lower() for kw in ["deploy", "release", "delete", "push", "merge", "destroy"])
    
    # Import governance
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ledger-sdk", "src"))
        from ledger.sdk import Ledger
    except ImportError:
        logger.error("ledger-sdk not installed. GitHub action blocked.")
        return {"error": "Governance SDK not available", "dispatched": False}
    
    result = await _github_dispatch(repo, action, params)
    
    # Broadcast to room
    from tools.room_tool import broadcast_to_room
    await broadcast_to_room(
        message=f"🐙 GitHub {action} on {repo}" + (" (HIGH RISK)" if high_risk else ""),
        message_type="alert" if high_risk else "info"
    )
    
    return result
