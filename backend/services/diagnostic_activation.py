"""
Diagnostic Activation — Phase 5
Maps diagnostic bottlenecks to specialist activation.

When a diagnosis identifies a bottleneck, automatically activate
the matching specialist(s) to address it.

This is the README promise: "Diagnoses before it prescribes."
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone

from business_models.base import BottleneckCategory, Severity

logger = logging.getLogger(__name__)


# ── Bottleneck → Specialist Mapping ──────────────────────────────────────

BOTTLENECK_TO_SPECIALIST: Dict[str, List[str]] = {
    # Acquisition — getting traffic
    "acquisition": ["growth", "promoter"],
    
    # Conversion — turning visitors into customers
    "conversion": ["forge", "merchant", "pixel"],
    
    # Retention — keeping customers
    "retention": ["cipher", "growth"],
    
    # Monetization — revenue per customer
    "monetization": ["merchant", "growth", "promoter"],
    
    # Operations — fulfillment, capacity, cash flow
    "operations": ["nova", "ultron"],  # Nova re-diagnoses, Ultron coordinates
}


# ── Severity Thresholds ──────────────────────────────────────────────────

class ActivationThreshold:
    """When to activate specialists based on severity."""
    AUTONOMOUS = {Severity.CRITICAL.value, Severity.HIGH.value}
    NOTIFY = {Severity.MEDIUM.value}
    IGNORE = {Severity.LOW.value, Severity.HEALTHY.value}


# ── Data Classes ─────────────────────────────────────────────────────────

@dataclass
class SpecialistActivation:
    """A single specialist activation request."""
    specialist_id: str
    task: str
    priority: str  # "critical", "high", "medium", "low"
    reason: str
    estimated_cost: float
    requires_approval: bool
    auto_approve: bool = False


@dataclass
class DiagnosticActivationResult:
    """Result of mapping diagnosis to specialist activations."""
    diagnosis_id: str
    business_id: str
    health_score: float
    primary_bottleneck: Optional[Dict[str, Any]]
    activated_specialists: List[SpecialistActivation]
    notifications: List[str]  # Human-readable notification messages
    skipped: List[str]  # Bottlenecks below threshold
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "business_id": self.business_id,
            "health_score": self.health_score,
            "primary_bottleneck": self.primary_bottleneck,
            "activated_specialists": [
                {
                    "specialist_id": a.specialist_id,
                    "task": a.task,
                    "priority": a.priority,
                    "reason": a.reason,
                    "estimated_cost": a.estimated_cost,
                    "requires_approval": a.requires_approval,
                    "auto_approve": a.auto_approve,
                }
                for a in self.activated_specialists
            ],
            "notifications": self.notifications,
            "skipped": self.skipped,
            "created_at": self.created_at,
        }


# ── Diagnostic Activator ───────────────────────────────────────────────

class DiagnosticActivator:
    """
    Maps diagnostic results to specialist activations.
    
    Usage:
        activator = DiagnosticActivator()
        result = activator.activate_from_diagnosis(diagnosis_dict, business_id)
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def activate_from_diagnosis(
        self,
        diagnosis: Dict[str, Any],
        business_id: str,
    ) -> DiagnosticActivationResult:
        """
        Map a diagnosis to specialist activations.

        Args:
            diagnosis: Dict with health_score, primary_bottleneck, secondary_bottlenecks
            business_id: The business that was diagnosed

        Returns:
            DiagnosticActivationResult with activated specialists and notifications
        """
        activated = []
        notifications = []
        skipped = []

        health_score = diagnosis.get("health_score", 0.0)
        primary = diagnosis.get("primary_bottleneck")
        secondaries = diagnosis.get("secondary_bottlenecks", [])

        # Process primary bottleneck
        if primary:
            result = self._process_bottleneck(primary, business_id, is_primary=True)
            activated.extend(result["activated"])
            notifications.extend(result["notifications"])
            skipped.extend(result["skipped"])

        # Process secondary bottlenecks (only critical/high)
        for secondary in secondaries:
            result = self._process_bottleneck(secondary, business_id, is_primary=False)
            activated.extend(result["activated"])
            notifications.extend(result["notifications"])
            skipped.extend(result["skipped"])

        return DiagnosticActivationResult(
            diagnosis_id=diagnosis.get("diagnosis_id", f"diag_{business_id}"),
            business_id=business_id,
            health_score=health_score,
            primary_bottleneck=primary,
            activated_specialists=activated,
            notifications=notifications,
            skipped=skipped,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _process_bottleneck(
        self,
        bottleneck: Dict[str, Any],
        business_id: str,
        is_primary: bool = False,
    ) -> Dict[str, Any]:
        """Process a single bottleneck and return activations."""
        activated = []
        notifications = []
        skipped = []

        category = bottleneck.get("category", "")
        severity = bottleneck.get("severity", "medium")
        description = bottleneck.get("description", "No description")

        # Check severity threshold
        if severity in ActivationThreshold.IGNORE:
            skipped.append(f"{category} ({severity}): below activation threshold")
            return {"activated": activated, "notifications": notifications, "skipped": skipped}

        # Map category to specialists
        specialists = BOTTLENECK_TO_SPECIALIST.get(category.lower(), [])
        if not specialists:
            self.logger.warning(f"No specialist mapping for category: {category}")
            return {"activated": activated, "notifications": notifications, "skipped": skipped}

        # Determine priority and auto-approve
        if severity in ActivationThreshold.AUTONOMOUS:
            priority = severity  # critical or high
            auto_approve = is_primary and severity == "critical"
        else:
            priority = "medium"
            auto_approve = False

        # Create activations for each mapped specialist
        for specialist_id in specialists:
            activation = SpecialistActivation(
                specialist_id=specialist_id,
                task=self._build_task(specialist_id, category, description, business_id),
                priority=priority,
                reason=f"{'Primary' if is_primary else 'Secondary'} bottleneck: {category} ({severity})",
                estimated_cost=self._estimate_cost(specialist_id),
                requires_approval=specialist_id in ["merchant", "promoter"] and not auto_approve,
                auto_approve=auto_approve,
            )
            activated.append(activation)

            notifications.append(
                f"🤖 **{specialist_id.title()}** activated for **{category}** "
                f"({severity}) — {description[:60]}..."
            )

        return {"activated": activated, "notifications": notifications, "skipped": skipped}

    def _build_task(self, specialist_id: str, category: str, description: str, business_id: str) -> str:
        """Build a task description for the specialist."""
        templates = {
            "nova": f"Re-diagnose {category} bottleneck in business {business_id}. Focus: {description}",
            "pixel": f"Create visual assets to address {category} issue. Context: {description}",
            "forge": f"Optimize listings/content for {category}. Problem: {description}",
            "cipher": f"Draft customer communications regarding {category}. Context: {description}",
            "merchant": f"Review and optimize sales channels for {category}. Context: {description}",
            "promoter": f"Design campaign to address {category}. Target: {description}",
            "growth": f"Execute organic growth strategy for {category}. Focus: {description}",
            "ultron": f"Coordinate specialist team to resolve {category}. Context: {description}",
        }
        return templates.get(specialist_id, f"Address {category} bottleneck: {description}")

    def _estimate_cost(self, specialist_id: str) -> float:
        """Estimated cost for specialist activation."""
        costs = {
            "nova": 0.05,
            "pixel": 0.50,
            "forge": 0.10,
            "cipher": 0.05,
            "merchant": 0.10,
            "promoter": 0.25,
            "growth": 0.10,
            "ultron": 0.05,
        }
        return costs.get(specialist_id, 0.10)


# ── Singleton ───────────────────────────────────────────────────────────

_diagnostic_activator: Optional[DiagnosticActivator] = None


def get_diagnostic_activator() -> DiagnosticActivator:
    global _diagnostic_activator
    if _diagnostic_activator is None:
        _diagnostic_activator = DiagnosticActivator()
    return _diagnostic_activator
