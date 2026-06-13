from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from agentic_loop.config import RunConfig
from agentic_loop.llm.openai_compat import OpenAICompatClient
from agentic_loop.terminal import Terminal


@dataclass
class GoalEvaluation:
    satisfied: bool
    reason: str


EVALUATOR_SYSTEM = """You are an independent goal evaluator for an agent loop.
You do NOT execute tools. You judge whether a stopping condition is satisfied based on:
1) the goal condition text, and
2) the worker agent's final response and run summary.

Reply with JSON only: {"satisfied": true|false, "reason": "..."}"""


class GoalRunner:
    def __init__(self, *, config: RunConfig) -> None:
        self.config = config

    async def evaluate(self, *, condition: str, worker_result: str, turns: int) -> GoalEvaluation:
        if self.config.dry_run:
            return GoalEvaluation(satisfied=True, reason="[dry-run] goal assumed satisfied")

        self.config.require_api_key()
        client = OpenAICompatClient(
            api_key=self.config.api_key or "",
            base_url=self.config.base_url,
            model=self.config.effective_evaluator_model,
            max_retries=self.config.max_retries,
        )
        user_content = (
            f"Goal condition:\n{condition}\n\n"
            f"Worker turns: {turns}\n\n"
            f"Worker final output:\n{worker_result}\n\n"
            "Is the goal condition satisfied?"
        )
        response = await client.chat(
            [
                {"role": "system", "content": EVALUATOR_SYSTEM},
                {"role": "user", "content": user_content},
            ]
        )
        text = (response.content or "").strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return GoalEvaluation(
                    satisfied=bool(data.get("satisfied")),
                    reason=str(data.get("reason", "")),
                )
            except json.JSONDecodeError:
                pass
        lowered = text.lower()
        satisfied = any(word in lowered for word in ("true", "satisfied", "yes", "complete", "passed"))
        return GoalEvaluation(satisfied=satisfied, reason=text[:500] or "Could not parse evaluator output")

    async def run_until_goal(
        self,
        *,
        condition: str,
        prompt: str,
        system_prompt: str | None = None,
        max_rounds: int = 10,
        on_event=None,
    ) -> tuple[Terminal, list[GoalEvaluation]]:
        from agentic_loop.api import execute_run

        evaluations: list[GoalEvaluation] = []
        last_terminal: Terminal | None = None

        for round_idx in range(1, max_rounds + 1):
            round_prompt = prompt
            if round_idx > 1 and last_terminal and last_terminal.content:
                round_prompt = (
                    f"{prompt}\n\nPrevious attempt summary:\n{last_terminal.content}\n"
                    f"Continue working toward the goal."
                )

            terminal, _journal = await execute_run(
                round_prompt,
                config=self.config,
                system_prompt=system_prompt,
                on_event=on_event,
            )
            last_terminal = terminal
            evaluation = await self.evaluate(
                condition=condition,
                worker_result=terminal.content or terminal.error or "",
                turns=terminal.turns,
            )
            evaluations.append(evaluation)
            if evaluation.satisfied:
                return Terminal.completed(
                    f"Goal satisfied after round {round_idx}: {evaluation.reason}\n\n"
                    f"{terminal.content or ''}",
                    turns=terminal.turns,
                ), evaluations

        return Terminal.failed(
            f"Goal not satisfied after {max_rounds} rounds. Last reason: {evaluations[-1].reason if evaluations else 'none'}",
            turns=last_terminal.turns if last_terminal else 0,
        ), evaluations
