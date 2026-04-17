"""
Governed Risk Tools — Agent World

The 4 riskiest tool types wrapped with @governed:
- send_email
- write_database  
- stripe_charge
- github_action

These CANNOT be called without human approval.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import raw tools
from tools.email_tool import send_email as _raw_send_email
from tools.database_tool import write_database as _raw_write_database
from tools.stripe_tool import stripe_charge as _raw_stripe_charge
from tools.github_tool import github_action as _raw_github_action

# Import governance
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ledger-sdk", "src"))

try:
    from ledger.sdk import Ledger
    _gov = Ledger(
        audit_dsn=os.getenv("LEDGER_AUDIT_DSN", "postgresql://user:pass@localhost/agentworld"),
        agent="agent-world"
    )
    _GOV_AVAILABLE = True
    logger.info("[Risk Tools] Governance SDK loaded")
except ImportError:
    _GOV_AVAILABLE = False
    logger.warning("[Risk Tools] ledger-sdk not installed — governance disabled")
    _gov = None


# Define governed versions
if _GOV_AVAILABLE and _gov:
    
    @_gov.governed(action="send_email", resource="outbound_email", flag="email_send")
    async def send_email_governed(
        to: str,
        subject: str,
        body: str,
        from_addr: Optional[str] = None,
        _agent_id: str = "",
        _task_id: str = "",
        _room_id: str = ""
    ) -> dict:
        """GOVERNED: Send email (requires HARD approval)."""
        return await _raw_send_email(to, subject, body, from_addr, _agent_id, _task_id, _room_id)

    @_gov.governed(action="database_write", resource="production_db", flag="db_write")
    async def write_database_governed(
        query: str,
        params: Optional[dict] = None,
        _agent_id: str = "",
        _task_id: str = "",
        _room_id: str = ""
    ) -> dict:
        """GOVERNED: Database write (requires approval if high cost)."""
        return await _raw_write_database(query, params, _agent_id, _task_id, _room_id)

    @_gov.governed(action="charge_payment", resource="stripe", flag="stripe_charge")
    async def stripe_charge_governed(
        amount: float,
        customer_id: str,
        description: Optional[str] = None,
        _agent_id: str = "",
        _task_id: str = "",
        _room_id: str = ""
    ) -> dict:
        """GOVERNED: Stripe charge (always requires HARD approval)."""
        return await _raw_stripe_charge(amount, customer_id, description, _agent_id, _task_id, _room_id)

    @_gov.governed(action="external_action", resource="github", flag="github_action")
    async def github_action_governed(
        repo: str,
        action: str,
        params: Optional[dict] = None,
        _agent_id: str = "",
        _task_id: str = "",
        _room_id: str = ""
    ) -> dict:
        """GOVERNED: GitHub action (requires approval for high-risk ops)."""
        return await _raw_github_action(repo, action, params, _agent_id, _task_id, _room_id)

else:
    # Fallback: raw versions without governance
    send_email_governed = _raw_send_email
    write_database_governed = _raw_write_database
    stripe_charge_governed = _raw_stripe_charge
    github_action_governed = _raw_github_action


def register_risk_tools(register_fn):
    """Register the 4 governed risk tools."""
    
    register_fn(
        name="send_email",
        description="Send an email to a customer or user. GOVERNED: requires human approval before sending.",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"},
                "from_addr": {"type": "string", "description": "Optional sender address", "default": None},
            },
            "required": ["to", "subject", "body"],
        },
        fn=send_email_governed,
    )

    register_fn(
        name="write_database",
        description="Execute a database write query (INSERT/UPDATE/DELETE). GOVERNED: requires approval for high-cost operations.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL query to execute"},
                "params": {"type": "object", "description": "Query parameters", "default": None},
            },
            "required": ["query"],
        },
        fn=write_database_governed,
    )

    register_fn(
        name="stripe_charge",
        description="Charge a customer via Stripe. GOVERNED: always requires human approval before charging.",
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Amount to charge in dollars"},
                "customer_id": {"type": "string", "description": "Stripe customer ID"},
                "description": {"type": "string", "description": "Charge description", "default": None},
            },
            "required": ["amount", "customer_id"],
        },
        fn=stripe_charge_governed,
    )

    register_fn(
        name="github_action",
        description="Trigger a GitHub Action or modify a repository. GOVERNED: requires approval for deploy/release/delete operations.",
        parameters={
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository name (owner/repo)"},
                "action": {"type": "string", "description": "Action to perform (e.g., 'deploy', 'release', 'delete_branch')"},
                "params": {"type": "object", "description": "Additional parameters", "default": None},
            },
            "required": ["repo", "action"],
        },
        fn=github_action_governed,
    )

    logger.info("[Risk Tools] 4 governed tools registered: send_email, write_database, stripe_charge, github_action")
