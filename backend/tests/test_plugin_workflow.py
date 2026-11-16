"""
Plugin Manager + Native Workflow Engine Tests
"""

import os
import pytest
import asyncio
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_agentverse.db"

import plugin_manager
from plugin_manager import PluginManager, PluginError, ExtensionPoint, BasePlugin
from workflow_engine_native import (
    WorkflowEngineNative,
    WorkflowDefinition,
    WorkflowTask,
    WorkflowStatus,
    WorkflowResult,
    TaskResult,
    TaskPriority,
    WorkflowMetrics,
    WorkflowDebugInfo,
    WorkflowEngineError,
)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    from database import init_db, close_engine
    asyncio.run(init_db())
    yield
    asyncio.run(close_engine())


# ── Plugin Manager Tests ─────────────────────────────────────────────────


class MockPlugin(BasePlugin):
    def __init__(self, plugin_id, name="Mock", version="1.0.0", priority=0, deps=None):
        super().__init__(
            plugin_id=plugin_id,
            name=name,
            version=version,
            priority=priority,
            dependencies=deps or [],
        )
        self.initialized = False
        self.shutdown_called = False

    async def on_initialize(self):
        self.initialized = True

    async def on_shutdown(self):
        self.shutdown_called = True

    def register_test_point(self):
        async def handler(ctx):
            return {"plugin_id": self.id, "context": ctx}
        self.register_extension_point("test.point", handler, priority=self.priority)


@pytest.mark.asyncio
async def test_plugin_manager_lifecycle():
    """PluginManager should initialize and shutdown cleanly."""
    pm = PluginManager()
    await pm.initialize()
    assert pm._initialized is True
    await pm.shutdown()
    assert pm._initialized is False


@pytest.mark.asyncio
async def test_load_and_unload_plugin():
    """Should load a plugin and register its extension points."""
    pm = PluginManager()
    plugin = MockPlugin("mock-1")
    plugin.register_test_point()

    await pm.load_plugin(plugin)
    assert pm.is_loaded("mock-1")
    assert plugin.initialized

    # Invoke extension point
    results = await pm.invoke_extension_point("test.point", {"foo": "bar"})
    assert len(results) == 1
    assert results[0]["plugin_id"] == "mock-1"

    await pm.unload_plugin("mock-1")
    assert not pm.is_loaded("mock-1")
    assert plugin.shutdown_called


@pytest.mark.asyncio
async def test_plugin_priority_ordering():
    """Extension point handlers should respect priority."""
    pm = PluginManager()
    low = MockPlugin("low", priority=1)
    high = MockPlugin("high", priority=10)
    low.register_test_point()
    high.register_test_point()

    await pm.load_plugin(low)
    await pm.load_plugin(high)

    results = await pm.invoke_extension_point("test.point", "ctx")
    # High priority first
    assert results[0]["plugin_id"] == "high"
    assert results[1]["plugin_id"] == "low"


@pytest.mark.asyncio
async def test_plugin_dependencies():
    """Should enforce plugin dependencies."""
    pm = PluginManager()
    child = MockPlugin("child", deps=["parent"])

    with pytest.raises(PluginError) as exc:
        await pm.load_plugin(child)
    assert "depends on 'parent'" in str(exc.value)

    parent = MockPlugin("parent")
    await pm.load_plugin(parent)
    await pm.load_plugin(child)  # Now succeeds


@pytest.mark.asyncio
async def test_plugin_version_compatibility():
    """Should enforce core version compatibility."""
    pm = PluginManager(core_version="3.0.0")
    too_new = MockPlugin("too-new")
    too_new.min_core_version = "4.0.0"

    with pytest.raises(PluginError) as exc:
        await pm.load_plugin(too_new)
    assert "requires core >= 4.0.0" in str(exc.value)


@pytest.mark.asyncio
async def test_plugin_unload_reverse_deps():
    """Should prevent unloading a plugin that others depend on."""
    pm = PluginManager()
    await pm.load_plugin(MockPlugin("parent"))
    await pm.load_plugin(MockPlugin("child", deps=["parent"]))

    with pytest.raises(PluginError) as exc:
        await pm.unload_plugin("parent")
    assert "depends on it" in str(exc.value)


@pytest.mark.asyncio
async def test_plugin_reload():
    """Should reload a plugin with a new instance."""
    pm = PluginManager()
    old = MockPlugin("reload-test", version="1.0")
    await pm.load_plugin(old)

    new = MockPlugin("reload-test", version="2.0")
    await pm.reload_plugin("reload-test", new)

    meta = pm.get_plugin_metadata("reload-test")
    assert meta["version"] == "2.0"


