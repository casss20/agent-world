"""
Plugin Manager — Agent World
Dynamic tool/plugin load/unload/reload with dependency resolution,
version compatibility, priority ordering, and extension points.

Adapted from Ruflo v3 pattern: PluginManager.ts + Plugin.ts + ExtensionPoint.ts
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    runtime_checkable,
)

logger = logging.getLogger(__name__)


# ── Extension Points ───────────────────────────────────────────────────────


@dataclass
class ExtensionPoint:
    """A hook point where plugins can extend functionality."""

    name: str
    handler: Callable[[Any], Awaitable[Any]]
    priority: int = 0


class ExtensionPointNames:
    """Standard extension point names."""

    TASK_BEFORE_EXECUTE = "task.beforeExecute"
    TASK_AFTER_EXECUTE = "task.afterExecute"
    TASK_VALIDATE = "task.validate"

    WORKFLOW_BEFORE_EXECUTE = "workflow.beforeExecute"
    WORKFLOW_AFTER_EXECUTE = "workflow.afterExecute"
    WORKFLOW_ON_ERROR = "workflow.onError"

    AGENT_BEFORE_SPAWN = "agent.beforeSpawn"
    AGENT_AFTER_SPAWN = "agent.afterSpawn"
    AGENT_BEFORE_TERMINATE = "agent.beforeTerminate"

    MEMORY_BEFORE_STORE = "memory.beforeStore"
    MEMORY_AFTER_STORE = "memory.afterStore"
    MEMORY_BEFORE_QUERY = "memory.beforeQuery"


# ── Plugin Interface ───────────────────────────────────────────────────────


@runtime_checkable
class Plugin(Protocol):
    """Plugin contract — every plugin must satisfy this."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    homepage: str = ""
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    min_core_version: Optional[str] = None
    max_core_version: Optional[str] = None

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        ...

    async def shutdown(self) -> None:
        ...

    def get_extension_points(self) -> List[ExtensionPoint]:
        ...


# ── Base Plugin (convenience) ────────────────────────────────────────────


class BasePlugin(ABC):
    """Abstract base class for plugins — subclass and override hooks."""

    def __init__(
        self,
        *,
        plugin_id: str,
        name: str,
        version: str,
        description: str = "",
        author: str = "",
        homepage: str = "",
        priority: int = 0,
        dependencies: Optional[List[str]] = None,
        config_schema: Optional[Dict[str, Any]] = None,
        min_core_version: Optional[str] = None,
        max_core_version: Optional[str] = None,
    ):
        self.id = plugin_id
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.homepage = homepage
        self.priority = priority
        self.dependencies = dependencies or []
        self.config_schema = config_schema
        self.min_core_version = min_core_version
        self.max_core_version = max_core_version
        self._config: Optional[Dict[str, Any]] = None
        self._extension_points: List[ExtensionPoint] = []

    # ── Lifecycle hooks (override in subclass) ─────────────────────────────

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config
        await self.on_initialize()

    async def shutdown(self) -> None:
        await self.on_shutdown()

    async def on_initialize(self) -> None:
        """Override for custom initialization."""
        pass

    async def on_shutdown(self) -> None:
        """Override for custom shutdown."""
        pass

    # ── Extension points ──────────────────────────────────────────────────

    def register_extension_point(
        self, name: str, handler: Callable[[Any], Awaitable[Any]], priority: Optional[int] = None
    ) -> None:
        self._extension_points.append(
            ExtensionPoint(
                name=name,
                handler=handler,
                priority=priority if priority is not None else self.priority,
            )
        )

    def get_extension_points(self) -> List[ExtensionPoint]:
        return self._extension_points

    # ── Metadata ──────────────────────────────────────────────────────────

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
        }


# ── Plugin Manager ─────────────────────────────────────────────────────────


class PluginError(Exception):
    """Raised when a plugin operation fails."""

    pass


