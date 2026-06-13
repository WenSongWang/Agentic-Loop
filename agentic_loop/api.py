from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable
from typing import Any

from agentic_loop.config import RunConfig
from agentic_loop.llm.openai_compat import OpenAICompatClient
from agentic_loop.loop import LoopEvent, query_loop, terminal_from_event
from agentic_loop.observability.journal import RunJournal
from agentic_loop.terminal import Terminal
from agentic_loop.tools.registry import build_default_registry


async def execute_run(
    prompt: str,
    *,
    config: RunConfig,
    system_prompt: str | None = None,
    on_event: Callable[[LoopEvent], None] | None = None,
) -> tuple[Terminal, RunJournal]:
    if config.dry_run:
        journal = RunJournal(config.runs_dir, run_id="dry-run")
        terminal = Terminal.completed(
            f"[dry-run] Would run with model={config.model}, tools={build_default_registry(cwd=config.cwd, allow_bash=config.allow_bash).list_names()}, stream={config.stream}",
            turns=0,
        )
        return terminal, journal

    config.require_api_key()
    journal = RunJournal(config.runs_dir)
    started = time.perf_counter()

    journal.started(
        prompt=prompt,
        config={
            "model": config.model,
            "cwd": str(config.cwd),
            "max_turns": config.max_turns,
            "allow_bash": config.allow_bash,
            "stream": config.stream,
        },
    )

    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    llm = OpenAICompatClient(
        api_key=config.api_key or "",
        base_url=config.base_url,
        model=config.model,
        max_retries=config.max_retries,
    )
    tools = build_default_registry(cwd=config.cwd, allow_bash=config.allow_bash)

    terminal: Terminal | None = None
    async for event in query_loop(
        messages,
        tools=tools,
        llm=llm,
        max_turns=config.max_turns,
        journal=journal,
        stream=config.stream,
        tool_timeout=config.tool_timeout,
    ):
        if on_event:
            on_event(event)
        if event.kind == "terminal":
            terminal = terminal_from_event(event.data)

    if terminal is None:
        terminal = Terminal.failed("Run ended without terminal event", turns=0)

    journal.finished(
        terminal=terminal.to_dict(),
        duration_ms=(time.perf_counter() - started) * 1000,
    )
    return terminal, journal


async def iter_run(
    prompt: str,
    *,
    config: RunConfig,
    system_prompt: str | None = None,
) -> AsyncIterator[LoopEvent]:
    """Public API: stream loop events for integrations."""
    if config.dry_run:
        yield LoopEvent(
            kind="terminal",
            data=Terminal.completed("[dry-run]", turns=0).to_dict(),
        )
        return

    config.require_api_key()
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    llm = OpenAICompatClient(
        api_key=config.api_key or "",
        base_url=config.base_url,
        model=config.model,
        max_retries=config.max_retries,
    )
    tools = build_default_registry(cwd=config.cwd, allow_bash=config.allow_bash)

    async for event in query_loop(
        messages,
        tools=tools,
        llm=llm,
        max_turns=config.max_turns,
        stream=config.stream,
        tool_timeout=config.tool_timeout,
    ):
        yield event
