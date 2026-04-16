"""
MCP Tool Registry — Agent World

Central registry of all tools agents can call.
Add new MCP-compatible tools here by registering them.

Each tool has:
  - schema:  OpenAI function-calling JSON schema
  - fn:      async callable that executes the tool
"""

import logging
from typing import Dict, Optional, Callable, Any

_REGISTRY: Dict[str, Dict] = {}


def register_tool(name: str, description: str, parameters: dict, fn: Callable):
    """Register a callable tool in the global registry."""
    _REGISTRY[name] = {
        "schema": {
            "name":        name,
            "description": description,
            "parameters":  parameters,
        },
        "fn": fn,
    }


def get_tool(name: str) -> Optional[Dict]:
    """Return tool dict with 'schema' and 'fn', or None."""
    return _REGISTRY.get(name)


def list_tools() -> Dict[str, Dict]:
    """Return all registered tools."""
    return _REGISTRY


def get_schemas_for_capabilities(capabilities: list) -> list:
    """Return OpenAI-style tool schemas for a list of capability names."""
    schemas = []
    for cap in capabilities:
        tool = _REGISTRY.get(cap)
        if tool:
            schemas.append(tool["schema"])
    return schemas


def get_all_schemas() -> list:
    """Return all registered tool schemas."""
    return [t["schema"] for t in _REGISTRY.values()]


# ------------------------------------------------------------------ #
# Auto-load all built-in tools on import                              #
# ------------------------------------------------------------------ #

def _load_builtin_tools():
    from tools.web_search  import web_search
    from tools.http_tool   import http_request
    from tools.file_tool   import read_file, write_file
    from tools.memory_tool import save_memory, load_memory
    from tools.room_tool   import broadcast_to_room
    
    # Import and register new agent tools
    from tools.merchant_tools import register_merchant_tools
    from tools.promoter_tools import register_promoter_tools
    from tools.growth_tools import register_growth_tools

    register_tool(
        name="web_search",
        description="Search the web for current information using DuckDuckGo. Returns titles, snippets, and URLs.",
        parameters={
            "type": "object",
            "properties": {
                "query":       {"type": "string",  "description": "The search query"},
                "max_results": {"type": "integer", "description": "Max results to return (default 5)", "default": 5},
            },
            "required": ["query"],
        },
        fn=web_search,
    )

    register_tool(
        name="http_request",
        description="Make an HTTP request to any REST API. Use this to interact with Etsy, Shopify, or any external service.",
        parameters={
            "type": "object",
            "properties": {
                "url":     {"type": "string", "description": "Full URL to call"},
                "method":  {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE", "default": "GET"},
                "headers": {"type": "object", "description": "Optional request headers"},
                "body":    {"type": "object", "description": "Optional JSON body for POST/PUT"},
            },
            "required": ["url"],
        },
        fn=http_request,
    )

    register_tool(
        name="read_file",
        description="Read the contents of a file in the project workspace.",
        parameters={
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename to read (relative to project workspace)"},
            },
            "required": ["filename"],
        },
        fn=read_file,
    )

    register_tool(
        name="write_file",
        description="Write or append content to a file in the project workspace.",
        parameters={
            "type": "object",
            "properties": {
                "filename": {"type": "string",  "description": "Filename to write"},
                "content":  {"type": "string",  "description": "Content to write"},
                "append":   {"type": "boolean", "description": "If true, append instead of overwrite", "default": False},
            },
            "required": ["filename", "content"],
        },
        fn=write_file,
    )

    register_tool(
        name="save_memory",
        description="Save a piece of information to your long-term memory so you can recall it in future sessions.",
        parameters={
            "type": "object",
            "properties": {
                "key":         {"type": "string", "description": "Memory key (unique identifier)"},
                "value":       {"type": "string", "description": "Value to remember"},
                "memory_type": {"type": "string", "description": "short_term | long_term | episodic", "default": "long_term"},
            },
            "required": ["key", "value"],
        },
        fn=save_memory,
    )

    register_tool(
        name="load_memory",
        description="Recall a piece of information you previously saved to memory.",
        parameters={
            "type": "object",
            "properties": {
                "key":         {"type": "string", "description": "Memory key to retrieve"},
                "memory_type": {"type": "string", "description": "short_term | long_term | episodic", "default": "long_term"},
            },
            "required": ["key"],
        },
        fn=load_memory,
    )

    register_tool(
        name="broadcast_to_room",
        description="Post a message to the room so all agents and the dashboard can see your progress or findings.",
        parameters={
            "type": "object",
            "properties": {
                "message":      {"type": "string", "description": "Message to broadcast"},
                "message_type": {"type": "string", "description": "info | update | alert | completed", "default": "info"},
            },
            "required": ["message"],
        },
        fn=broadcast_to_room,
    )
    
    # Register Merchant, Promoter, and Growth agent tools
    register_merchant_tools()
    register_promoter_tools()
    register_growth_tools()
    
    logger = logging.getLogger(__name__)
    logger.info(f"[MCP Registry] Loaded {len(_REGISTRY)} tools total")


_load_builtin_tools()
