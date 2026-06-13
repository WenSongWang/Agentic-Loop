from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


_INTERVAL_RE = re.compile(r"^(\d+)(s|m|h|d)$", re.IGNORECASE)


def parse_interval(value: str) -> float:
    """Parse interval like 30s, 5m, 2h into seconds."""
    match = _INTERVAL_RE.match(value.strip())
    if not match:
        raise ValueError(
            f"Invalid interval '{value}'. Use formats like 30s, 5m, 2h, 1d.\n"
            "Example: agentic-loop loop --every 5m \"triage open issues\""
        )
    amount = int(match.group(1))
    unit = match.group(2).lower()
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return float(amount * multipliers[unit])


@dataclass
class AutomationResult:
    runs: int
    last_error: str | None = None


async def run_interval(
    *,
    every: str,
    task: Callable[[], Awaitable[Any]],
    once: bool = False,
    max_runs: int | None = None,
) -> AutomationResult:
    seconds = parse_interval(every)
    runs = 0
    last_error: str | None = None

    while True:
        try:
            await task()
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        runs += 1
        if once or (max_runs is not None and runs >= max_runs):
            break
        await asyncio.sleep(seconds)

    return AutomationResult(runs=runs, last_error=last_error)
