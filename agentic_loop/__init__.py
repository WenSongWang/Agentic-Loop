"""Agentic Loop — lightweight Loop Engineering orchestrator."""

from agentic_loop.api import execute_run, iter_run
from agentic_loop.config import RunConfig
from agentic_loop.connectors.base import ConnectorRegistry, ConnectorResult
from agentic_loop.loop import query_loop, run_loop
from agentic_loop.orchestration.orchestrator import Orchestrator
from agentic_loop.terminal import Terminal, TerminalKind
from agentic_loop.tools.registry import ToolRegistry, build_default_registry

__all__ = [
    "ConnectorRegistry",
    "ConnectorResult",
    "Orchestrator",
    "RunConfig",
    "Terminal",
    "TerminalKind",
    "ToolRegistry",
    "build_default_registry",
    "execute_run",
    "iter_run",
    "query_loop",
    "run_loop",
]

__version__ = "0.2.0"
