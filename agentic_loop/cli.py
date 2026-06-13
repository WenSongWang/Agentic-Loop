from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from agentic_loop.abort import AbortController
from agentic_loop.api import execute_run
from agentic_loop.config import RunConfig
from agentic_loop.loop import LoopEvent
from agentic_loop.orchestration.automations import parse_interval
from agentic_loop.orchestration.orchestrator import Orchestrator

RUN_EPILOG = """
Examples:
  agentic-loop run "List Python files" --dry-run
  agentic-loop run "Find TODO comments" --max-turns 10
  agentic-loop run "Explain README" --no-stream
"""

LOOP_EPILOG = """
Examples:
  agentic-loop loop --every 5m "Triage open issues" --once
  agentic-loop loop --every 30s "Check deploy" --skill triage --dry-run
"""

GOAL_EPILOG = """
Examples:
  agentic-loop goal "pytest tests/ passes" "Fix failing tests" --max-rounds 5
  agentic-loop goal "lint is clean" "Run linter and fix issues" --dry-run
"""

STATE_EPILOG = """
Examples:
  agentic-loop state show
  agentic-loop state reset
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-loop",
        description="Lightweight Loop Engineering orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Single agent run", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=RUN_EPILOG)
    run.add_argument("prompt")
    _add_common_run_flags(run)

    loop = sub.add_parser("loop", help="Scheduled automation", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=LOOP_EPILOG)
    loop.add_argument("prompt")
    loop.add_argument("--every", required=True, help="Interval: 30s, 5m, 2h, 1d")
    loop.add_argument("--once", action="store_true", help="Run once instead of forever")
    _add_common_run_flags(loop)

    goal = sub.add_parser("goal", help="Run until goal condition passes", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=GOAL_EPILOG)
    goal.add_argument("condition", help="Verifiable stopping condition")
    goal.add_argument("prompt", help="Worker task prompt")
    goal.add_argument("--max-rounds", type=int, default=10)
    _add_common_run_flags(goal)

    state = sub.add_parser("state", help="Project memory", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=STATE_EPILOG)
    state_sub = state.add_subparsers(dest="state_cmd", required=True)
    state_show = state_sub.add_parser("show", help="Print state markdown")
    state_show.add_argument("--cwd", type=Path, default=Path.cwd())
    state_show.add_argument("--json", action="store_true")
    state_reset = state_sub.add_parser("reset", help="Clear state and triage")
    state_reset.add_argument("--cwd", type=Path, default=Path.cwd())
    state_reset.add_argument("--yes", action="store_true", help="Skip confirmation")

    return parser


def _add_common_run_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--model")
    parser.add_argument("--api-base", dest="base_url")
    parser.add_argument("--allow-bash", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-stream", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skill", help="Skill to load into system prompt")
    parser.add_argument("--agent", help="Sub-agent role")


def _print_error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def _config_from_args(args: argparse.Namespace) -> RunConfig:
    overrides = {
        "cwd": args.cwd.resolve(),
        "max_turns": getattr(args, "max_turns", 20),
        "allow_bash": getattr(args, "allow_bash", False),
        "dry_run": getattr(args, "dry_run", False),
        "stream": not getattr(args, "no_stream", False),
    }
    if getattr(args, "model", None):
        overrides["model"] = args.model
    if getattr(args, "base_url", None):
        overrides["base_url"] = args.base_url
    return RunConfig.from_env(overrides=overrides)


def _make_event_handler(*, stream_output: bool, json_mode: bool):
    streamed_header = False

    def on_event(event: LoopEvent) -> None:
        nonlocal streamed_header
        if json_mode:
            return
        if event.kind == "turn_start":
            print(f"\n--- turn {event.data.get('turn')} ---", file=sys.stderr)
        elif event.kind == "assistant_delta" and stream_output:
            if not streamed_header:
                print("\n--- assistant ---", file=sys.stderr)
                streamed_header = True
            print(event.data.get("text", ""), end="", flush=True)
        elif event.kind == "tool_result":
            print(f"\n[tool:{event.data.get('tool')}]", file=sys.stderr)

    return on_event


def _print_terminal(terminal, journal, *, config: RunConfig, json_mode: bool) -> int:
    if json_mode:
        print(json.dumps({"run_id": journal.run_id, "terminal": terminal.to_dict()}, ensure_ascii=False, indent=2))
        return terminal.exit_code
    if config.stream:
        print()
    print(f"run_id: {journal.run_id}")
    print(f"terminal: {terminal.kind.value}")
    print(f"turns: {terminal.turns}")
    if terminal.content:
        print("\n--- result ---\n")
        print(terminal.content)
    if terminal.error and terminal.kind.value != "completed":
        print(f"\nerror: {terminal.error}", file=sys.stderr)
    return terminal.exit_code


async def _cmd_run(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    on_event = _make_event_handler(stream_output=config.stream, json_mode=args.json)
    try:
        if args.skill or args.agent:
            orch = Orchestrator(config)
            terminal, run_id = await orch.run(
                args.prompt,
                skill=args.skill,
                agent=args.agent,
                on_event=on_event,
            )
            if args.json:
                print(json.dumps({"run_id": run_id, "terminal": terminal.to_dict()}, ensure_ascii=False, indent=2))
                return terminal.exit_code
            print(f"run_id: {run_id}")
            print(f"terminal: {terminal.kind.value}")
            if terminal.content:
                print(terminal.content)
            return terminal.exit_code

        terminal, journal = await execute_run(args.prompt, config=config, on_event=on_event)
    except ValueError as exc:
        _print_error(str(exc))
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    return _print_terminal(terminal, journal, config=config, json_mode=args.json)


async def _cmd_loop(args: argparse.Namespace) -> int:
    try:
        parse_interval(args.every)
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    config = _config_from_args(args)
    orch = Orchestrator(config)
    on_event = _make_event_handler(stream_output=config.stream, json_mode=args.json)

    if args.dry_run:
        print(f"[dry-run] Would run every {args.every}: {args.prompt}")
        return 0

    print(f"Automation started: every {args.every}" + (" (once)" if args.once else ""), file=sys.stderr)
    try:
        result = await orch.automation(
            args.prompt,
            every=args.every,
            skill=args.skill,
            once=args.once,
            on_event=on_event,
        )
    except KeyboardInterrupt:
        print("\nAutomation stopped.", file=sys.stderr)
        return 130

    if args.json:
        print(json.dumps({"runs": result.runs, "last_error": result.last_error}, indent=2))
    else:
        print(f"runs: {result.runs}")
        if result.last_error:
            print(f"last_error: {result.last_error}", file=sys.stderr)
    return 0 if not result.last_error else 1


async def _cmd_goal(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    orch = Orchestrator(config)
    on_event = _make_event_handler(stream_output=config.stream, json_mode=args.json)
    try:
        terminal, evaluations = await orch.run_goal(
            condition=args.condition,
            prompt=args.prompt,
            skill=args.skill,
            agent=args.agent,
            max_rounds=args.max_rounds,
            on_event=on_event,
        )
    except ValueError as exc:
        _print_error(str(exc))
        return 1
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130

    if args.json:
        print(
            json.dumps(
                {
                    "terminal": terminal.to_dict(),
                    "evaluations": [e.__dict__ for e in evaluations],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"terminal: {terminal.kind.value}")
        for idx, ev in enumerate(evaluations, start=1):
            print(f"round {idx}: satisfied={ev.satisfied} reason={ev.reason}")
        if terminal.content:
            print("\n--- result ---\n")
            print(terminal.content)
    return terminal.exit_code


async def _cmd_state(args: argparse.Namespace) -> int:
    config = RunConfig.from_env(overrides={"cwd": args.cwd.resolve()})
    store = Orchestrator(config).memory

    if args.state_cmd == "show":
        if args.json:
            print(json.dumps(store.load_state().__dict__, ensure_ascii=False, indent=2))
        else:
            print(store.format_markdown())
        return 0

    if args.state_cmd == "reset":
        if not args.yes:
            _print_error("Pass --yes to clear state.json and triage.json")
            return 1
        if store.state_path.exists():
            store.state_path.unlink()
        if store.triage_path.exists():
            store.triage_path.unlink()
        print("State cleared.")
        return 0

    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return asyncio.run(_cmd_run(args))
    if args.command == "loop":
        return asyncio.run(_cmd_loop(args))
    if args.command == "goal":
        return asyncio.run(_cmd_goal(args))
    if args.command == "state":
        return asyncio.run(_cmd_state(args))

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
