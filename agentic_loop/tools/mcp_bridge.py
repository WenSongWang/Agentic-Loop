from __future__ import annotations

from typing import Any

from agentic_loop.connectors.mcp import MCPConnector, MCPServerConfig
from agentic_loop.tools.registry import ToolRegistry


async def register_mcp_tools(
    registry: ToolRegistry,
    connector: MCPConnector,
    *,
    prefix: str = "mcp",
) -> list[str]:
    """Register MCP server tools into a ToolRegistry with optional name prefix."""
    tools = await connector.list_tools()
    registered: list[str] = []

    for spec in tools:
        name = spec["name"]
        tool_name = f"{prefix}_{name}" if prefix else name
        schema = spec.get("inputSchema") or {"type": "object", "properties": {}}

        async def handler(args: dict[str, Any], *, _tool=name) -> str:
            result = await connector.call_tool(_tool, args)
            return result.message if result.ok else f"Error: {result.message}"

        registry.register(
            tool_name,
            spec.get("description") or f"MCP tool {name}",
            schema,
            handler,
        )
        registered.append(tool_name)

    return registered
