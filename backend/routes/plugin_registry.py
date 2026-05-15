"""
Plugin Registry Routes
API endpoints for provider discovery and health status.
Used by the frontend ProviderStatusPanel component.
"""

from fastapi import APIRouter
from typing import Optional

from plugins.plugin_loader import PluginLoader
from plugins.base.plugin_registry import PluginRegistry

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("/registry", response_model=dict)
async def list_registered_plugins():
    """List all registered providers with their status."""
    registry = PluginLoader.get_registry()
    status = registry.get_status()
    names = registry.get_provider_names()

    providers = []
    for name in names:
        provider = registry.get_provider(name)
        if provider:
            capability = provider.get_capability()
            providers.append({
                "name": provider.name,
                "provider_type": provider.provider_type,
                "version": provider.version,
                "status": provider.status.value,
                "required_credentials": capability.required_credentials,
                "error_message": provider._error_message,
            })

    return {
        "providers": providers,
        "total": status["total"],
        "active": status["active"],
        "failed": status["failed"],
    }


@router.get("/registry/{name}/health", response_model=dict)
async def check_provider_health(name: str):
    """Check health of a specific provider."""
    registry = PluginLoader.get_registry()
    provider = registry.get_provider(name)

    if not provider:
        return {"success": False, "error": f"Provider '{name}' not found"}

    healthy = await provider.health_check()
    return {
        "success": True,
        "provider": name,
        "healthy": healthy,
        "status": provider.status.value,
    }


@router.post("/reload", response_model=dict)
async def reload_all_plugins():
    """Reload all plugins from disk."""
    PluginLoader.reset_registry()
    registry = PluginLoader.load_all_plugins()
    status = registry.get_status()

    return {
        "success": True,
        "message": "Plugins reloaded",
        "total": status["total"],
        "active": status["active"],
        "failed": status["failed"],
    }


@router.get("/types", response_model=dict)
async def list_provider_types():
    """List all provider types and their counts."""
    registry = PluginLoader.get_registry()
    types = ["image_gen", "video_gen", "communication", "business", "tools"]

    result = {}
    for t in types:
        providers = registry.get_providers_by_type(t)
        result[t] = [p.name for p in providers]

    return {"types": result}
