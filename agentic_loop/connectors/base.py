from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol


@dataclass
class ConnectorResult:
    ok: bool
    message: str
    data: dict[str, Any] | None = None


class Connector(Protocol):
    name: str

    async def invoke(self, action: str, **params: Any) -> ConnectorResult: ...


ConnectorHandler = Callable[..., Awaitable[ConnectorResult] | ConnectorResult]


class ConnectorRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, ConnectorHandler] = {}

    def register(self, name: str, handler: ConnectorHandler) -> None:
        self._handlers[name] = handler

    async def invoke(self, name: str, action: str, **params: Any) -> ConnectorResult:
        if name not in self._handlers:
            return ConnectorResult(ok=False, message=f"Unknown connector '{name}'")
        result = self._handlers[name](action=action, **params)
        if hasattr(result, "__await__"):
            return await result
        return result

    def list_names(self) -> list[str]:
        return sorted(self._handlers.keys())