@pytest.mark.asyncio
async def test_plugin_error_isolation():
    """A failing extension point handler should not break others."""
    pm = PluginManager()
    good = MockPlugin("good")
    good.register_test_point()

    bad = MockPlugin("bad")
    async def bad_handler(ctx):
        raise ValueError("boom")
    bad.register_extension_point("test.point", bad_handler)

    await pm.load_plugin(good)
    await pm.load_plugin(bad)

    results = await pm.invoke_extension_point("test.point", "ctx")
    assert len(results) == 2
    # One is a dict with error, one is a dict with plugin_id
    statuses = ["error" in str(r) for r in results]
    assert any(statuses)
    assert not all(statuses)


# ── Native Workflow Engine Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_workflow_dependency_resolution():
    """WorkflowTask should resolve dependencies in topological order."""
    a = WorkflowTask(id="a", type="code", description="A")
    b = WorkflowTask(id="b", type="code", description="B", dependencies=["a"])
    c = WorkflowTask(id="c", type="code", description="C", dependencies=["b"])

    ordered = WorkflowTask.resolve_execution_order([c, a, b])
    ids = [t.id for t in ordered]
    assert ids == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_workflow_priority_sorting():
    """High-priority tasks should come before medium/low."""
    low = WorkflowTask(id="low", type="code", description="Low", priority=TaskPriority.LOW)
    med = WorkflowTask(id="med", type="code", description="Med", priority=TaskPriority.MEDIUM)
    high = WorkflowTask(id="high", type="code", description="High", priority=TaskPriority.HIGH)

    sorted_tasks = WorkflowTask.sort_by_priority([med, low, high])
    ids = [t.id for t in sorted_tasks]
    assert ids == ["high", "med", "low"]


@pytest.mark.asyncio
async def test_workflow_execution_basic():
    """Engine should execute a simple workflow."""
    engine = WorkflowEngineNative()
    await engine.initialize()

    # Create a simple workflow with two independent tasks
    wf = WorkflowDefinition(
        id="basic-wf",
        name="Basic Workflow",
        tasks=[
            WorkflowTask(id="t1", type="code", description="Task 1"),
            WorkflowTask(id="t2", type="code", description="Task 2"),
        ],
    )

    result = await engine.execute_workflow(wf)
    assert result.status == "completed"
    assert result.tasks_completed == 2
    assert result.tasks_failed == 0
    assert len(result.execution_order) == 2


@pytest.mark.asyncio
async def test_workflow_execution_with_dispatcher():
    """Engine should use task_dispatcher when provided."""
    calls = []

    async def dispatcher(task, agent_id):
        calls.append((task.id, agent_id))
        return TaskResult(task_id=task.id, status="completed", result="ok")

    engine = WorkflowEngineNative(task_dispatcher=dispatcher)
    await engine.initialize()

    wf = WorkflowDefinition(
        id="dispatch-wf",
        name="Dispatch Workflow",
        tasks=[
            WorkflowTask(id="d1", type="code", description="D1", assigned_to="agent-1"),
            WorkflowTask(id="d2", type="code", description="D2", assigned_to="agent-2"),
        ],
    )

    result = await engine.execute_workflow(wf)
    assert result.status == "completed"
    assert len(calls) == 2
    assert calls[0] == ("d1", "agent-1")
    assert calls[1] == ("d2", "agent-2")


@pytest.mark.asyncio
async def test_workflow_nested_execution():
    """Engine should execute nested workflows."""
    inner = WorkflowDefinition(
        id="inner",
        name="Inner",
        tasks=[
            WorkflowTask(id="inner-1", type="code", description="Inner 1"),
        ],
    )

    outer = WorkflowDefinition(
        id="outer",
        name="Outer",
        tasks=[
            WorkflowTask(
                id="outer-1",
                type="workflow",
                description="Nested task",
                nested_workflow=inner,
            ),
        ],
    )

    engine = WorkflowEngineNative()
    await engine.initialize()
    result = await engine.execute_workflow(outer)
    assert result.status == "completed"
    assert result.tasks_completed == 1


@pytest.mark.asyncio
async def test_workflow_rollback_on_failure():
    """Engine should execute rollback hooks when a task fails."""
    rollback_log = []

    async def fail_execute(task):
        raise RuntimeError("Task failed")

    async def rollback_handler(task):
        rollback_log.append(task.id)

    wf = WorkflowDefinition(
        id="rollback-wf",
        name="Rollback Test",
        tasks=[
            WorkflowTask(
                id="r1",
                type="code",
                description="R1",
                on_execute=fail_execute,
                on_rollback=rollback_handler,
            ),
        ],
        rollback_on_failure=True,
    )

    engine = WorkflowEngineNative()
    await engine.initialize()
    result = await engine.execute_workflow(wf)
    assert result.status == "failed"
    assert "Task failed" in result.errors[0]
    assert "r1" in rollback_log


