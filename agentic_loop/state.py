from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

TransitionReason = Literal[
    "next_turn",
    "max_output_tokens_recovery",
    "stop_hook_blocking",
]


@dataclass(frozen=True)
class LoopState:
    messages: list[dict[str, Any]]
    turn_count: int = 0
    transition: TransitionReason | None = None

    def with_messages(self, messages: list[dict[str, Any]]) -> LoopState:
        return replace(self, messages=list(messages))

    def next_turn(self, messages: list[dict[str, Any]], reason: TransitionReason = "next_turn") -> LoopState:
        return replace(
            self,
            messages=list(messages),
            turn_count=self.turn_count + 1,
            transition=reason,
        )
