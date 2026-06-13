from __future__ import annotations

import asyncio
from typing import Any

import pytest

from agentic_loop.abort import AbortController
from agentic_loop.llm.client import LLMResponse, StreamChunk, ToolCall
from agentic_loop.loop import query_loop, run_loop
from agentic_loop.terminal import TerminalKind
from agentic_loop.tools.registry import build_default_registry


class MockLLM:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        self.calls += 1
        if not self._responses:
            raise RuntimeError("No mock responses left")
        return self._responses.pop(0)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ):
        response = await self.chat(messages, tools=tools)
        if response.content:
            yield StreamChunk(kind="text_delta", text=response.content)
        yield StreamChunk(kind="done", response=response)


@pytest.mark.asyncio
async def test_run_loop_completes_without_tools(tmp_path) -> None:
    llm = MockLLM([LLMResponse(content="done", tool_calls=[], raw_message={"role": "assistant", "content": "done"})])
    tools = build_default_registry(cwd=tmp_path)

    terminal = await run_loop(
        [{"role": "user", "content": "hi"}],
        tools=tools,
        llm=llm,
        max_turns=5,
        stream=False,
    )

    assert terminal.kind == TerminalKind.COMPLETED
    assert terminal.content == "done"
    assert terminal.turns == 1


@pytest.mark.asyncio
async def test_run_loop_executes_tool_then_completes(tmp_path) -> None:
    read_call = ToolCall(id="call_1", name="read_file", arguments='{"path": "hello.txt"}')
    (tmp_path / "hello.txt").write_text("world", encoding="utf-8")

    llm = MockLLM(
        [
            LLMResponse(
                content=None,
                tool_calls=[read_call],
                raw_message={
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "read_file", "arguments": '{"path": "hello.txt"}'},
                        }
                    ],
                },
            ),
            LLMResponse(content="found world", tool_calls=[], raw_message={"role": "assistant", "content": "found world"}),
        ]
    )
    tools = build_default_registry(cwd=tmp_path)

    terminal = await run_loop(
        [{"role": "user", "content": "read hello.txt"}],
        tools=tools,
        llm=llm,
        max_turns=5,
        stream=False,
    )

    assert terminal.kind == TerminalKind.COMPLETED
    assert llm.calls == 2
    assert "world" in (terminal.content or "")


@pytest.mark.asyncio
async def test_run_loop_max_turns(tmp_path) -> None:
    tool_call = ToolCall(id="c1", name="grep", arguments='{"pattern": "x", "path": "."}')
    response = LLMResponse(
        content=None,
        tool_calls=[tool_call],
        raw_message={
            "role": "assistant",
            "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "grep", "arguments": '{"pattern": "x", "path": "."}'}}
            ],
        },
    )
    llm = MockLLM([response, response, response])
    tools = build_default_registry(cwd=tmp_path)

    terminal = await run_loop(
        [{"role": "user", "content": "loop"}],
        tools=tools,
        llm=llm,
        max_turns=2,
        stream=False,
    )

    assert terminal.kind == TerminalKind.MAX_TURNS


@pytest.mark.asyncio
async def test_parallel_tool_calls(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    calls = [
        ToolCall(id="1", name="read_file", arguments='{"path": "a.txt"}'),
        ToolCall(id="2", name="read_file", arguments='{"path": "b.txt"}'),
    ]
    llm = MockLLM(
        [
            LLMResponse(
                content=None,
                tool_calls=calls,
                raw_message={"role": "assistant", "tool_calls": []},
            ),
            LLMResponse(content="ok", tool_calls=[], raw_message={"role": "assistant", "content": "ok"}),
        ]
    )
    tools = build_default_registry(cwd=tmp_path)

    events = []
    async for event in query_loop(
        [{"role": "user", "content": "read both"}],
        tools=tools,
        llm=llm,
        max_turns=3,
        stream=False,
    ):
        events.append(event)

    tool_events = [e for e in events if e.kind == "tool_result"]
    assert len(tool_events) == 2
    assert events[-1].kind == "terminal"


@pytest.mark.asyncio
async def test_query_loop_aborts(tmp_path) -> None:
    tool_call = ToolCall(id="c1", name="grep", arguments='{"pattern": "x", "path": "."}')
    response = LLMResponse(
        content=None,
        tool_calls=[tool_call],
        raw_message={"role": "assistant", "tool_calls": []},
    )
    llm = MockLLM([response])
    tools = build_default_registry(cwd=tmp_path)
    abort = AbortController()
    abort.abort()

    events = []
    async for event in query_loop(
        [{"role": "user", "content": "x"}],
        tools=tools,
        llm=llm,
        abort=abort,
        stream=False,
    ):
        events.append(event)

    assert events[-1].data["kind"] == TerminalKind.ABORTED.value


@pytest.mark.asyncio
async def test_streaming_yields_deltas(tmp_path) -> None:
    llm = MockLLM(
        [LLMResponse(content="hello", tool_calls=[], raw_message={"role": "assistant", "content": "hello"})]
    )
    tools = build_default_registry(cwd=tmp_path)

    kinds = []
    async for event in query_loop(
        [{"role": "user", "content": "hi"}],
        tools=tools,
        llm=llm,
        stream=True,
    ):
        kinds.append(event.kind)

    assert "assistant_delta" in kinds
    assert kinds[-1] == "terminal"
