# MCP Bridge Example

Connect an MCP server and expose its tools to the agent loop.

## Install

```powershell
pip install -e ".[mcp]"
```

## Dry-run

```powershell
set DRY_RUN=1
python examples/mcp-bridge/demo.py "List available MCP tools"
```

## Real run (requires MCP server + API key)

```powershell
set MCP_COMMAND=npx
set MCP_ARGS=["-y","@modelcontextprotocol/server-everything"]
python examples/mcp-bridge/demo.py "Use MCP tools to answer a simple question"
```

See `agentic_loop/connectors/mcp.py` and `agentic_loop/tools/mcp_bridge.py`.
