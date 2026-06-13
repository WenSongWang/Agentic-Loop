from __future__ import annotations

from pathlib import Path
from typing import Callable

from agentic_loop.api import execute_run
from agentic_loop.config import RunConfig
from agentic_loop.loop import LoopEvent
from agentic_loop.orchestration.automations import AutomationResult, run_interval
from agentic_loop.orchestration.goal import GoalEvaluation, GoalRunner
from agentic_loop.orchestration.memory import StateStore, TriageItem
from agentic_loop.orchestration.subagents import load_agent_specs, merge_run_config
from agentic_loop.skills.loader import SkillLoader
from agentic_loop.terminal import Terminal


class Orchestrator:
    """Loop Engineering orchestration layer (memory, skills, sub-agents, goal, automations)."""

    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.memory = StateStore(config.state_dir)
        self.skills = SkillLoader(config.cwd, config.state_dir)
        self.agents_dir = config.state_dir / "agents"
        self.agent_specs = load_agent_specs(self.agents_dir)

    def _system_prompt(self, *, skill: str | None = None, agent: str | None = None) -> str | None:
        parts: list[str] = []
        if skill:
            parts.append(self.skills.load_skill(skill))
        if agent and agent in self.agent_specs:
            spec_prompt = self.agent_specs[agent].system_prompt.strip()
            if spec_prompt:
                parts.append(spec_prompt)
        if not parts:
            return self.skills.default_system_prompt()
        return "\n\n".join(parts)

    async def run(
        self,
        prompt: str,
        *,
        skill: str | None = None,
        agent: str | None = None,
        on_event: Callable[[LoopEvent], None] | None = None,
    ) -> tuple[Terminal, str]:
        config = self.config
        system_prompt = self._system_prompt(skill=skill, agent=agent)

        if agent and agent in self.agent_specs:
            config, agent_prompt, _tools = merge_run_config(config, self.agent_specs[agent])
            if agent_prompt:
                system_prompt = "\n\n".join(filter(None, [system_prompt, agent_prompt]))

        state_context = self.memory.format_markdown()
        enriched_prompt = f"{prompt}\n\n--- project state ---\n{state_context}"

        terminal, journal = await execute_run(
            enriched_prompt,
            config=config,
            system_prompt=system_prompt,
            on_event=on_event,
        )
        passed = terminal.kind.value == "completed"
        summary = terminal.content or terminal.error or prompt[:200]
        self.memory.record_run(run_id=journal.run_id, summary=summary, passed=passed)
        return terminal, journal.run_id

    async def run_goal(
        self,
        *,
        condition: str,
        prompt: str,
        skill: str | None = None,
        agent: str | None = None,
        max_rounds: int = 10,
        on_event: Callable[[LoopEvent], None] | None = None,
    ) -> tuple[Terminal, list[GoalEvaluation]]:
        config = self.config
        system_prompt = self._system_prompt(skill=skill, agent=agent)
        if agent and agent in self.agent_specs:
            config, agent_prompt, _ = merge_run_config(config, self.agent_specs[agent])
            if agent_prompt:
                system_prompt = "\n\n".join(filter(None, [system_prompt, agent_prompt]))

        runner = GoalRunner(config=config)
        terminal, evaluations = await runner.run_until_goal(
            condition=condition,
            prompt=prompt,
            system_prompt=system_prompt,
            max_rounds=max_rounds,
            on_event=on_event,
        )
        return terminal, evaluations

    async def automation(
        self,
        prompt: str,
        *,
        every: str,
        skill: str | None = None,
        once: bool = False,
        on_event: Callable[[LoopEvent], None] | None = None,
    ) -> AutomationResult:
        async def _task() -> None:
            terminal, run_id = await self.run(prompt, skill=skill, on_event=on_event)
            if terminal.kind.value != "completed":
                self.memory.add_triage(
                    f"Automation run needs review ({run_id})",
                    detail=terminal.error or terminal.content or "",
                )

        return await run_interval(every=every, task=_task, once=once)

    def triage_pending(self) -> list[TriageItem]:
        return [item for item in self.memory.load_triage() if item.status == "pending"]

    def state_markdown(self) -> str:
        return self.memory.format_markdown()
