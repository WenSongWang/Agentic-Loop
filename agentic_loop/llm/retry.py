from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from openai import APIStatusError, APITimeoutError, RateLimitError

T = TypeVar("T")

RETRYABLE_EXCEPTIONS = (RateLimitError, APITimeoutError, APIStatusError)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, RateLimitError | APITimeoutError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code >= 500:
        return True
    return False


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> T:
    delay = base_delay
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await operation()
        except RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt >= max_retries - 1:
                raise
            await asyncio.sleep(delay)
            delay *= 2
    if last_exc:
        raise last_exc
    raise RuntimeError("with_retry exhausted without result")
