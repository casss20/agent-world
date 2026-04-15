"""
ledger_router.py — Agent World

The Ledger Router is the ONLY component with authority to route agent outputs
to platform adapters. Agents never touch platforms directly.

Routing logic:
  1. Find the right channel adapter for this output
  2. Evaluate risk and required approval level
  3. Return a RoutingDecision (can_auto_route vs held_for_approval)
  4. After human approval: execute() pushes the output to the adapter

Approval rules (constitution-grade — never bypassed):
  LISTING  → always HARD  — no listing ever publishes without human sign-off
  MESSAGE  → always HARD  — no reply ever sends without human sign-off
  ASSET    → HARD         — assets need approval before use in listings
  RESEARCH → SOFT         — informational, auto-queued for review
  TASK     → NONE         — internal Ultron orchestration, auto-proceed
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from channel_registry import ChannelAdapter, get_channel_registry
from output_schema import (
    AgentOutput,
    ApprovalLevel,
    AssetOutput,
    ListingOutput,
    MessageOutput,
    OutputType,
    ResearchOutput,
    TaskOutput,
)

logger = logging.getLogger(__name__)


# ── Routing Decision ───────────────────────────────────────────── #

class RoutingDecision:
    def __init__(
        self,
        output:            AgentOutput,
        channel:           Optional[ChannelAdapter],
        can_auto_route:    bool,
        requires_approval: bool,
        reason:            str,
        risk_level:        str = "low",   # low | medium | high
    ):
        self.output            = output
        self.channel           = channel
        self.can_auto_route    = can_auto_route
        self.requires_approval = requires_approval
        self.reason            = reason
        self.risk_level        = risk_level
        self.decided_at        = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output_id":          self.output.id,
            "output_type":        self.output.output_type,
            "agent_name":         self.output.agent_name,
            "channel":            self.channel.channel_id   if self.channel else None,
            "channel_name":       self.channel.display_name if self.channel else None,
            "can_auto_route":     self.can_auto_route,
            "requires_approval":  self.requires_approval,
            "reason":             self.reason,
            "risk_level":         self.risk_level,
            "decided_at":         self.decided_at,
        }


# ── Router ─────────────────────────────────────────────────────── #

class LedgerRouter:
    """
    Central routing authority — sits between agents and platform adapters.

    Usage:
        router   = get_ledger_router()
        decision = router.decide(output)

        if decision.requires_approval:
            # Hold in approval queue — show to human
        else:
            result = await router.execute(decision)
    """

    def __init__(self):
        self.registry = get_channel_registry()

    # ── Main entry point ──────────────────────────────── #

    def decide(self, output: AgentOutput) -> RoutingDecision:
        """
        Inspect an agent output and produce a routing decision.
        Does NOT execute anything — just evaluates.
        """
        channel = self._find_channel(output)
        requires_approval, risk_level, reason = self._evaluate_risk(output, channel)

        can_auto = (
            not requires_approval
            and channel is not None
            and channel.connected
        )

        # Stamp the output with the routing decision
        output.target_channel = channel.channel_id if channel else output.target_channel

        return RoutingDecision(
            output            = output,
            channel           = channel,
            can_auto_route    = can_auto,
            requires_approval = requires_approval,
            reason            = reason,
            risk_level        = risk_level,
        )

    # ── Channel selection ─────────────────────────────── #

    def _find_channel(self, output: AgentOutput) -> Optional[ChannelAdapter]:
        """Find the best channel for this output."""

        # Explicit target requested by agent or user
        if output.target_channel:
            adapter = self.registry.get_adapter(output.target_channel)
            if adapter and adapter.connected:
                return adapter
            logger.warning(
                f"[Router] Requested channel '{output.target_channel}' not available"
            )
            return None

        # Filter to channels that support this output type
        connected = self.registry.get_connected()
        compatible = [
            a for a in connected
            if output.output_type.value in a.supported_outputs
        ]

        if len(compatible) == 1:
            return compatible[0]

        if len(compatible) > 1:
            # Multiple options — cannot auto-select, hold for human assignment
            logger.info(
                f"[Router] {len(compatible)} channels support "
                f"'{output.output_type}' — holding for human channel selection"
            )
            return None

        return None   # No compatible channel connected

    # ── Risk evaluation ───────────────────────────────── #

    def _evaluate_risk(
        self,
        output: AgentOutput,
        channel: Optional[ChannelAdapter],
    ) -> tuple[bool, str, str]:
        """
        Returns (requires_approval, risk_level, reason).
        These rules are constitution-grade — never bypassed.
        """

        if output.output_type == OutputType.LISTING:
            return (
                True,
                "high",
                "Listings always require human approval before publishing to any platform. "
                "This prevents accidental publication and policy violations.",
            )

        if output.output_type == OutputType.MESSAGE:
            return (
                True,
                "high",
                "Customer communications always require human approval before sending. "
                "Automated replies can damage store reputation or violate platform policies.",
            )

        if output.output_type == OutputType.ASSET:
            return (
                True,
                "medium",
                "Design assets require human approval before being used in a listing. "
                "Reviewing for trademark issues, quality, and brand consistency.",
            )

        if output.output_type == OutputType.RESEARCH:
            return (
                False,
                "low",
                "Research outputs are informational. Auto-queued for review — no platform action taken.",
            )

        if output.output_type == OutputType.TASK:
            return (
                False,
                "low",
                "Task outputs are internal orchestration. Auto-proceed.",
            )

        # Unknown type — be safe
        return (
            True,
            "medium",
            f"Unknown output type '{output.output_type}' — held for manual review.",
        )

    # ── Execution (post-approval) ─────────────────────── #

    async def execute(self, decision: RoutingDecision) -> Dict[str, Any]:
        """
        Execute an approved routing decision.
        ONLY call this after human approval for HARD-approval outputs.
        """
        output  = decision.output
        channel = decision.channel

        if not channel:
            return {
                "ok":    False,
                "error": "No channel available — connect a platform in Channels settings.",
            }

        if not channel.connected:
            return {
                "ok":    False,
                "error": f"Channel '{channel.channel_id}' is configured but not connected.",
            }

        try:
            result: Dict[str, Any] = {}

            if output.output_type == OutputType.LISTING:
                result = await channel.create_draft_listing(output)

            elif output.output_type == OutputType.MESSAGE:
                sent_count = 0
                for msg in getattr(output, "messages", []):
                    if msg.draft_reply and msg.sender:
                        r = await channel.send_message(msg.sender, msg.draft_reply)
                        if r.get("ok"):
                            sent_count += 1
                result = {"ok": True, "sent_messages": sent_count}

            else:
                result = {
                    "ok":    False,
                    "error": f"No executor implemented for output type: {output.output_type}",
                }

            # Stamp routing timestamp
            output.routed_at = datetime.utcnow().isoformat()

            logger.info(
                f"[Router] {output.output_type} from '{output.agent_name}' "
                f"→ {channel.channel_id}: ok={result.get('ok')}"
            )
            return result

        except Exception as e:
            logger.error(f"[Router] Execution error: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}

    # ── Dashboard summary ─────────────────────────────── #

    def get_routing_summary(self) -> Dict[str, Any]:
        """Current routing state — used by the dashboard."""
        connected = self.registry.get_connected()
        return {
            "connected_channels": [a.to_dict() for a in connected],
            "channel_count":      len(connected),
            "can_publish":        any(
                c.channel_id != "generic" for c in connected
            ),
            "all_channels":       self.registry.list_channels(),
            "approval_rules": {
                "listing":  "HARD — always requires human approval",
                "message":  "HARD — always requires human approval",
                "asset":    "HARD — requires approval before use in listing",
                "research": "SOFT — auto-queued, no platform action",
                "task":     "NONE — internal orchestration, auto-proceed",
            },
        }


# ── Singleton ──────────────────────────────────────────────────── #

_router: Optional[LedgerRouter] = None


def get_ledger_router() -> LedgerRouter:
    global _router
    if _router is None:
        _router = LedgerRouter()
    return _router