class PluginManager:
    """
    Manages plugin lifecycle, dependencies, version compatibility,
    priority ordering, and extension-point invocation.
    """

    def __init__(self, core_version: str = "3.0.0"):
        self._plugins: Dict[str, Plugin] = {}
        self._extension_points: Dict[
            str, List[Dict[str, Any]]
        ] = {}  # name -> [{plugin_id, handler, priority}]
        self.core_version = core_version
        self._initialized = False

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        logger.info("PluginManager initialized (core v%s)", self.core_version)

    async def shutdown(self) -> None:
        """Shutdown all plugins in reverse load order."""
        for plugin_id in reversed(list(self._plugins.keys())):
            try:
                await self.unload_plugin(plugin_id)
            except Exception as e:
                logger.warning("Error unloading plugin %s: %s", plugin_id, e)
        self._extension_points.clear()
        self._initialized = False
        logger.info("PluginManager shutdown")

    # ── Load / Unload / Reload ────────────────────────────────────────────

    async def load_plugin(
        self, plugin: Plugin, config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Load and initialize a plugin."""
        plugin_id = getattr(plugin, "id", None)
        if not plugin_id:
            raise PluginError("Plugin has no 'id' attribute")

        # Already loaded → unload first
        if plugin_id in self._plugins:
            await self.unload_plugin(plugin_id)

        # Validate config against schema
        config_schema = getattr(plugin, "config_schema", None)
        if config_schema and config:
            self._validate_config(config_schema, config)

        # Version compatibility
        self._check_version_compatibility(plugin)

        # Dependency resolution
        deps = getattr(plugin, "dependencies", None) or []
        for dep_id in deps:
            if dep_id not in self._plugins:
                raise PluginError(
                    f"Plugin '{plugin_id}' depends on '{dep_id}' which is not loaded"
                )

        # Initialize
        await plugin.initialize(config)

        # Register
        self._plugins[plugin_id] = plugin

        # Register extension points
        try:
            eps = plugin.get_extension_points()
        except Exception as e:
            logger.warning("Plugin %s get_extension_points() failed: %s", plugin_id, e)
            eps = []

        priority = getattr(plugin, "priority", 0)
        for ep in eps:
            self._register_extension_point(
                plugin_id=plugin_id,
                ep=ep,
                plugin_priority=priority,
            )

        logger.info("Plugin loaded: %s v%s", plugin_id, getattr(plugin, "version", "?"))

    async def unload_plugin(self, plugin_id: str) -> None:
        """Unload a plugin, checking for dependent plugins."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return

        # Check reverse dependencies
        for other_id, other in self._plugins.items():
            if other_id == plugin_id:
                continue
            other_deps = getattr(other, "dependencies", None) or []
            if plugin_id in other_deps:
                raise PluginError(
                    f"Cannot unload '{plugin_id}': plugin '{other_id}' depends on it"
                )

        # Shutdown
        try:
            await plugin.shutdown()
        except Exception as e:
            logger.warning("Plugin %s shutdown error: %s", plugin_id, e)

        # Remove extension points
        for name, handlers in list(self._extension_points.items()):
            filtered = [h for h in handlers if h["plugin_id"] != plugin_id]
            if filtered:
                self._extension_points[name] = filtered
            else:
                del self._extension_points[name]

        # Remove plugin
        del self._plugins[plugin_id]
        logger.info("Plugin unloaded: %s", plugin_id)

    async def reload_plugin(self, plugin_id: str, plugin: Plugin) -> None:
        """Reload a plugin with a new version."""
        await self.unload_plugin(plugin_id)
        await self.load_plugin(plugin)

    # ── Queries ───────────────────────────────────────────────────────────

    def list_plugins(self) -> List[Plugin]:
        return list(self._plugins.values())

    def get_plugin_metadata(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return None
        return {
            "id": getattr(plugin, "id", plugin_id),
            "name": getattr(plugin, "name", ""),
            "version": getattr(plugin, "version", ""),
            "description": getattr(plugin, "description", ""),
            "author": getattr(plugin, "author", ""),
            "homepage": getattr(plugin, "homepage", ""),
        }

    def is_loaded(self, plugin_id: str) -> bool:
        return plugin_id in self._plugins

    # ── Extension Point Invocation ────────────────────────────────────────

    async def invoke_extension_point(self, name: str, context: Any) -> List[Any]:
        """
        Invoke all handlers for an extension point.
        Handlers are sorted by priority (highest first).
        Errors from individual handlers are captured and returned as
        {error, plugin_id} dicts — remaining handlers continue.
        """
        handlers = self._extension_points.get(name, [])
        sorted_handlers = sorted(handlers, key=lambda h: h["priority"], reverse=True)

        results: List[Any] = []
        for h in sorted_handlers:
            plugin_id = h["plugin_id"]
            handler = h["handler"]
            try:
                result = await handler(context)
                results.append(result)
            except Exception as e:
                logger.warning(
                    "Extension point '%s' handler from '%s' failed: %s",
                    name,
                    plugin_id,
                    e,
                )
                results.append({"error": str(e), "plugin_id": plugin_id})

        return results

    # ── Private helpers ───────────────────────────────────────────────────

    def _register_extension_point(
        self,
        *,
        plugin_id: str,
        ep: ExtensionPoint,
        plugin_priority: int = 0,
    ) -> None:
        priority = ep.priority if ep.priority is not None else plugin_priority
        handlers = self._extension_points.setdefault(ep.name, [])
        handlers.append(
            {
                "plugin_id": plugin_id,
                "handler": ep.handler,
                "priority": priority,
            }
        )

    @staticmethod
    def _validate_config(schema: Dict[str, Any], config: Dict[str, Any]) -> None:
        required = schema.get("required")
        if required:
            for field in required:
                if field not in config:
                    raise PluginError(f"Missing required config field: {field}")

    def _check_version_compatibility(self, plugin: Plugin) -> None:
        current = self._parse_version(self.core_version)
        min_ver = getattr(plugin, "min_core_version", None)
        max_ver = getattr(plugin, "max_core_version", None)

        if min_ver:
            if self._compare_versions(current, self._parse_version(min_ver)) < 0:
                raise PluginError(
                    f"Plugin '{plugin.id}' requires core >= {min_ver}, "
                    f"but core is {self.core_version}"
                )

        if max_ver:
            if self._compare_versions(current, self._parse_version(max_ver)) > 0:
                raise PluginError(
                    f"Plugin '{plugin.id}' requires core <= {max_ver}, "
                    f"but core is {self.core_version}"
                )

    @staticmethod
    def _parse_version(version: str) -> List[int]:
        return [int(n) if n.isdigit() else 0 for n in version.split(".")]

    @staticmethod
    def _compare_versions(a: List[int], b: List[int]) -> int:
        for av, bv in zip(a, b):
            if av != bv:
                return av - bv
        return len(a) - len(b)


# ── Singleton (optional) ───────────────────────────────────────────────────

_DEFAULT_MANAGER: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Return the default global PluginManager instance."""
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = PluginManager()
    return _DEFAULT_MANAGER


def set_plugin_manager(manager: PluginManager) -> None:
    global _DEFAULT_MANAGER
    _DEFAULT_MANAGER = manager