@pytest.mark.asyncio
async def test_workflow_pause_resume():
    """Engine should support pausing and resuming workflow execution."""
    async def slow_execute(task):
        await asyncio.sleep(0.5)

    wf = WorkflowDefinition(
        id="pause-wf",
        name="Pause Test",
        tasks=[
            WorkflowTask(id="p1", type="code", description="P1", on_execute=slow_execute),
            WorkflowTask(id="p2", type="code", description="P2", on_execute=slow_execute),
        ],
    )

    engine = WorkflowEngineNative()
    await engine.initialize()

    # Start workflow asynchronously
    task = await engine.start_workflow(wf)

    # Give it a moment to start, then pause
    await asyncio.sleep(0.15)
    await engine.pause_workflow("pause-wf")

    state = engine.get_workflow_state("pause-wf")
    assert state.status == WorkflowStatus.PAUSED

    # Resume
    await engine.resume_workflow("pause-wf")
    result = await task
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_workflow_state_persistence():
    """Engine should persist and restore workflow state."""
    persisted = {}

    async def persister(wid, state):
        persisted[wid] = state

    async def loader(wid):
        return persisted.get(wid)

    wf = WorkflowDefinition(
        id="persist-wf",
        name="Persist Test",
        tasks=[
            WorkflowTask(id="s1", type="code", description="S1"),
        ],
    )

    engine = WorkflowEngineNative(state_persister=persister, state_loader=loader)
    await engine.initialize()
    result = await engine.execute_workflow(wf)
    assert result.status == "completed"

    # Verify state was persisted
    assert "persist-wf" in persisted
    assert persisted["persist-wf"]["status"] == "completed"

    # Restore
    restored = await engine.restore_state("persist-wf")
    assert restored is not None
    assert restored.status == WorkflowStatus.COMPLETED
    assert len(restored.tasks) == 1


@pytest.mark.asyncio
async def test_workflow_metrics_and_debug():
    """Engine should collect metrics and debug info."""
    wf = WorkflowDefinition(
        id="metrics-wf",
        name="Metrics Test",
        tasks=[
            WorkflowTask(id="m1", type="code", description="M1"),
            WorkflowTask(id="m2", type="code", description="M2"),
        ],
    )

    engine = WorkflowEngineNative()
    await engine.initialize()
    result = await engine.execute_workflow(wf)
    assert result.status == "completed"

    metrics = engine.get_workflow_metrics("metrics-wf")
    assert metrics is not None
    assert metrics.tasks_total == 2
    assert metrics.tasks_completed == 2
    assert metrics.success_rate == 1.0

    debug = engine.get_workflow_debug_info("metrics-wf")
    assert debug is not None
    assert len(debug.event_log) > 0
    assert len(debug.execution_trace) == 2


@pytest.mark.asyncio
async def test_workflow_distributed_execution():
    """Engine should distribute tasks across multiple dispatchers."""
    dispatcher_calls = {0: [], 1: []}

    async def make_dispatcher(idx):
        async def dispatcher(task, agent_id):
            dispatcher_calls[idx].append(task.id)
            return TaskResult(task_id=task.id, status="completed")
        return dispatcher

    dispatchers = [await make_dispatcher(0), await make_dispatcher(1)]

    wf = WorkflowDefinition(
        id="dist-wf",
        name="Distributed",
        tasks=[
            WorkflowTask(id="d1", type="code", description="D1"),
            WorkflowTask(id="d2", type="code", description="D2"),
            WorkflowTask(id="d3", type="code", description="D3"),
            WorkflowTask(id="d4", type="code", description="D4"),
        ],
    )

    engine = WorkflowEngineNative()
    await engine.initialize()
    result = await engine.execute_distributed(wf, dispatchers)
    assert result.status == "completed"
    assert result.tasks_completed == 4
    # Tasks were distributed across both dispatchers
    total = sum(len(c) for c in dispatcher_calls.values())
    assert total == 4


@pytest.mark.asyncio
async def test_workflow_engine_shutdown():
    """Engine shutdown should cancel running workflows."""
    async def slow(task):
        await asyncio.sleep(10)

    wf = WorkflowDefinition(
        id="shutdown-wf",
        name="Shutdown Test",
        tasks=[WorkflowTask(id="s1", type="code", description="S1", on_execute=slow)],
    )

    engine = WorkflowEngineNative()
    await engine.initialize()
    running_task = await engine.start_workflow(wf)
    await asyncio.sleep(0.05)

    await engine.shutdown()
    # Cancel the running task to avoid unawaited coroutine warning
    running_task.cancel()
    try:
        await running_task
    except asyncio.CancelledError:
        pass
    state = engine.get_workflow_state("shutdown-wf")
    assert state is None or state.status == WorkflowStatus.CANCELLED
