from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agentic_loop.connectors.base import ConnectorResult


@dataclass
class MCPServerConfig:
    """Stdio MCP server launch configuration."""

    command: str
    args: list[str]
    env: dict[str, str] | None = None


class MCPConnector:
    """
    Minimal MCP client wrapper (stdio transport).

    Requires optional dependency: pip install agentic-loop[mcp]
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._session = None
        self._context = None

    async def __aenter__(self) -> MCPConnector:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise ImportError(
                "MCP support requires: pip install agentic-loop[mcp]"
            ) from exc

        params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env,
        )
        self._context = stdio_client(params)
        read, write = await self._context.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._session is not None:
            await self._session.__aexit__(*args)
        if self._context is not None:
            await self._context.__aexit__(*args)

    async def list_tools(self) -> list[dict[str, Any]]:
        assert self._session is not None
        result = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema,
            }
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ConnectorResult:
        assert self._session is not None
        try:
            result = await self._session.call_tool(name, arguments)
            text_parts = [
                item.text
                for item in result.content
                if hasattr(item, "text") and item.text
            ]
            message = "\n".join(text_parts) if text_parts else json.dumps(
                [item.model_dump() if hasattr(item, "model_dump") else str(item) for item in result.content],
                ensure_ascii=False,
            )
            return ConnectorResult(ok=not result.isError, message=message)
        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(ok=False, message=str(exc))

    async def invoke(self, action: str, **params: Any) -> ConnectorResult:
        if action == "list_tools":
            tools = await self.list_tools()
            return ConnectorResult(ok=True, message=f"{len(tools)} tools", data={"tools": tools})
        if action == "call_tool":
            name = str(params.get("name", ""))
            arguments = params.get("arguments") or {}
            if not name:
                return ConnectorResult(ok=False, message="Missing tool name")
            if not isinstance(arguments, dict):
                return ConnectorResult(ok=False, message="arguments must be an object")
            return await self.call_tool(name, arguments)
        return ConnectorResult(ok=False, message=f"Unknown MCP action '{action}'")
