"""
Plugin System Tests
Verify BaseProvider, PluginRegistry, PluginLoader work correctly.
"""

import os
import pytest
import asyncio
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_agentverse.db"

from plugins.base.base_provider import BaseProvider, ProviderCapability, ProviderStatus
from plugins.base.plugin_registry import PluginRegistry
from plugins.plugin_loader import PluginLoader


# ── Mock Provider (for testing only) ─────────────────────────────────────


class MockProvider(BaseProvider):
    def __init__(self):
        super().__init__(name="test", provider_type="test_type", version="1.0.0")

    def initialize(self, config=None):
        self.status = ProviderStatus.ACTIVE
        return True

    def get_capability(self):
        return ProviderCapability(
            name="test",
            version="1.0.0",
            description="Test provider",
            parameters={"required": ["input"]},
            output_type="text",
        )

    async def execute(self, parameters):
        return {"success": True, "result": parameters.get("input"), "error": None}

    async def health_check(self):
        return True


# ── BaseProvider Tests ─────────────────────────────────────────────────


def test_base_provider_is_abstract():
    """BaseProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseProvider()


def test_mock_provider_instantiates():
    """Concrete subclass should instantiate."""
    p = MockProvider()
    assert p.name == "test"
    assert p.provider_type == "test_type"
    assert p.status == ProviderStatus.INACTIVE


def test_provider_initializes():
    """Provider should initialize successfully."""
    p = MockProvider()
    result = p.initialize()
    assert result is True
    assert p.status == ProviderStatus.ACTIVE
    assert p.is_active()


@pytest.mark.asyncio
async def test_provider_execute():
    """Provider execute should return structured response."""
    p = MockProvider()
    p.initialize()
    result = await p.execute({"input": "hello"})
    assert result["success"] is True
    assert result["result"] == "hello"


@pytest.mark.asyncio
async def test_provider_health_check():
    """Health check should pass for active provider."""
    p = MockProvider()
    p.initialize()
    assert await p.health_check() is True


def test_provider_validate_parameters():
    """Validation should detect missing required params."""
    p = MockProvider()
    p.initialize()
    missing = p.validate_parameters({})
    assert "input" in missing
    missing = p.validate_parameters({"input": "x"})
    assert missing == []


def test_provider_metadata():
    """Metadata should include name, type, version, status."""
    p = MockProvider()
    p.initialize()
    meta = p.get_metadata()
    assert meta["name"] == "test"
    assert meta["type"] == "test_type"
    assert meta["status"] == "active"


# ── PluginRegistry Tests ───────────────────────────────────────────────


def test_registry_singleton():
    """PluginLoader should return same registry instance."""
    PluginLoader.reset_registry()
    r1 = PluginLoader.get_registry()
    r2 = PluginLoader.get_registry()
    assert r1 is r2


def test_registry_register_and_retrieve():
    """Should register and retrieve a provider."""
    PluginLoader.reset_registry()
    registry = PluginLoader.get_registry()
    p = MockProvider()
    p.initialize()
    registry.register("my_test", p, p.get_capability())

    retrieved = registry.get_provider("my_test")
    assert retrieved is p
    assert retrieved.name == "test"


def test_registry_get_by_type():
    """Should retrieve providers by type."""
    PluginLoader.reset_registry()
    registry = PluginLoader.get_registry()
    p = MockProvider()
    p.initialize()
    registry.register("t1", p, p.get_capability())

    providers = registry.get_providers_by_type("test_type")
    assert len(providers) == 1
    assert providers[0].name == "test"


def test_registry_unload():
    """Should unregister providers cleanly."""
    PluginLoader.reset_registry()
    registry = PluginLoader.get_registry()
    p = MockProvider()
    p.initialize()
    registry.register("unload_me", p)
    assert registry.has_provider("unload_me")

    registry.unregister("unload_me")
    assert not registry.has_provider("unload_me")


def test_registry_keyerror_on_missing():
    """Should raise KeyError for unknown provider."""
    PluginLoader.reset_registry()
    registry = PluginLoader.get_registry()
    with pytest.raises(KeyError):
        registry.get_provider("nonexistent")


def test_registry_mark_failed():
    """Should track failed plugin loads."""
    PluginLoader.reset_registry()
    registry = PluginLoader.get_registry()
    registry.mark_failed("bad_plugin", "SyntaxError")
    assert len(registry.get_failed_plugins()) == 1
    assert registry.get_failed_plugins()[0]["name"] == "bad_plugin"


def test_registry_status():
    """Status summary should report totals."""
    PluginLoader.reset_registry()
    registry = PluginLoader.get_registry()
    p = MockProvider()
    p.initialize()
    registry.register("s1", p, p.get_capability())
    registry.mark_failed("f1", "error")

    status = registry.get_status()
    assert status["total"] == 1
    assert status["failed"] == 1
    assert status["by_type"]["test_type"] == 1


@pytest.mark.asyncio
async def test_registry_health_check_all():
    """Should health-check all providers."""
    PluginLoader.reset_registry()
    registry = PluginLoader.get_registry()
    p = MockProvider()
    p.initialize()
    registry.register("h1", p)

    results = await registry.health_check_all_async()
    assert results["h1"] is True


# ── PluginLoader Integration Tests ─────────────────────────────────────


def test_load_all_plugins_empty_dir(tmp_path):
    """Loading from empty dir should return empty registry."""
    PluginLoader.reset_registry()
    registry = PluginLoader.load_all_plugins(tmp_path)
    assert registry.get_status()["total"] == 0


def test_load_all_plugins_with_bad_file(tmp_path):
    """Syntax error in plugin should not crash loader."""
    # PluginLoader expects category subdirectories
    category_dir = tmp_path / "testcat"
    category_dir.mkdir()
    bad_plugin = category_dir / "bad_provider.py"
    bad_plugin.write_text("this is not valid python!!!")

    PluginLoader.reset_registry()
    registry = PluginLoader.load_all_plugins(tmp_path)
    assert registry.get_status()["failed"] == 1
    assert registry.get_status()["total"] == 0


def test_load_all_plugins_with_good_provider(tmp_path):
    """Valid provider file should load successfully."""
    category_dir = tmp_path / "image_gen"
    category_dir.mkdir()
    good_plugin = category_dir / "dalle_provider.py"
    good_plugin.write_text('''
from plugins.base.base_provider import BaseProvider, ProviderCapability, ProviderStatus

class DalleProvider(BaseProvider):
    def __init__(self):
        super().__init__(name="dalle", provider_type="image_gen", version="1.0")

    def initialize(self, config=None):
        self.status = ProviderStatus.ACTIVE
        return True

    def get_capability(self):
        return ProviderCapability(name="dalle", version="1.0", description="DALL-E image generation")

    async def execute(self, parameters):
        return {"success": True, "result": "https://example.com/image.png"}

    async def health_check(self):
        return True
''')

    PluginLoader.reset_registry()
    registry = PluginLoader.load_all_plugins(tmp_path)
    assert registry.get_status()["total"] == 1
    assert registry.get_status()["failed"] == 0
    assert registry.has_provider("image_gen/dalle")


def test_load_all_plugins_skips_non_provider_files(tmp_path):
    """Files not ending in _provider.py should be skipped."""
    category_dir = tmp_path / "tools"
    category_dir.mkdir()
    helper = category_dir / "helper.py"
    helper.write_text("x = 1")

    PluginLoader.reset_registry()
    registry = PluginLoader.load_all_plugins(tmp_path)
    assert registry.get_status()["total"] == 0


# ── Integration: PluginLoader + existing plugin_manager.py ─────────────


@pytest.mark.asyncio
async def test_integration_with_plugin_manager():
    """New BaseProvider system should coexist with existing plugin_manager."""
    from plugin_manager import PluginManager, BasePlugin

    # Existing plugin_manager still works
    pm = PluginManager()
    await pm.initialize()

    # New PluginLoader works independently
    PluginLoader.reset_registry()
    registry = PluginLoader.get_registry()
    p = MockProvider()
    p.initialize()
    registry.register("compat_test", p)

    assert pm.is_loaded("compat_test") is False  # Different system
    assert registry.has_provider("compat_test") is True

    # Both can coexist
    assert len(pm.list_plugins()) == 0
    assert len(registry.get_provider_names()) == 1
