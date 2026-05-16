"""
Tests for RevenueTracker — Phase 7
AgentWorld v2.0 — Revenue Feedback Loop
"""

import pytest
from datetime import datetime, timezone, timedelta

from services.revenue_tracker import (
    RevenueTracker,
    WeeklyCostReport,
    get_revenue_tracker,
)


# ── Instantiation ────────────────────────────────────────────────────────

def test_tracker_creation():
    """RevenueTracker can be instantiated."""
    tracker = RevenueTracker()
    assert tracker is not None


def test_tracker_singleton():
    """get_revenue_tracker returns singleton."""
    t1 = get_revenue_tracker()
    t2 = get_revenue_tracker()
    assert t1 is t2


# ── Record Tests ─────────────────────────────────────────────────────────

def test_record_execution():
    """Execution cost is recorded."""
    tracker = RevenueTracker()
    tracker.record_execution("proj_1", "nova", 0.05, "task_1")
    assert len(tracker._executions) == 1
    assert tracker._executions[0]["cost"] == 0.05


def test_record_approval():
    """Approval event is recorded."""
    tracker = RevenueTracker()
    tracker.record_approval("appr_1", "proj_1", "merchant", 0.50, "pending")
    assert len(tracker._approvals) == 1


# ── Weekly Report Tests ──────────────────────────────────────────────────

def test_weekly_report_empty():
    """Empty week returns zero costs."""
    tracker = RevenueTracker()
    report = tracker.generate_weekly_report()
    assert report.total_cost == 0.0
    assert report.execution_count == 0


def test_weekly_report_with_data():
    """Report aggregates execution costs."""
    tracker = RevenueTracker()
    tracker.record_execution("proj_1", "nova", 0.05, "task_1")
    tracker.record_execution("proj_1", "pixel", 0.50, "task_2")
    tracker.record_execution("proj_2", "nova", 0.05, "task_3")

    report = tracker.generate_weekly_report()
    assert report.total_cost == 0.60
    assert report.by_specialist["nova"] == 0.10
    assert report.by_specialist["pixel"] == 0.50
    assert report.execution_count == 3


def test_weekly_report_by_project():
    """Report filtered by project."""
    tracker = RevenueTracker()
    tracker.record_execution("proj_1", "nova", 0.05, "task_1")
    tracker.record_execution("proj_2", "nova", 0.10, "task_2")

    report = tracker.generate_weekly_report(project_id="proj_1")
    assert report.total_cost == 0.05
    assert report.by_project == {"proj_1": 0.05}


# ── Budget Tests ─────────────────────────────────────────────────────────

def test_budget_allow():
    """Budget check allows when under limit."""
    tracker = RevenueTracker()
    tracker.set_budget("proj_1", 1.00)
    tracker.record_execution("proj_1", "nova", 0.05, "task_1")

    result = tracker.check_budget("proj_1", 0.10)
    assert result["allowed"] is True
    assert result["remaining"] == 0.95  # budget - current_spend


def test_budget_deny():
    """Budget check denies when over limit."""
    tracker = RevenueTracker()
    tracker.set_budget("proj_1", 0.50)
    tracker.record_execution("proj_1", "nova", 0.45, "task_1")

    result = tracker.check_budget("proj_1", 0.10)
    assert result["allowed"] is False
    assert "exceed" in result["reason"]


def test_budget_warning():
    """Budget check warns at 90%."""
    tracker = RevenueTracker()
    tracker.set_budget("proj_1", 1.00)
    tracker.record_execution("proj_1", "nova", 0.85, "task_1")

    result = tracker.check_budget("proj_1", 0.05)
    assert result["allowed"] is True
    assert "90%" in result["warning"]


def test_budget_no_budget_set():
    """No budget set allows everything."""
    tracker = RevenueTracker()
    result = tracker.check_budget("proj_unknown", 1.00)
    assert result["allowed"] is True
    assert "No budget set" in result["reason"]


# ── Threshold Tests ────────────────────────────────────────────────────────

