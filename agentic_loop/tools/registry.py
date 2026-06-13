from __future__ import annotations

import asyncio
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from agentic_loop.llm.openai_compat import parse_tool_arguments

ToolHandler = Callable[[dict[str, Any]], Awaitable[str] | str]


@dataclass
class RegisteredTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    requires_bash: bool = False


class ToolRegistry:
    def __init__(self, *, cwd: Path, allow_bash: bool = False) -> None:
        self.cwd = cwd.resolve()
        self.allow_bash = allow_bash
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: ToolHandler,
        *,
        requires_bash: bool = False,
    ) -> None:
        self._tools[name] = RegisteredTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            requires_bash=requires_bash,
        )

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    async def execute(self, name: str, arguments: str) -> str:
        if name not in self._tools:
            return f"Error: unknown tool '{name}'"

        tool = self._tools[name]
        if tool.requires_bash and not self.allow_bash:
            return "Error: bash tool disabled. Re-run with --allow-bash."

        try:
            args = parse_tool_arguments(arguments)
        except ValueError as exc:
            return f"Error: {exc}"

        try:
            result = tool.handler(args)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        except Exception as exc:  # noqa: BLE001 - tool errors become observations
            return f"Error: {exc}"

    def list_names(self) -> list[str]:
        return sorted(self._tools.keys())


def _resolve_path(cwd: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = cwd / path
    resolved = path.resolve()
    if cwd not in resolved.parents and resolved != cwd:
        raise ValueError(f"Path escapes workspace: {raw}")
    return resolved


async def read_file_handler(cwd: Path, args: dict[str, Any]) -> str:
    path = _resolve_path(cwd, str(args["path"]))
    if not path.is_file():
        return f"Error: file not found: {path}"
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


async def write_file_handler(cwd: Path, args: dict[str, Any]) -> str:
    path = _resolve_path(cwd, str(args["path"]))
    content = str(args.get("content", ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path.relative_to(cwd)}"


async def grep_handler(cwd: Path, args: dict[str, Any]) -> str:
    pattern = str(args["pattern"])
    root = _resolve_path(cwd, str(args.get("path", ".")))
    if root.is_file():
        targets = [root]
    else:
        targets = [p for p in root.rglob("*") if p.is_file()]

    regex = re.compile(pattern)
    matches: list[str] = []
    for file_path in targets:
        if ".venv" in file_path.parts or ".git" in file_path.parts:
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                rel = file_path.relative_to(cwd)
                matches.append(f"{rel}:{idx}:{line[:200]}")
                if len(matches) >= 100:
                    return "\n".join(matches) + "\n...(truncated at 100 matches)"

    if not matches:
        return "No matches found."
    return "\n".join(matches)


async def bash_handler(cwd: Path, args: dict[str, Any]) -> str:
    command = str(args["command"])
    timeout = float(args.get("timeout", 60))
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return f"Error: timeout after {timeout}s"

    parts: list[str] = []
    if stdout:
        parts.append(stdout.decode("utf-8", errors="replace"))
    if stderr:
        parts.append(stderr.decode("utf-8", errors="replace"))
    if proc.returncode not in (0, None):
        parts.append(f"exit code: {proc.returncode}")
    return "\n".join(parts).strip() or "(no output)"


def build_default_registry(*, cwd: Path, allow_bash: bool = False) -> ToolRegistry:
    registry = ToolRegistry(cwd=cwd, allow_bash=allow_bash)

    registry.register(
        "read_file",
        "Read a UTF-8 text file relative to the workspace.",
        {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
        lambda args: read_file_handler(cwd, args),
    )
    registry.register(
        "write_file",
        "Write content to a file relative to the workspace.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        lambda args: write_file_handler(cwd, args),
    )
    registry.register(
        "grep",
        "Search file contents under a path using a regex pattern.",
        {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "File or directory", "default": "."},
            },
            "required": ["pattern"],
        },
        lambda args: grep_handler(cwd, args),
    )
    registry.register(
        "bash",
        "Run a shell command in the workspace directory.",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "number", "default": 60},
            },
            "required": ["command"],
        },
        lambda args: bash_handler(cwd, args),
        requires_bash=True,
    )
    return registry
