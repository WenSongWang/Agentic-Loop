from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from agentic_loop.llm.client import LLMClient, LLMResponse, ToolCall
from agentic_loop.observability.journal import RunJournal
from agentic_loop.state import LoopState
from agentic_loop.terminal import Terminal, TerminalKind
from agentic_loop.tools.registry import ToolRegistry

TRUNCATION_NUDGE = (
    "Your previous response was truncated due to output length limits. "
    "Continue directly from where you stopped. Do not repeat earlier content."
)


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


def terminal_from_event(data: dict[str, Any]) -> Terminal:
    return Terminal(
        kind=TerminalKind(data["kind"]),
        content=data.get("content"),
        error=data.get("error"),
        turns=data.get("turns", 0),
    )


async def _call_llm(
    llm: LLMClient,
    messages: list[dict[str, Any]],
    *,
    tools: ToolRegistry,
    stream: bool,
) -> tuple[LLMResponse, list[str]]:
    deltas: list[str] = []
    if stream and hasattr(llm, "stream_chat"):
        response: LLMResponse | None = None
        async for chunk in llm.stream_chat(messages, tools=tools.schemas()):
            if chunk.kind == "text_delta" and chunk.text:
                deltas.append(chunk.text)
            elif chunk.kind == "done" and chunk.response:
                response = chunk.response
        if response is None:
            raise RuntimeError("Stream ended without a final response")
        return response, deltas

    response = await llm.chat(messages, tools=tools.schemas())
    if response.content:
        deltas.append(response.content)
    return response, deltas


async def _execute_tools_parallel(
    calls: list[ToolCall],
    *,
    tools: ToolRegistry,
    turn: int,
    journal: RunJournal | None,
    abort: AbortSignal | None,
    tool_timeout: float,
) -> list[tuple[ToolCall, str]] | Terminal:
    async def _one(call: ToolCall) -> tuple[ToolCall, str]:
        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                tools.execute(call.name, call.arguments),
                timeout=tool_timeout,
            )
        except asyncio.TimeoutError:
            result = f"Error: tool '{call.name}' timed out after {tool_timeout}s"
        duration_ms = (time.perf_counter() - started) * 1000
        if journal:
            journal.tool_result(
                turn=turn,
                name=call.name,
                duration_ms=duration_ms,
                preview=result,
            )
        return call, result

    if abort and abort.is_set():
        return Terminal.aborted(turns=turn)

    return await asyncio.gather(*[_one(call) for call in calls])


async def query_loop(
    messages: list[dict[str, Any]],
    *,
    tools: ToolRegistry,
    llm: LLMClient,
    max_turns: int = 20,
    journal: RunJournal | None = None,
    abort: AbortSignal | None = None,
    stream: bool = True,
    tool_timeout: float = 120.0,
    max_truncation_retries: int = 2,
) -> AsyncIterator[LoopEvent]:
    state = LoopState(messages=list(messages))

    for turn in range(1, max_turns + 1):
        if abort and abort.is_set():
            yield LoopEvent(kind="terminal", data=Terminal.aborted(turns=turn - 1).to_dict())
            return

        yield LoopEvent(kind="turn_start", data={"turn": turn})

        truncation_attempts = 0
        while True:
            try:
                response, deltas = await _call_llm(
                    llm,
                    state.messages,
                    tools=tools,
                    stream=stream,
                )
            except Exception as exc:  # noqa: BLE001
                yield LoopEvent(
                    kind="terminal",
                    data=Terminal.model_error(str(exc), turns=turn - 1).to_dict(),
                )
                return

            for delta in deltas:
                if stream and delta:
                    yield LoopEvent(kind="assistant_delta", data={"turn": turn, "text": delta})

            if response.finish_reason == "length" and truncation_attempts < max_truncation_retries:
                truncation_attempts += 1
                state = state.with_messages(
                    [
                        *state.messages,
                        {"role": "system", "content": TRUNCATION_NUDGE},
                    ]
                )
                continue
            break

        state = state.with_messages([*state.messages, response.raw_message])

        if not response.tool_calls:
            if journal:
                journal.turn(turn=turn, tool_names=[])
            terminal = Terminal.completed(response.content, turns=turn)
            yield LoopEvent(kind="terminal", data=terminal.to_dict())
            return

        tool_names = [call.name for call in response.tool_calls]
        if journal:
            journal.turn(turn=turn, tool_names=tool_names)

        tool_outcome = await _execute_tools_parallel(
            response.tool_calls,
            tools=tools,
            turn=turn,
            journal=journal,
            abort=abort,
            tool_timeout=tool_timeout,
        )
        if isinstance(tool_outcome, Terminal):
            yield LoopEvent(kind="terminal", data=tool_outcome.to_dict())
            return

        for call, result in tool_outcome:
            yield LoopEvent(
                kind="tool_result",
                data={"turn": turn, "tool": call.name, "preview": result[:500]},
            )
            state = state.with_messages([*state.messages, _tool_result_message(call, result)])

        state = state.next_turn(state.messages)

    last_content = None
    for msg in reversed(state.messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            last_content = msg["content"]
            break
    yield LoopEvent(
        kind="terminal",
        data=Terminal.max_turns(turns=max_turns, last_content=last_content).to_dict(),
    )


async def run_loop(
    messages: list[dict[str, Any]],
    *,
    tools: ToolRegistry,
    llm: LLMClient,
    max_turns: int = 20,
    journal: RunJournal | None = None,
    abort: AbortSignal | None = None,
    stream: bool = False,
    tool_timeout: float = 120.0,
) -> Terminal:
    async for event in query_loop(
        messages,
        tools=tools,
        llm=llm,
        max_turns=max_turns,
        journal=journal,
        abort=abort,
        stream=stream,
        tool_timeout=tool_timeout,
    ):
        if event.kind == "terminal":
            return terminal_from_event(event.data)
    return Terminal.failed("Loop ended without terminal event", turns=0)
