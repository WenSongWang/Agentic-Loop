from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SubAgentSpec:
    name: str
    description: str = ""
    system_prompt: str = ""
    model: str | None = None
    allow_bash: bool | None = None
    tools: list[str] | None = None
    max_turns: int | None = None


def load_agent_specs(agents_dir: Path) -> dict[str, SubAgentSpec]:
    if not agents_dir.exists():
        return {}

    specs: dict[str, SubAgentSpec] = {}
    for path in sorted(agents_dir.glob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        name = str(data.get("name") or path.stem)
        specs[name] = SubAgentSpec(
            name=name,
            description=str(data.get("description", "")),
            system_prompt=str(data.get("system_prompt", "")),
            model=data.get("model"),
            allow_bash=data.get("allow_bash"),
            tools=list(data["tools"]) if data.get("tools") else None,
            max_turns=data.get("max_turns"),
        )
    return specs


def merge_run_config(base, spec: SubAgentSpec):
    from agentic_loop.config import RunConfig

    overrides: dict = {}
    if spec.model:
        overrides["model"] = spec.model
    if spec.allow_bash is not None:
        overrides["allow_bash"] = spec.allow_bash
    if spec.max_turns is not None:
        overrides["max_turns"] = spec.max_turns

    merged = RunConfig(
        cwd=base.cwd,
        model=overrides.get("model", base.model),
        evaluator_model=base.evaluator_model,
        api_key=base.api_key,
        base_url=base.base_url,
        max_turns=overrides.get("max_turns", base.max_turns),
        allow_bash=overrides.get("allow_bash", base.allow_bash),
        dry_run=base.dry_run,
        stream=base.stream,
        max_retries=base.max_retries,
        tool_timeout=base.tool_timeout,
        agentic_loop_dir=base.agentic_loop_dir,
    )
    return merged, spec.system_prompt or None, spec.tools
