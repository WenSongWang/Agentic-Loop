from __future__ import annotations

from typing import Any

import pytest

from agentic_loop.llm.client import LLMResponse, ToolCall
from agentic_loop.loop import run_loop
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


@pytest.mark.asyncio
async def test_run_loop_completes_without_tools(tmp_path: Path) -> None:
    llm = MockLLM([LLMResponse(content="done", tool_calls=[], raw_message={"role": "assistant", "content": "done"})])
    tools = build_default_registry(cwd=tmp_path)

    terminal = await run_loop(
        [{"role": "user", "content": "hi"}],
        tools=tools,
        llm=llm,
        max_turns=5,
    )

    assert terminal.kind == TerminalKind.COMPLETED
    assert terminal.content == "done"
    assert terminal.turns == 1


@pytest.mark.asyncio
async def test_run_loop_executes_tool_then_completes(tmp_path: Path) -> None:
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
    )

    assert terminal.kind == TerminalKind.COMPLETED
    assert llm.calls == 2
    assert "world" in (terminal.content or "")


@pytest.mark.asyncio
async def test_run_loop_max_turns(tmp_path: Path) -> None:
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
    )

    assert terminal.kind == TerminalKind.MAX_TURNS
