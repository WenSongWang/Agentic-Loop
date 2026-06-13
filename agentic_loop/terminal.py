from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TerminalKind(str, Enum):
    COMPLETED = "completed"
    MAX_TURNS = "max_turns"
    ERROR = "error"
    ABORTED = "aborted"
    MODEL_ERROR = "model_error"


class Terminal(BaseModel):
    kind: TerminalKind
    content: str | None = None
    error: str | None = None
    turns: int = 0

    @classmethod
    def completed(cls, content: str | None, *, turns: int) -> Terminal:
        return cls(kind=TerminalKind.COMPLETED, content=content, turns=turns)

    @classmethod
    def max_turns(cls, *, turns: int, last_content: str | None = None) -> Terminal:
        return cls(
            kind=TerminalKind.MAX_TURNS,
            content=last_content,
            turns=turns,
            error=f"Reached max turns ({turns})",
        )

    @classmethod
    def failed(cls, message: str, *, turns: int = 0) -> Terminal:
        return cls(kind=TerminalKind.ERROR, error=message, turns=turns)

    @classmethod
    def aborted(cls, *, turns: int) -> Terminal:
        return cls(kind=TerminalKind.ABORTED, turns=turns, error="Run aborted")

    @classmethod
    def model_error(cls, message: str, *, turns: int) -> Terminal:
        return cls(kind=TerminalKind.MODEL_ERROR, error=message, turns=turns)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)

    @property
    def exit_code(self) -> int:
        if self.kind == TerminalKind.COMPLETED:
            return 0
        return 1
