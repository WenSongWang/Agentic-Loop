"""Example MCP bridge — register MCP server tools into ToolRegistry."""

from __future__ import annotations

import asyncio
import os
import sys

from agentic_loop.config import RunConfig
from agentic_loop.connectors.mcp import MCPConnector, MCPServerConfig
from agentic_loop.llm.openai_compat import OpenAICompatClient
from agentic_loop.loop import run_loop
from agentic_loop.tools.mcp_bridge import register_mcp_tools
from agentic_loop.tools.registry import build_default_registry


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python demo.py <prompt>")
        print("Env: MCP_COMMAND, MCP_ARGS (JSON array optional)")
        raise SystemExit(1)

    command = os.getenv("MCP_COMMAND", "npx")
    args_env = os.getenv("MCP_ARGS", '["-y", "@modelcontextprotocol/server-everything"]')
    import json

    args = json.loads(args_env)
    prompt = sys.argv[1]

    config = RunConfig.from_env(overrides={"dry_run": os.getenv("DRY_RUN") == "1"})
    if config.dry_run:
        print("[dry-run] Would connect MCP and run:", prompt)
        return

    config.require_api_key()
    mcp_config = MCPServerConfig(command=command, args=args)

    async with MCPConnector(mcp_config) as connector:
        tools = build_default_registry(cwd=config.cwd, allow_bash=False)
        names = await register_mcp_tools(tools, connector, prefix="mcp")
        print("Registered MCP tools:", names)

        llm = OpenAICompatClient(
            api_key=config.api_key or "",
            base_url=config.base_url,
            model=config.model,
        )
        terminal = await run_loop(
            [{"role": "user", "content": prompt}],
            tools=tools,
            llm=llm,
            max_turns=config.max_turns,
            stream=False,
        )
        print(terminal.kind.value, terminal.content or terminal.error)


if __name__ == "__main__":
    asyncio.run(main())
