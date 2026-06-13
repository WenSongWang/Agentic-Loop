from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def _find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        if (path / "agentic-loop.toml").exists() or (path / "pyproject.toml").exists():
            return path
    return current


@dataclass
class RunConfig:
    cwd: Path = field(default_factory=Path.cwd)
    model: str = "gpt-4o-mini"
    evaluator_model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    max_turns: int = 20
    allow_bash: bool = False
    dry_run: bool = False
    stream: bool = True
    max_retries: int = 3
    tool_timeout: float = 120.0
    agentic_loop_dir: Path | None = None

    @property
    def state_dir(self) -> Path:
        base = self.agentic_loop_dir or (self.cwd / ".agentic-loop")
        return base

    @property
    def runs_dir(self) -> Path:
        return self.state_dir / "runs"

    @property
    def effective_evaluator_model(self) -> str:
        return self.evaluator_model or self.model

    @classmethod
    def from_env(cls, *, cwd: Path | None = None, overrides: dict[str, Any] | None = None) -> RunConfig:
        root = _find_project_root(cwd)
        load_dotenv(root / ".env")
        load_dotenv()

        cfg = cls(
            cwd=(cwd or Path.cwd()).resolve(),
            model=os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "gpt-4o-mini",
            evaluator_model=os.getenv("EVALUATOR_MODEL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
        if overrides:
            for key, value in overrides.items():
                if value is not None and hasattr(cfg, key):
                    setattr(cfg, key, value)
        return cfg

    def require_api_key(self) -> str:
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set.\n"
                "Copy .env.example to .env and set your key.\n"
                "Example: agentic-loop run \"hello\" --dry-run  # no API key needed"
            )
        return self.api_key
