from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TriageItem:
    id: str
    title: str
    status: str = "pending"
    detail: str = ""
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    run_id: str | None = None

    @classmethod
    def create(cls, title: str, *, detail: str = "") -> TriageItem:
        return cls(id=uuid.uuid4().hex[:10], title=title, detail=detail)


@dataclass
class ProjectState:
    attempted: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    last_run_at: str | None = None
    last_run_id: str | None = None
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectState:
        return cls(
            attempted=list(data.get("attempted", [])),
            passed=list(data.get("passed", [])),
            pending=list(data.get("pending", [])),
            last_run_at=data.get("last_run_at"),
            last_run_id=data.get("last_run_id"),
            notes=data.get("notes", ""),
        )


class StateStore:
    """Persistent loop memory on disk (models forget; the repo does not)."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "state.json"
        self.triage_path = self.state_dir / "triage.json"

    def load_state(self) -> ProjectState:
        if not self.state_path.exists():
            return ProjectState()
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        return ProjectState.from_dict(data)

    def save_state(self, state: ProjectState) -> None:
        self.state_path.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def load_triage(self) -> list[TriageItem]:
        if not self.triage_path.exists():
            return []
        raw = json.loads(self.triage_path.read_text(encoding="utf-8"))
        return [TriageItem(**item) for item in raw.get("items", [])]

    def save_triage(self, items: list[TriageItem]) -> None:
        payload = {"items": [asdict(item) for item in items]}
        self.triage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def record_run(self, *, run_id: str, summary: str, passed: bool) -> ProjectState:
        state = self.load_state()
        state.last_run_at = _utc_now()
        state.last_run_id = run_id
        key = summary[:200]
        if key not in state.attempted:
            state.attempted.append(key)
        if passed:
            if key not in state.passed:
                state.passed.append(key)
            state.pending = [item for item in state.pending if item != key]
        elif key not in state.pending:
            state.pending.append(key)
        self.save_state(state)
        return state

    def add_triage(self, title: str, *, detail: str = "", dedupe: bool = True) -> TriageItem:
        items = self.load_triage()
        if dedupe:
            for item in items:
                if item.title == title and item.status == "pending":
                    return item
        entry = TriageItem.create(title, detail=detail)
        items.append(entry)
        self.save_triage(items)
        return entry

    def update_triage_status(self, item_id: str, status: str) -> TriageItem | None:
        items = self.load_triage()
        for item in items:
            if item.id == item_id:
                item.status = status
                item.updated_at = _utc_now()
                self.save_triage(items)
                return item
        return None

    def format_markdown(self) -> str:
        state = self.load_state()
        triage = self.load_triage()
        lines = [
            "# Agentic Loop State",
            "",
            f"- last_run_at: {state.last_run_at or '(none)'}",
            f"- last_run_id: {state.last_run_id or '(none)'}",
            "",
            "## Attempted",
        ]
        lines.extend(f"- {item}" for item in state.attempted[-20:]) or ["- (none)"]
        lines.extend(["", "## Passed"])
        lines.extend(f"- {item}" for item in state.passed[-20:]) or ["- (none)"]
        lines.extend(["", "## Pending"])
        lines.extend(f"- {item}" for item in state.pending) or ["- (none)"]
        lines.extend(["", "## Triage Inbox"])
        pending_triage = [t for t in triage if t.status == "pending"]
        if not pending_triage:
            lines.append("- (empty)")
        else:
            for item in pending_triage[:20]:
                lines.append(f"- [{item.id}] {item.title}")
        return "\n".join(lines) + "\n"
