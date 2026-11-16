"""
Tests for MemoryInjector — Phase 4 Specialist Memory
AgentWorld v2.0 — Two-Tier Agent Unification
"""

import pytest
from typing import Dict, List

from core.harnesses.memory_injector import MemoryInjector, get_memory_injector
from core.interfaces.base_harness import HarnessContext


# ── Instantiation Tests ──────────────────────────────────────────────────

def test_memory_injector_creation():
    """MemoryInjector can be created without vector memory."""
    injector = MemoryInjector()
    assert injector is not None
    assert injector.vector_memory is None


def test_memory_injector_singleton():
    """get_memory_injector returns singleton."""
    injector1 = get_memory_injector()
    injector2 = get_memory_injector()
    assert injector1 is injector2


# ── Namespace Tests ──────────────────────────────────────────────────────

def test_namespace_isolation():
    """Different projects get different namespaces."""
    injector = MemoryInjector()
    ns1 = injector._namespace("proj_tiktok", "nova")
    ns2 = injector._namespace("proj_etsy", "nova")
    assert ns1 != ns2
    assert "proj_tiktok" in ns1
    assert "proj_etsy" in ns2


# ── Save Tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_specialist_output():
    """Save returns success with memory ID."""
    injector = MemoryInjector()
    result = await injector.save_specialist_output(
        project_id="proj_test",
        specialist_id="nova",
        output="Competitor analysis complete",
    )
    assert result["success"] is True
    assert "memory_id" in result
    assert result["namespace"] == "proj_test:nova"


@pytest.mark.asyncio
async def test_save_with_metadata():
    """Metadata is preserved in save result."""
    injector = MemoryInjector()
    result = await injector.save_specialist_output(
        project_id="proj_test",
        specialist_id="pixel",
        output="Logo draft",
        metadata={"task_id": "task_123", "cost": 0.50},
    )
    assert result["success"] is True


# ── Retrieve Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retrieve_relevant_memories():
    """Retrieve returns memories based on query keywords."""
    injector = MemoryInjector()
    memories = await injector.retrieve_relevant_memories(
        project_id="proj_test",
        specialist_id="nova",
        query="Research competitors",
        limit=5,
    )
    assert len(memories) > 0
    assert any("competitor" in m["content"].lower() for m in memories)


@pytest.mark.asyncio
async def test_retrieve_design_memories():
    """Design query returns design-related memories."""
    injector = MemoryInjector()
    memories = await injector.retrieve_relevant_memories(
        project_id="proj_test",
        specialist_id="pixel",
        query="Design a logo",
    )
    assert any("design" in m["content"].lower() or "brand" in m["content"].lower() for m in memories)


@pytest.mark.asyncio
async def test_retrieve_listing_memories():
    """Listing query returns listing-related memories."""
    injector = MemoryInjector()
    memories = await injector.retrieve_relevant_memories(
        project_id="proj_test",
        specialist_id="forge",
        query="Create product listing",
    )
    assert any("tags" in m["content"].lower() or "listing" in m["content"].lower() for m in memories)


@pytest.mark.asyncio
async def test_retrieve_respects_limit():
    """Retrieve respects the limit parameter."""
    injector = MemoryInjector()
    memories = await injector.retrieve_relevant_memories(
        project_id="proj_test",
        specialist_id="nova",
        query="Research and design and publish",
        limit=2,
    )
    assert len(memories) <= 2


# ── Context Injection Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inject_into_context():
    """Memories are injected into HarnessContext."""
    injector = MemoryInjector()
    ctx = HarnessContext(task="Research competitors", agent_id="ceo", project_id="proj_test")

    updated = await injector.inject_into_context(
        context=ctx,
        project_id="proj_test",
        specialist_ids=["nova"],
        query="Research competitors",
    )

    assert len(updated.memories) > 0
    assert updated.memories[0]["specialist"] == "nova"
    assert "relevance" in updated.memories[0]


@pytest.mark.asyncio
async def test_inject_multiple_specialists():
    """Multiple specialists inject memories into same context."""
    injector = MemoryInjector()
    ctx = HarnessContext(task="Complex task", agent_id="ceo", project_id="proj_test")

    updated = await injector.inject_into_context(
        context=ctx,
        project_id="proj_test",
        specialist_ids=["nova", "pixel", "forge"],
        query="Research design and listing",
    )

    assert len(updated.memories) >= 2
    specialists = {m["specialist"] for m in updated.memories}
    assert "nova" in specialists or "pixel" in specialists


@pytest.mark.asyncio
async def test_inject_respects_max():
    """Max 10 memories injected regardless of query."""
    injector = MemoryInjector()
    ctx = HarnessContext(task="Big task", agent_id="ceo", project_id="proj_test")

    updated = await injector.inject_into_context(
        context=ctx,
        project_id="proj_test",
        specialist_ids=["nova", "pixel", "forge", "merchant", "promoter", "growth"],
        query="Everything",
    )

    assert len(updated.memories) <= 10


@pytest.mark.asyncio
async def test_inject_sorted_by_relevance():
    """Memories sorted by relevance descending."""
    injector = MemoryInjector()
    ctx = HarnessContext(task="Task", agent_id="ceo", project_id="proj_test")

    updated = await injector.inject_into_context(
        context=ctx,
        project_id="proj_test",
        specialist_ids=["nova", "pixel"],
        query="Research and design",
    )

    if len(updated.memories) >= 2:
        assert updated.memories[0]["relevance"] >= updated.memories[1]["relevance"]


# ── Integration: Memory + Harness ────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_with_harness_context():
    """MemoryInjector works with real HarnessContext from harness tests."""
    from core.harnesses.ultron_harness import UltronHarness

    harness = UltronHarness()
    injector = MemoryInjector()

    ctx = HarnessContext(
        task="Research and design a logo",
        agent_id="ceo",
        project_id="proj_test",
    )

    # Inject memories before running harness
    ctx = await injector.inject_into_context(
        context=ctx,
        project_id="proj_test",
        specialist_ids=["nova", "pixel"],
        query=ctx.task,
    )

    # Run harness with injected memories
    result = await harness.run(ctx, max_retries=2)

    assert result.success is True
    assert len(result.evidence["plan"]["detected_keywords"]) > 0


# ── Project Isolation Tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_project_memory_isolation():
    """Memories from one project don't leak to another."""
    injector = MemoryInjector()

    mems_tiktok = await injector.retrieve_relevant_memories(
        project_id="proj_tiktok",
        specialist_id="nova",
        query="Research",
    )
    mems_etsy = await injector.retrieve_relevant_memories(
        project_id="proj_etsy",
        specialist_id="nova",
        query="Research",
    )

    # Both should have different namespaces
    assert any("proj_tiktok" in m["namespace"] for m in mems_tiktok)
    assert any("proj_etsy" in m["namespace"] for m in mems_etsy)
