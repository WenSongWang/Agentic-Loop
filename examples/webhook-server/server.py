"""
Minimal HTTP wrapper for Agentic Loop (FastAPI).

Install extras:
  pip install -e ".[webhook]"

Run:
  python examples/webhook-server/server.py
  curl -X POST http://127.0.0.1:8765/run -H "Content-Type: application/json" -d "{\"prompt\":\"hello\"}"
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from fastapi import FastAPI, Header, HTTPException
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise SystemExit(
        "Missing dependencies. Install with: pip install -e \".[webhook]\""
    ) from exc

from agentic_loop import Orchestrator, RunConfig

app = FastAPI(title="Agentic Loop Webhook", version="0.3.0")


class RunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    skill: str | None = None
    agent: str | None = None
    max_turns: int = 20
    dry_run: bool = False
    cwd: str | None = None


class RunResponse(BaseModel):
    run_id: str
    terminal: dict
    state_markdown: str


def _check_token(authorization: str | None) -> None:
    expected = os.getenv("WEBHOOK_TOKEN")
    if not expected:
        return
    if not authorization or authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid or missing Bearer token")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
async def run(body: RunRequest, authorization: str | None = Header(default=None)) -> RunResponse:
    _check_token(authorization)
    cwd = Path(body.cwd).resolve() if body.cwd else Path.cwd()
    config = RunConfig.from_env(
        overrides={
            "cwd": cwd,
            "max_turns": body.max_turns,
            "dry_run": body.dry_run,
        }
    )
    orch = Orchestrator(config)
    terminal, run_id = await orch.run(body.prompt, skill=body.skill, agent=body.agent)
    return RunResponse(
        run_id=run_id,
        terminal=terminal.to_dict(),
        state_markdown=orch.state_markdown(),
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("WEBHOOK_HOST", "127.0.0.1")
    port = int(os.getenv("WEBHOOK_PORT", "8765"))
    uvicorn.run("server:app", host=host, port=port, reload=False)
