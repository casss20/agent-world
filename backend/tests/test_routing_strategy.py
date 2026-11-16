"""
Tests for Routing Strategy — Phase 5
"""

import pytest
from core.routing.routing_rules import TaskTier
from core.routing.llm_router import RuleBasedStrategy


def test_strategy_name():
    s = RuleBasedStrategy()
    assert s.name() == "rule_based"


def test_strategy_description():
    s = RuleBasedStrategy()
    assert "keyword" in s.description().lower()


def test_strategy_classify_standard_default():
    s = RuleBasedStrategy()
    tier = s.classify("random task", "unknown", "", ["mock"])
    assert tier == TaskTier.STANDARD
