from __future__ import annotations

import time
from typing import Any

from agentic_loop.config import RunConfig
from agentic_loop.llm.openai_compat import OpenAICompatClient
from agentic_loop.loop import run_loop
from agentic_loop.observability.journal import RunJournal
from agentic_loop.terminal import Terminal
from agentic_loop.tools.registry import build_default_registry


async def execute_run(
    prompt: str,
    *,
    config: RunConfig,
    system_prompt: str | None = None,
) -> tuple[Terminal, RunJournal]:
    if config.dry_run:
        journal = RunJournal(config.runs_dir, run_id="dry-run")
        terminal = Terminal.completed(
            f"[dry-run] Would run with model={config.model}, tools={build_default_registry(cwd=config.cwd, allow_bash=config.allow_bash).list_names()}",
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
    )
    tools = build_default_registry(cwd=config.cwd, allow_bash=config.allow_bash)

    terminal = await run_loop(
        messages,
        tools=tools,
        llm=llm,
        max_turns=config.max_turns,
        journal=journal,
    )

    journal.finished(
        terminal=terminal.to_dict(),
        duration_ms=(time.perf_counter() - started) * 1000,
    )
    return terminal, journal
