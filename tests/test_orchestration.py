from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_loop.config import RunConfig
from agentic_loop.orchestration.automations import parse_interval
from agentic_loop.orchestration.memory import StateStore, TriageItem
from agentic_loop.orchestration.orchestrator import Orchestrator
from agentic_loop.skills.loader import SkillLoader


def test_parse_interval() -> None:
    assert parse_interval("30s") == 30
    assert parse_interval("5m") == 300
    assert parse_interval("2h") == 7200


def test_parse_interval_invalid() -> None:
    with pytest.raises(ValueError):
        parse_interval("5minutes")


def test_state_store_record_and_dedupe(tmp_path: Path) -> None:
    store = StateStore(tmp_path / ".agentic-loop")
    store.record_run(run_id="r1", summary="task-a", passed=True)
    state = store.load_state()
    assert "task-a" in state.passed
    assert state.last_run_id == "r1"

    item1 = store.add_triage("CI failure", detail="test failed")
    item2 = store.add_triage("CI failure", detail="duplicate")
    assert item1.id == item2.id


def test_skill_loader(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".agentic-loop" / "skills" / "triage"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Triage skill\nCheck CI.", encoding="utf-8")
    loader = SkillLoader(tmp_path, tmp_path / ".agentic-loop")
    assert "triage" in loader.list_skills()
    assert "Triage skill" in loader.load_skill("triage")


@pytest.mark.asyncio
async def test_orchestrator_run_dry_run(tmp_path: Path) -> None:
    config = RunConfig(cwd=tmp_path, dry_run=True)
    orch = Orchestrator(config)
    terminal, run_id = await orch.run("hello", skill=None)
    assert terminal.kind.value == "completed"
    assert run_id == "dry-run"


@pytest.mark.asyncio
async def test_orchestrator_automation_once(tmp_path: Path) -> None:
    config = RunConfig(cwd=tmp_path, dry_run=True)
    orch = Orchestrator(config)
    result = await orch.automation("check issues", every="1s", once=True)
    assert result.runs == 1


@pytest.mark.asyncio
async def test_goal_dry_run(tmp_path: Path) -> None:
    config = RunConfig(cwd=tmp_path, dry_run=True)
    orch = Orchestrator(config)
    terminal, evaluations = await orch.run_goal(
        condition="tests pass",
        prompt="fix tests",
        max_rounds=2,
    )
    assert terminal.kind.value == "completed"
    assert evaluations[-1].satisfied is True
