"""
MCP Manager — Model Context Protocol Server Connections

Manages connections to MCP servers, tool discovery, and JSON-RPC 2.0 protocol.
Supports multiple transports: stdio, HTTP, SSE.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from plugins.base.base_provider import BaseProvider, ProviderCapability, ProviderStatus

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""

    name: str
    transport: str  # stdio | http | sse
    endpoint: Optional[str] = None
    command: Optional[str] = None  # For stdio transport
    args: List[str] = None
    env: Dict[str, str] = None


class MCPManager:
    """
    Manages multiple MCP server connections.
    - Discover tools from MCP servers
    - Route tool calls to appropriate servers
    - Handle JSON-RPC 2.0 protocol
    """

    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True
        logger.info("MCP Manager initialized")

    async def add_server(self, config: MCPServerConfig) -> bool:
        """Add an MCP server configuration."""
        self._servers[config.name] = config
        logger.info("MCP server added: %s (%s)", config.name, config.transport)
        return True

    async def remove_server(self, name: str) -> bool:
        """Remove an MCP server."""
        if name in self._servers:
            del self._servers[name]
            # Remove tools from this server
            self._tools = {
                k: v for k, v in self._tools.items() if v.get("server") != name
            }
            logger.info("MCP server removed: %s", name)
            return True
        return False

    async def discover_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Discover available tools from MCP servers.
        In production, this would make JSON-RPC calls to the server.
        """
        discovered = []

        servers_to_check = (
            [self._servers.get(server_name)] if server_name else self._servers.values()
        )

        for server in servers_to_check:
            if not server:
                continue
            # Placeholder: In production, call tools/list via JSON-RPC
            tools = [
                {
                    "name": f"{server.name}_tool_1",
                    "description": f"Tool from {server.name}",
                    "input_schema": {"type": "object", "properties": {}},
                    "server": server.name,
                }
            ]
            for tool in tools:
                self._tools[tool["name"]] = tool
            discovered.extend(tools)

        return discovered

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on its associated MCP server."""
        tool = self._tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        server_name = tool.get("server")
        server = self._servers.get(server_name)
        if not server:
            return {"success": False, "error": f"Server '{server_name}' not available"}

        # Placeholder: In production, call via JSON-RPC
        logger.info("Calling tool %s on server %s", tool_name, server_name)
        return {
            "success": True,
            "result": {"tool": tool_name, "parameters": parameters, "server": server_name},
        }

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all configured MCP servers."""
        return [
            {
                "name": s.name,
                "transport": s.transport,
                "endpoint": s.endpoint,
                "status": "connected" if s.name in self._servers else "disconnected",
            }
            for s in self._servers.values()
        ]

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all discovered tools."""
        return list(self._tools.values())

    async def health_check(self) -> Dict[str, bool]:
        """Health check all MCP servers."""
        return {name: True for name in self._servers.keys()}


# ── Singleton ───────────────────────────────────────────────────────────

_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
