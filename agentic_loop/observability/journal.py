from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunJournal:
    def __init__(self, runs_dir: Path, run_id: str | None = None) -> None:
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.runs_dir = runs_dir
        self.path = runs_dir / f"{self.run_id}.jsonl"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _write(self, event: dict[str, Any]) -> None:
        event = {"ts": datetime.now(timezone.utc).isoformat(), **event}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def started(self, *, prompt: str, config: dict[str, Any]) -> None:
        self._write({"event": "run_started", "prompt": prompt, "config": config})

    def turn(self, *, turn: int, tool_names: list[str]) -> None:
        self._write({"event": "turn", "turn": turn, "tools": tool_names})

    def tool_result(self, *, turn: int, name: str, duration_ms: float, preview: str) -> None:
        self._write(
            {
                "event": "tool_result",
                "turn": turn,
                "tool": name,
                "duration_ms": round(duration_ms, 2),
                "preview": preview[:500],
            }
        )

    def finished(self, *, terminal: dict[str, Any], duration_ms: float) -> None:
        self._write(
            {
                "event": "run_finished",
                "terminal": terminal,
                "duration_ms": round(duration_ms, 2),
            }
        )
