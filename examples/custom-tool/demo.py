"""Example: register a custom tool and connector for secondary development."""

from __future__ import annotations

import asyncio

from agentic_loop import ConnectorRegistry, ConnectorResult, Orchestrator, RunConfig
from agentic_loop.tools.registry import ToolRegistry, build_default_registry


async def ping_connector(*, action: str, **params) -> ConnectorResult:
    if action != "ping":
        return ConnectorResult(ok=False, message=f"Unknown action {action}")
    return ConnectorResult(ok=True, message="pong", data={"echo": params.get("message", "")})


async def main() -> None:
    connectors = ConnectorRegistry()
    connectors.register("demo", ping_connector)
    result = await connectors.invoke("demo", "ping", message="hello")
    print(result)

    config = RunConfig(dry_run=True)
    orch = Orchestrator(config)
    terminal, run_id = await orch.run("custom tool demo")
    print(run_id, terminal.kind.value)


if __name__ == "__main__":
    asyncio.run(main())
