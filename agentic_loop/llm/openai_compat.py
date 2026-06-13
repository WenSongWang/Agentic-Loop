from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from agentic_loop.llm.client import LLMResponse, StreamChunk, ToolCall
from agentic_loop.llm.retry import with_retry


def parse_tool_arguments(arguments: str) -> dict[str, Any]:
    try:
        parsed = json.loads(arguments or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid tool arguments JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Tool arguments must be a JSON object")
    return parsed


def _build_raw_message(content: str | None, tool_calls: list[ToolCall]) -> dict[str, Any]:
    raw: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        raw["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": tc.arguments},
            }
            for tc in tool_calls
        ]
    return raw


def _parse_tool_calls(message_tool_calls: Any) -> list[ToolCall]:
    tool_calls: list[ToolCall] = []
    if not message_tool_calls:
        return tool_calls
    for call in message_tool_calls:
        tool_calls.append(
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=call.function.arguments or "{}",
            )
        )
    return tool_calls


class OpenAICompatClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        model: str,
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        self.model = model
        self.max_retries = max_retries
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def _request_kwargs(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None,
        stream: bool,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        return kwargs

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        async def _call() -> LLMResponse:
            completion = await self._client.chat.completions.create(
                **self._request_kwargs(messages, tools=tools, stream=False)
            )
            message = completion.choices[0].message
            tool_calls = _parse_tool_calls(message.tool_calls)
            return LLMResponse(
                content=message.content,
                tool_calls=tool_calls,
                raw_message=_build_raw_message(message.content, tool_calls),
                finish_reason=completion.choices[0].finish_reason,
            )

        return await with_retry(_call, max_retries=self.max_retries)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        async def _create_stream():
            return await self._client.chat.completions.create(
                **self._request_kwargs(messages, tools=tools, stream=True)
            )

        stream = await with_retry(_create_stream, max_retries=self.max_retries)

        content_parts: list[str] = []
        tool_calls_by_index: dict[int, dict[str, str]] = {}
        finish_reason: str | None = None

        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            finish_reason = choice.finish_reason or finish_reason
            delta = choice.delta

            if delta.content:
                content_parts.append(delta.content)
                yield StreamChunk(kind="text_delta", text=delta.content)

            if delta.tool_calls:
                for tool_delta in delta.tool_calls:
                    idx = tool_delta.index
                    entry = tool_calls_by_index.setdefault(
                        idx,
                        {"id": "", "name": "", "arguments": ""},
                    )
                    if tool_delta.id:
                        entry["id"] = tool_delta.id
                    if tool_delta.function:
                        if tool_delta.function.name:
                            entry["name"] = tool_delta.function.name
                        if tool_delta.function.arguments:
                            entry["arguments"] += tool_delta.function.arguments

        tool_calls = [
            ToolCall(
                id=entry["id"] or f"call_{index}",
                name=entry["name"],
                arguments=entry["arguments"] or "{}",
            )
            for index, entry in sorted(tool_calls_by_index.items())
            if entry["name"]
        ]
        content = "".join(content_parts) or None
        response = LLMResponse(
            content=content,
            tool_calls=tool_calls,
            raw_message=_build_raw_message(content, tool_calls),
            finish_reason=finish_reason,
        )
        yield StreamChunk(kind="done", response=response)
