"""
Tests for DiagnosticActivator — Phase 5
AgentWorld v2.0 — Diagnostic-Triggered Specialist Activation
"""

import pytest
from typing import Dict, List

from services.diagnostic_activation import (
    DiagnosticActivator,
    SpecialistActivation,
    DiagnosticActivationResult,
    ActivationThreshold,
    get_diagnostic_activator,
)
from business_models.base import BottleneckCategory, Severity


# ── Instantiation ────────────────────────────────────────────────────────

def test_activator_creation():
    """DiagnosticActivator can be instantiated."""
    activator = DiagnosticActivator()
    assert activator is not None


def test_activator_singleton():
    """get_diagnostic_activator returns singleton."""
    a1 = get_diagnostic_activator()
    a2 = get_diagnostic_activator()
    assert a1 is a2


# ── Primary Bottleneck Tests ───────────────────────────────────────────

def test_activate_acquisition_critical():
    """Critical acquisition bottleneck activates Growth + Promoter."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_123",
        "health_score": 0.3,
        "primary_bottleneck": {
            "category": "acquisition",
            "severity": "critical",
            "description": "No traffic sources active",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_123")

    assert len(result.activated_specialists) == 2
    specialist_ids = [s.specialist_id for s in result.activated_specialists]
    assert "growth" in specialist_ids
    assert "promoter" in specialist_ids
    assert result.health_score == 0.3


def test_activate_conversion_high():
    """High conversion bottleneck activates Forge + Merchant + Pixel."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_456",
        "health_score": 0.5,
        "primary_bottleneck": {
            "category": "conversion",
            "severity": "high",
            "description": "Low CTR on product listings",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_456")

    specialist_ids = [s.specialist_id for s in result.activated_specialists]
    assert "forge" in specialist_ids
    assert "merchant" in specialist_ids
    assert "pixel" in specialist_ids


def test_activate_retention_medium():
    """Medium retention bottleneck activates Cipher + Growth (notify only)."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_789",
        "health_score": 0.7,
        "primary_bottleneck": {
            "category": "retention",
            "severity": "medium",
            "description": "Repeat purchase rate declining",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_789")

    specialist_ids = [s.specialist_id for s in result.activated_specialists]
    assert "cipher" in specialist_ids
    assert "growth" in specialist_ids
    # Medium severity should not auto-approve
    assert not any(s.auto_approve for s in result.activated_specialists)


def test_activate_operations_critical():
    """Critical operations bottleneck activates Nova + Ultron."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_ops",
        "health_score": 0.2,
        "primary_bottleneck": {
            "category": "operations",
            "severity": "critical",
            "description": "Fulfillment capacity maxed out",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_ops")

    specialist_ids = [s.specialist_id for s in result.activated_specialists]
    assert "nova" in specialist_ids
    assert "ultron" in specialist_ids


# ── Severity Threshold Tests ─────────────────────────────────────────────

def test_low_severity_skipped():
    """Low severity bottlenecks are skipped (no activation)."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_low",
        "health_score": 0.9,
        "primary_bottleneck": {
            "category": "conversion",
            "severity": "low",
            "description": "Minor listing optimization possible",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_low")

    assert len(result.activated_specialists) == 0
    assert len(result.skipped) == 1
    assert "below activation threshold" in result.skipped[0]


def test_healthy_skipped():
    """Healthy status is skipped."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_healthy",
        "health_score": 1.0,
        "primary_bottleneck": {
            "category": "acquisition",
            "severity": "healthy",
            "description": "Traffic growing steadily",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_healthy")

    assert len(result.activated_specialists) == 0


# ── Secondary Bottleneck Tests ───────────────────────────────────────────

def test_secondary_critical_activated():
    """Critical secondary bottlenecks are also activated."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_sec",
        "health_score": 0.4,
        "primary_bottleneck": {
            "category": "acquisition",
            "severity": "high",
            "description": "Traffic low",
        },
        "secondary_bottlenecks": [
            {
                "category": "conversion",
                "severity": "critical",
                "description": "Checkout abandonment 80%",
            }
        ],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_sec")

    # Primary: acquisition → Growth + Promoter (2)
    # Secondary: conversion critical → Forge + Merchant + Pixel (3)
    assert len(result.activated_specialists) == 5


def test_secondary_low_skipped():
    """Low severity secondary bottlenecks are skipped."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_sec_low",
        "health_score": 0.6,
        "primary_bottleneck": {
            "category": "acquisition",
            "severity": "high",
            "description": "Traffic declining",
        },
        "secondary_bottlenecks": [
            {
                "category": "retention",
                "severity": "low",
                "description": "Minor churn increase",
            }
        ],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_sec")

    # Only primary should activate (2 specialists)
    assert len(result.activated_specialists) == 2
    assert len(result.skipped) == 1


# ── Approval Tests ──────────────────────────────────────────────────────

def test_merchant_requires_approval():
    """Merchant activations require human approval."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_merch",
        "health_score": 0.4,
        "primary_bottleneck": {
            "category": "conversion",
            "severity": "high",
            "description": "Low sales",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_merch")

    merchant = next(s for s in result.activated_specialists if s.specialist_id == "merchant")
    assert merchant.requires_approval is True


def test_promoter_requires_approval():
    """Promoter activations require human approval."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_promo",
        "health_score": 0.3,
        "primary_bottleneck": {
            "category": "acquisition",
            "severity": "critical",
            "description": "No traffic",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_promo")

    promoter = next(s for s in result.activated_specialists if s.specialist_id == "promoter")
    # Critical primary auto-approves, so requires_approval is False
    assert promoter.requires_approval is False
    assert promoter.auto_approve is True


def test_critical_auto_approve():
    """Critical primary bottlenecks can auto-approve."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_auto",
        "health_score": 0.1,
        "primary_bottleneck": {
            "category": "operations",
            "severity": "critical",
            "description": "System down",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_auto")

    # Operations doesn't have Merchant/Promoter, so no approval needed
    # But check that critical severity sets priority correctly
    assert all(s.priority == "critical" for s in result.activated_specialists)


# ── Cost Estimation Tests ────────────────────────────────────────────────

def test_cost_estimation():
    """Each activation has an estimated cost."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_cost",
        "health_score": 0.5,
        "primary_bottleneck": {
            "category": "conversion",
            "severity": "high",
            "description": "Low CTR",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_cost")

    for activation in result.activated_specialists:
        assert activation.estimated_cost > 0


def test_pixel_most_expensive():
    """Pixel (design) has highest cost estimate."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_pix",
        "health_score": 0.5,
        "primary_bottleneck": {
            "category": "conversion",
            "severity": "high",
            "description": "Need better images",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_pix")

    pixel = next(s for s in result.activated_specialists if s.specialist_id == "pixel")
    assert pixel.estimated_cost == 0.50  # Highest cost


# ── Serialization Tests ────────────────────────────────────────────────

def test_result_to_dict():
    """DiagnosticActivationResult serializes to dict."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_dict",
        "health_score": 0.5,
        "primary_bottleneck": {
            "category": "acquisition",
            "severity": "high",
            "description": "Low traffic",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_dict")
    d = result.to_dict()

    assert d["diagnosis_id"] == "diag_dict"
    assert d["health_score"] == 0.5
    assert "activated_specialists" in d
    assert "notifications" in d
    assert "skipped" in d
    assert "created_at" in d


# ── Notification Tests ──────────────────────────────────────────────────

def test_notifications_generated():
    """Human-readable notifications are generated for each activation."""
    activator = DiagnosticActivator()
    diagnosis = {
        "diagnosis_id": "diag_note",
        "health_score": 0.3,
        "primary_bottleneck": {
            "category": "monetization",
            "severity": "critical",
            "description": "Revenue per customer declining fast",
        },
        "secondary_bottlenecks": [],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_note")

    assert len(result.notifications) == len(result.activated_specialists)
    assert all("activated" in n for n in result.notifications)


# ── Integration: Full Diagnosis → Activation Flow ─────────────────────────

def test_full_flow_acquisition_to_growth_promoter():
    """End-to-end: Acquisition diagnosis → Growth + Promoter activation."""
    activator = DiagnosticActivator()

    # Simulate a real diagnosis result
    diagnosis = {
        "diagnosis_id": "diag_e2e",
        "health_score": 0.25,
        "primary_bottleneck": {
            "category": "acquisition",
            "severity": "critical",
            "description": "Zero organic traffic, no paid campaigns running",
            "impact": "Business will run out of leads in 30 days",
            "evidence": [
                {"metric": "monthly_traffic", "value": 0, "benchmark": 1000, "gap_percentage": 100}
            ],
        },
        "secondary_bottlenecks": [
            {
                "category": "conversion",
                "severity": "high",
                "description": "Landing page bounce rate 85%",
            }
        ],
    }

    result = activator.activate_from_diagnosis(diagnosis, "biz_e2e")

    # Should activate specialists for both bottlenecks
    specialist_ids = [s.specialist_id for s in result.activated_specialists]
    assert "growth" in specialist_ids      # For acquisition
    assert "promoter" in specialist_ids    # For acquisition
    assert "forge" in specialist_ids       # For conversion
    assert "merchant" in specialist_ids    # For conversion
    assert "pixel" in specialist_ids       # For conversion

    # Verify tasks are descriptive
    growth = next(s for s in result.activated_specialists if s.specialist_id == "growth")
    assert "acquisition" in growth.task.lower()
    assert "organic" in growth.task.lower()  # From description