def test_threshold_75_percent():
    """Report flags 75% threshold."""
    tracker = RevenueTracker()
    tracker.set_budget("proj_1", 1.00)
    tracker.record_execution("proj_1", "nova", 0.80, "task_1")

    report = tracker.generate_weekly_report(project_id="proj_1")
    assert report.budget_threshold_hit == "75%"


def test_threshold_90_percent():
    """Report flags 90% threshold."""
    tracker = RevenueTracker()
    tracker.set_budget("proj_1", 1.00)
    tracker.record_execution("proj_1", "nova", 0.95, "task_1")

    report = tracker.generate_weekly_report(project_id="proj_1")
    assert report.budget_threshold_hit == "90%"


# ── Recommendation Tests ─────────────────────────────────────────────────

def test_recommendations_high_cost():
    """Recommends when specialist cost is high."""
    tracker = RevenueTracker()
    tracker.set_budget("proj_1", 5.00)
    tracker.record_execution("proj_1", "pixel", 2.00, "task_1")

    recs = tracker.get_recommendations("proj_1")
    assert any("Pixel" in r for r in recs)


def test_recommendations_low_ratio():
    """Recommends when approval ratio is low."""
    tracker = RevenueTracker()
    tracker.set_budget("proj_1", 5.00)
    # 3 approvals, 1 execution = ratio 0.33 (< 0.5)
    tracker.record_approval("appr_1", "proj_1", "merchant", 0.50, "pending")
    tracker.record_approval("appr_2", "proj_1", "merchant", 0.50, "pending")
    tracker.record_approval("appr_3", "proj_1", "merchant", 0.50, "pending")
    tracker.record_execution("proj_1", "merchant", 0.50, "task_1")

    recs = tracker.get_recommendations("proj_1")
    assert any("ratio" in r for r in recs)


def test_recommendations_threshold():
    """Recommends when budget threshold hit."""
    tracker = RevenueTracker()
    tracker.set_budget("proj_1", 1.00)
    tracker.record_execution("proj_1", "nova", 1.00, "task_1")

    recs = tracker.get_recommendations("proj_1")
    assert any("threshold" in r for r in recs)


# ── Serialization Tests ──────────────────────────────────────────────────

def test_report_to_dict():
    """WeeklyCostReport serializes to dict."""
    tracker = RevenueTracker()
    tracker.record_execution("proj_1", "nova", 0.05, "task_1")
    report = tracker.generate_weekly_report()

    d = report.to_dict()
    assert "week_start" in d
    assert "week_end" in d
    assert d["total_cost"] == 0.05
    assert d["by_specialist"] == {"nova": 0.05}


# ── Cron Integration Test ─────────────────────────────────────────────────

def test_cron_simulation():
    """Simulate weekly cron job execution."""
    tracker = RevenueTracker()
    tracker.set_budget("proj_etsy", 5.00)
    tracker.set_budget("proj_tiktok", 3.00)

    # Simulate a week of activity
    tracker.record_execution("proj_etsy", "nova", 0.05, "task_1")
    tracker.record_execution("proj_etsy", "pixel", 1.50, "task_2")  # > 1.0 to trigger rec
    tracker.record_execution("proj_etsy", "forge", 0.10, "task_3")
    tracker.record_execution("proj_tiktok", "promoter", 0.25, "task_4")
    tracker.record_execution("proj_tiktok", "growth", 0.10, "task_5")

    # Generate reports
    etsy_report = tracker.generate_weekly_report(project_id="proj_etsy")
    tiktok_report = tracker.generate_weekly_report(project_id="proj_tiktok")

    assert etsy_report.total_cost == 1.65
    assert tiktok_report.total_cost == 0.35
    assert etsy_report.by_specialist["pixel"] == 1.50

    # Check budgets
    etsy_budget = tracker.check_budget("proj_etsy", 1.00)
    assert etsy_budget["allowed"] is True
    assert etsy_budget["remaining"] == 3.35  # 5.00 - 1.65

    # Get recommendations
    recs = tracker.get_recommendations("proj_etsy")
    assert any("Pixel" in r for r in recs)
