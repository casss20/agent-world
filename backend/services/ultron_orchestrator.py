"""
Ultron Orchestrator — Executive ↔ Specialist Bridge
Phase 2 — Two-Tier Agent Unification

When an executive agent receives a message, Ultron:
1. Analyzes the message for specialist-domain keywords
2. Routes to the appropriate specialist(s)
3. Returns a structured plan (not execution — Phase 3)
4. All routing goes through governance approval if required

Pattern: Bridge / Adapter — sits between executive layer and specialist layer.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from agents.roles.role_definitions import get_role, AgentRole

logger = logging.getLogger(__name__)

# ── Feature Flag ─────────────────────────────────────────────────────────

def _harness_enabled_agents() -> List[str]:
    """Parse HARNESS_ENABLED_AGENTS env var. Empty = all executives."""
    env = os.getenv("HARNESS_ENABLED_AGENTS", "")
    if not env or env.strip() == "*":
        return ["ceo", "coo", "developer", "content_director", "crm"]
    return [a.strip().lower() for a in env.split(",") if a.strip()]


# ── Routing Table ────────────────────────────────────────────────────────

class SpecialistType(Enum):
    NOVA = "nova"           # Research/diagnosis
    PIXEL = "pixel"         # Design/creative
    FORGE = "forge"         # Listings/content
    CIPHER = "cipher"       # Communications
    MERCHANT = "merchant"   # Publishing/sales
    PROMOTER = "promoter"   # Paid ads
    GROWTH = "growth"       # Organic/SEO


# Keyword → specialist mapping (simple rule-based for Phase 2)
KEYWORD_ROUTES: Dict[str, List[SpecialistType]] = {
    # Research / Diagnosis
    "research": [SpecialistType.NOVA],
    "diagnose": [SpecialistType.NOVA],
    "benchmark": [SpecialistType.NOVA],
    "analyze": [SpecialistType.NOVA],
    "market": [SpecialistType.NOVA],
    "competitor": [SpecialistType.NOVA],
    # Design / Creative
    "design": [SpecialistType.PIXEL],
    "image": [SpecialistType.PIXEL],
    "logo": [SpecialistType.PIXEL],
    "creative": [SpecialistType.PIXEL],
    "visual": [SpecialistType.PIXEL],
    "art": [SpecialistType.PIXEL],
    "thumbnail": [SpecialistType.PIXEL],
    # Listings / Content
    "listing": [SpecialistType.FORGE],
    "product": [SpecialistType.FORGE],
    "description": [SpecialistType.FORGE],
    "title": [SpecialistType.FORGE],
    "seo": [SpecialistType.FORGE, SpecialistType.GROWTH],
    "tags": [SpecialistType.FORGE],
    "price": [SpecialistType.FORGE, SpecialistType.MERCHANT],
    # Communications
    "message": [SpecialistType.CIPHER],
    "email": [SpecialistType.CIPHER, SpecialistType.GROWTH],
    "reply": [SpecialistType.CIPHER],
    "support": [SpecialistType.CIPHER],
    "customer": [SpecialistType.CIPHER],
    "review": [SpecialistType.CIPHER],
    # Publishing / Sales
    "publish": [SpecialistType.MERCHANT],
    "etsy": [SpecialistType.MERCHANT],
    "shopify": [SpecialistType.MERCHANT],
    "amazon": [SpecialistType.MERCHANT],
    "inventory": [SpecialistType.MERCHANT],
    "sync": [SpecialistType.MERCHANT],
    "channel": [SpecialistType.MERCHANT],
    # Paid Ads
    "ad": [SpecialistType.PROMOTER],
    "campaign": [SpecialistType.PROMOTER],
    "facebook": [SpecialistType.PROMOTER],
    "google": [SpecialistType.PROMOTER],
    "tiktok": [SpecialistType.PROMOTER],
    "roas": [SpecialistType.PROMOTER],
    "spend": [SpecialistType.PROMOTER],
    "budget": [SpecialistType.PROMOTER],
    # Growth / Organic
    "content": [SpecialistType.GROWTH],
    "blog": [SpecialistType.GROWTH],
    "social": [SpecialistType.GROWTH],
    "instagram": [SpecialistType.GROWTH],
    "pinterest": [SpecialistType.GROWTH],
    "youtube": [SpecialistType.GROWTH],
    "affiliate": [SpecialistType.GROWTH],
    "influencer": [SpecialistType.GROWTH],
    "organic": [SpecialistType.GROWTH],
    "traffic": [SpecialistType.GROWTH],
    "backlink": [SpecialistType.GROWTH],
}


# ── Data Classes ─────────────────────────────────────────────────────────

@dataclass
class RoutingPlan:
    """Result of Ultron's analysis — who should work on what."""
    message: str
    detected_keywords: List[str] = field(default_factory=list)
    suggested_specialists: List[SpecialistType] = field(default_factory=list)
    confidence: float = 0.0  # 0.0–1.0
    requires_approval: bool = False
    estimated_cost: float = 0.0
    plan_description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "detected_keywords": self.detected_keywords,
            "suggested_specialists": [s.value for s in self.suggested_specialists],
            "confidence": round(self.confidence, 2),
            "requires_approval": self.requires_approval,
            "estimated_cost": self.estimated_cost,
            "plan_description": self.plan_description,
        }


