from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from agentic_loop.llm.client import LLMClient, LLMResponse, ToolCall


class OpenAICompatClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        model: str,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        completion = await self._client.chat.completions.create(**kwargs)
        message = completion.choices[0].message

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for call in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=call.id,
                        name=call.function.name,
                        arguments=call.function.arguments or "{}",
                    )
                )

        raw: dict[str, Any] = {"role": "assistant", "content": message.content}
        if tool_calls:
            raw["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": tc.arguments},
                }
                for tc in tool_calls
            ]

        return LLMResponse(content=message.content, tool_calls=tool_calls, raw_message=raw)


def parse_tool_arguments(arguments: str) -> dict[str, Any]:
    try:
        parsed = json.loads(arguments or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid tool arguments JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Tool arguments must be a JSON object")
    return parsed
