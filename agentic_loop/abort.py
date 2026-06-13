from __future__ import annotations

import asyncio


class AbortController:
    """Cooperative cancellation signal checked between loop steps."""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def abort(self) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    def clear(self) -> None:
        self._event.clear()