@dataclass
class OrchestratorResult:
    """What Ultron returns to the executive layer."""
    action: str  # "route", "direct", "escalate"
    routing_plan: Optional[RoutingPlan] = None
    direct_response: Optional[str] = None
    escalate_to: Optional[str] = None  # executive role ID
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "routing_plan": self.routing_plan.to_dict() if self.routing_plan else None,
            "direct_response": self.direct_response,
            "escalate_to": self.escalate_to,
            "reason": self.reason,
        }


# ── Ultron Orchestrator ──────────────────────────────────────────────────

class UltronOrchestrator:
    """
    Bridge between executive agents and specialist agents.

    Phase 2: Simple keyword-based routing. Returns plans, not executions.
    Phase 3: Will implement BaseHarness for full PEV loop.
    """

    def __init__(self):
        self.enabled = True
        self.logger = logging.getLogger(self.__class__.__name__)

    # ── Public API ──────────────────────────────────────────────────────

    async def analyze_message(
        self,
        executive_role: AgentRole,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestratorResult:
        """
        Analyze an executive's incoming message and decide what to do.

        Returns:
            OrchestratorResult with action = "route" | "direct" | "escalate"
        """
        context = context or {}

        # 1. Check if this executive is harness-enabled
        if executive_role.id not in _harness_enabled_agents():
            return OrchestratorResult(
                action="direct",
                direct_response=None,
                reason=f"Harness not enabled for {executive_role.id}",
            )

        # 2. Detect specialist keywords in the message
        routing_plan = self._detect_specialists(message)

        # 3. Decide action based on detection
        if not routing_plan.suggested_specialists:
            # No specialist keywords — handle directly
            return OrchestratorResult(
                action="direct",
                direct_response=None,
                reason="No specialist keywords detected",
            )

        # 4. Check if executive should escalate instead
        escalate_target = self._should_escalate(executive_role, routing_plan)
        if escalate_target:
            return OrchestratorResult(
                action="escalate",
                escalate_to=escalate_target,
                routing_plan=routing_plan,
                reason=f"Escalating to {escalate_target} per escalation rules",
            )

        # 5. Route to specialists (default)
        routing_plan.requires_approval = self._requires_approval(routing_plan)
        routing_plan.estimated_cost = self._estimate_cost(routing_plan)
        routing_plan.plan_description = self._build_plan_description(routing_plan)

        return OrchestratorResult(
            action="route",
            routing_plan=routing_plan,
            reason=f"Routing to {len(routing_plan.suggested_specialists)} specialist(s)",
        )

    async def format_routing_response(
        self,
        result: OrchestratorResult,
        executive_role: AgentRole,
    ) -> str:
        """
        Format Ultron's routing decision into a user-facing message.

        This is what the user sees when an executive routes through Ultron.
        """
        if result.action == "direct":
            return ""

        if result.action == "escalate" and result.escalate_to:
            role = get_role(result.escalate_to)
            role_name = role.name if role else result.escalate_to
            return (
                f"📤 **Escalating to {role_name}**\n\n"
                f"This request is best handled by the {role_name}. "
                f"Transferring now..."
            )

        if result.action == "route" and result.routing_plan:
            plan = result.routing_plan
            specialists = [s.value.title() for s in plan.suggested_specialists]
            specialist_list = ", ".join(specialists)

            lines = [
                f"🤖 **Ultron Routing Plan**",
                f"",
                f"**Detected intent:** {plan.plan_description}",
                f"**Specialists:** {specialist_list}",
                f"**Confidence:** {plan.confidence:.0%}",
            ]

            if plan.requires_approval:
                lines.append(
                    f"⚠️ **Approval Required:** This plan includes actions that need human approval."
                )

            if plan.estimated_cost > 0:
                lines.append(f"**Estimated Cost:** ${plan.estimated_cost:.2f}")

            lines.extend([
                f"",
                f"---",
                f"*Phase 2 Preview: Specialists are not yet active. This shows the planned routing.*",
            ])

            return "\n".join(lines)

        return ""

    # ── Internal Methods ────────────────────────────────────────────────

    def _detect_specialists(self, message: str) -> RoutingPlan:
        """Scan message for specialist keywords."""
        message_lower = message.lower()
        detected = []
        specialists: set = set()

        for keyword, routes in KEYWORD_ROUTES.items():
            if keyword in message_lower:
                detected.append(keyword)
                specialists.update(routes)

        # Calculate confidence: more keywords = higher confidence
        confidence = min(1.0, len(detected) * 0.2 + 0.3) if detected else 0.0

        return RoutingPlan(
            message=message,
            detected_keywords=detected,
            suggested_specialists=list(specialists),
            confidence=confidence,
        )

    def _should_escalate(self, executive_role: AgentRole, plan: RoutingPlan) -> Optional[str]:
        """
        Check if this executive should escalate to another executive instead.
        Uses the role's escalation_rules from role_definitions.py.
        """
        # Map specialist types to escalation categories
        specialist_to_category = {
            SpecialistType.NOVA: "operational",      # Research = COO domain
            SpecialistType.PIXEL: "marketing",      # Design = Content Director
            SpecialistType.FORGE: "marketing",       # Listings = Content Director
            SpecialistType.CIPHER: "customer",       # Comms = CRM
            SpecialistType.MERCHANT: "operational",    # Sales = COO
            SpecialistType.PROMOTER: "marketing",      # Ads = Content Director
            SpecialistType.GROWTH: "marketing",      # Growth = Content Director
        }

        # If executive doesn't handle this category, escalate
        for specialist in plan.suggested_specialists:
            category = specialist_to_category.get(specialist)
            if category and category in executive_role.escalation_rules:
                # Only escalate if confidence is low (executive might still handle it)
                if plan.confidence < 0.7:
                    return executive_role.escalation_rules[category]

        return None

    def _requires_approval(self, plan: RoutingPlan) -> bool:
        """Check if any suggested specialist requires approval."""
        # Phase 2: Use template data. Phase 3: Query governance v2.
        approval_required_specialists = {
            SpecialistType.MERCHANT,
            SpecialistType.PROMOTER,
        }
        return any(s in approval_required_specialists for s in plan.suggested_specialists)

    def _estimate_cost(self, plan: RoutingPlan) -> float:
        """Rough cost estimate based on specialists involved."""
        cost_map = {
            SpecialistType.NOVA: 0.05,
            SpecialistType.PIXEL: 0.50,      # Design is expensive
            SpecialistType.FORGE: 0.10,
            SpecialistType.CIPHER: 0.05,
            SpecialistType.MERCHANT: 0.10,
            SpecialistType.PROMOTER: 0.25,   # Ads need budget
            SpecialistType.GROWTH: 0.10,
        }
        return sum(cost_map.get(s, 0.05) for s in plan.suggested_specialists)

    def _build_plan_description(self, plan: RoutingPlan) -> str:
        """Human-readable description of the plan."""
        if not plan.suggested_specialists:
            return "General inquiry — no specialist needed"

        names = [s.value.title() for s in plan.suggested_specialists]
        if len(names) == 1:
            return f"{names[0]} task detected"
        elif len(names) == 2:
            return f"{names[0]} + {names[1]} collaboration"
        else:
            return f"Multi-specialist workflow ({len(names)} agents)"


# ── Singleton ────────────────────────────────────────────────────────────

_ultron_orchestrator: Optional[UltronOrchestrator] = None


def get_ultron_orchestrator() -> UltronOrchestrator:
    global _ultron_orchestrator
    if _ultron_orchestrator is None:
        _ultron_orchestrator = UltronOrchestrator()
    return _ultron_orchestrator
