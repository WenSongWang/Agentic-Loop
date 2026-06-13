from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from agentic_loop.llm.client import LLMClient, ToolCall
from agentic_loop.observability.journal import RunJournal
from agentic_loop.state import LoopState
from agentic_loop.terminal import Terminal, TerminalKind
from agentic_loop.tools.registry import ToolRegistry


@dataclass
class LoopEvent:
    kind: str
    data: dict[str, Any]


@runtime_checkable
class AbortSignal(Protocol):
    def is_set(self) -> bool: ...


def _tool_result_message(call: ToolCall, content: str) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": call.id,
        "content": content,
    }


async def run_loop(
    messages: list[dict[str, Any]],
    *,
    tools: ToolRegistry,
    llm: LLMClient,
    max_turns: int = 20,
    journal: RunJournal | None = None,
    abort: AbortSignal | None = None,
) -> Terminal:
    state = LoopState(messages=list(messages))

    for turn in range(1, max_turns + 1):
        if abort and abort.is_set():
            return Terminal.aborted(turns=turn - 1)

        try:
            response = await llm.chat(state.messages, tools=tools.schemas())
        except Exception as exc:  # noqa: BLE001
            return Terminal.model_error(str(exc), turns=turn - 1)

        state = state.with_messages([*state.messages, response.raw_message])

        if not response.tool_calls:
            if journal:
                journal.turn(turn=turn, tool_names=[])
            return Terminal.completed(response.content, turns=turn)

        tool_names = [call.name for call in response.tool_calls]
        if journal:
            journal.turn(turn=turn, tool_names=tool_names)

        for call in response.tool_calls:
            if abort and abort.is_set():
                return Terminal.aborted(turns=turn)

            started = time.perf_counter()
            result = await tools.execute(call.name, call.arguments)
            duration_ms = (time.perf_counter() - started) * 1000
            if journal:
                journal.tool_result(
                    turn=turn,
                    name=call.name,
                    duration_ms=duration_ms,
                    preview=result,
                )
            state = state.with_messages([*state.messages, _tool_result_message(call, result)])

        state = state.next_turn(state.messages)

    last_content = None
    for msg in reversed(state.messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            last_content = msg["content"]
            break
    return Terminal.max_turns(turns=max_turns, last_content=last_content)


async def query_loop(
    messages: list[dict[str, Any]],
    *,
    tools: ToolRegistry,
    llm: LLMClient,
    max_turns: int = 20,
    journal: RunJournal | None = None,
    abort: AbortSignal | None = None,
) -> AsyncIterator[LoopEvent]:
    """Async generator wrapper; Phase 2 will stream deltas inline."""
    terminal = await run_loop(
        messages,
        tools=tools,
        llm=llm,
        max_turns=max_turns,
        journal=journal,
        abort=abort,
    )
    yield LoopEvent(kind="terminal", data=terminal.to_dict())
