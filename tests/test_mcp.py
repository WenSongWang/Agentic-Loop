from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_loop.connectors.base import ConnectorResult
from agentic_loop.connectors.mcp import MCPConnector, MCPServerConfig


@pytest.mark.asyncio
async def test_mcp_invoke_unknown_action() -> None:
    connector = MCPConnector(MCPServerConfig(command="echo", args=["hi"]))
    connector._session = MagicMock()
    result = await connector.invoke("unknown")
    assert result.ok is False


@pytest.mark.asyncio
async def test_mcp_call_tool_success() -> None:
    connector = MCPConnector(MCPServerConfig(command="echo", args=["hi"]))
    mock_content = MagicMock()
    mock_content.text = "tool output"
    mock_result = MagicMock()
    mock_result.isError = False
    mock_result.content = [mock_content]
    connector._session = MagicMock()
    connector._session.call_tool = AsyncMock(return_value=mock_result)

    result = await connector.call_tool("demo", {"x": 1})
    assert result.ok is True
    assert "tool output" in result.message


@pytest.mark.asyncio
async def test_register_mcp_tools(tmp_path) -> None:
    from agentic_loop.tools.mcp_bridge import register_mcp_tools
    from agentic_loop.tools.registry import build_default_registry

    connector = MCPConnector(MCPServerConfig(command="echo", args=[]))
    connector.list_tools = AsyncMock(
        return_value=[
            {
                "name": "search",
                "description": "search docs",
                "inputSchema": {
                    "type": "object",
                    "properties": {"q": {"type": "string"}},
                    "required": ["q"],
                },
            }
        ]
    )
    connector.call_tool = AsyncMock(return_value=ConnectorResult(ok=True, message="ok"))

    registry = build_default_registry(cwd=tmp_path)
    names = await register_mcp_tools(registry, connector, prefix="mcp")
    assert names == ["mcp_search"]
    result = await registry.execute("mcp_search", '{"q": "hello"}')
    assert result == "ok"
