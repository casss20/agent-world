"""
Governance Initialization — Agent World

Wires Ledger SDK into the application with:
- Startup/shutdown hooks
- Approval queue integration
- Kill switch registration
"""

import os
import sys
import logging
from typing import Callable, Awaitable, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Add ledger-sdk to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ledger-sdk", "src"))

# Lazy imports to avoid circular deps
gov = None


def get_governance() -> Optional[Any]:
    """Get or create the Ledger governance instance."""
    global gov
    if gov is None:
        try:
            from ledger.sdk import Ledger
            
            audit_dsn = os.getenv(
                "LEDGER_AUDIT_DSN",
                "postgresql://user:pass@localhost/agentworld"
            )
            gov = Ledger(audit_dsn=audit_dsn, agent="agent-world")
            
            # Wire approval hook
            from approval_queue import approval_hook
            gov.set_approval_hook(approval_hook)
            
            logger.info("[Governance] Ledger SDK initialized")
            
        except ImportError as e:
            logger.warning(f"[Governance] ledger-sdk not installed: {e}")
            return None
    return gov


async def start_governance():
    """Initialize governance at app startup."""
    g = get_governance()
    if not g:
        logger.warning("[Governance] No governance available")
        return
    
    try:
        await g.start()
        logger.info("✅ Governance layer started")
        
        # Register kill switches for the 4 risk tools
        g.killsw.register("email_send", enabled=True)
        g.killsw.register("db_write", enabled=True)
        g.killsw.register("stripe_charge", enabled=True)
        g.killsw.register("github_action", enabled=True)
        
        # Also register general safety switches
        g.killsw.register("agent_spawn", enabled=True)
        g.killsw.register("output_publish", enabled=True)
        
        logger.info("[Governance] Kill switches registered: email, db, stripe, github, spawn, publish")
        
    except Exception as e:
        logger.error(f"[Governance] Failed to start: {e}")


async def stop_governance():
    """Shut down governance at app shutdown."""
    global gov
    if gov:
        try:
            await gov.stop()
            logger.info("✅ Governance layer stopped")
            gov = None
        except Exception as e:
            logger.error(f"[Governance] Error stopping: {e}")


def build_system_prompt(task: str, agent_name: str = "default", session_id: str = "default") -> str:
    """Build system prompt with governance constitution."""
    g = get_governance()
    if not g:
        return ""
    
    try:
        return g.build_prompt(task=task, session_id=session_id, agent=agent_name)
    except Exception as e:
        logger.error(f"[Governance] Failed to build prompt: {e}")
        return ""
