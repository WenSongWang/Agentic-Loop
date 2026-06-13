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

EPILOG = """
Examples:
  agentic-loop run "List Python files in this repo" --dry-run
  agentic-loop run "Find TODO comments" --cwd . --max-turns 10
  agentic-loop run "Run tests" --allow-bash --max-turns 5
  agentic-loop run "Explain README" --no-stream
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-loop",
        description="Lightweight Loop Engineering orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser(
        "run",
        help="Run a single agent loop with tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    run.add_argument("prompt", help="Task prompt for the agent")
    run.add_argument("--cwd", type=Path, default=Path.cwd(), help="Workspace directory")
    run.add_argument("--max-turns", type=int, default=20, help="Maximum loop turns")
    run.add_argument("--model", help="Override OPENAI_MODEL")
    run.add_argument("--api-base", dest="base_url", help="Override OPENAI_BASE_URL")
    run.add_argument("--allow-bash", action="store_true", help="Enable bash tool")
    run.add_argument("--dry-run", action="store_true", help="Validate config without calling LLM")
    run.add_argument("--no-stream", action="store_true", help="Disable streaming LLM output")
    run.add_argument("--json", action="store_true", help="Print machine-readable result")
    return parser


def _print_error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    print("Example: agentic-loop run \"hello\" --dry-run", file=sys.stderr)


def _make_event_handler(*, stream_output: bool, json_mode: bool):
    streamed_header = False

    def on_event(event: LoopEvent) -> None:
        nonlocal streamed_header
        if json_mode:
            return
        if event.kind == "turn_start":
            turn = event.data.get("turn")
            print(f"\n--- turn {turn} ---", file=sys.stderr)
        elif event.kind == "assistant_delta" and stream_output:
            if not streamed_header:
                print("\n--- assistant ---", file=sys.stderr)
                streamed_header = True
            print(event.data.get("text", ""), end="", flush=True)
        elif event.kind == "tool_result":
            name = event.data.get("tool")
            print(f"\n[tool:{name}]", file=sys.stderr)

    return on_event


async def _cmd_run(args: argparse.Namespace) -> int:
    overrides = {
        "cwd": args.cwd.resolve(),
        "max_turns": args.max_turns,
        "allow_bash": args.allow_bash,
        "dry_run": args.dry_run,
        "stream": not args.no_stream,
    }
    if args.model:
        overrides["model"] = args.model
    if args.base_url:
        overrides["base_url"] = args.base_url

    config = RunConfig.from_env(overrides=overrides)
    abort = AbortController()

    on_event = _make_event_handler(stream_output=config.stream, json_mode=args.json)

    try:
        terminal, journal = await execute_run(
            args.prompt,
            config=config,
            on_event=on_event,
        )
    except ValueError as exc:
        _print_error(str(exc))
        return 1
    except KeyboardInterrupt:
        abort.abort()
        print("\nAborted.", file=sys.stderr)
        return 130

    if args.json:
        payload = {
            "run_id": journal.run_id,
            "terminal": terminal.to_dict(),
            "journal": str(journal.path),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if config.stream:
            print()
        print(f"run_id: {journal.run_id}")
        print(f"terminal: {terminal.kind.value}")
        print(f"turns: {terminal.turns}")
        if terminal.content and not config.stream:
            print("\n--- result ---\n")
            print(terminal.content)
        elif terminal.content and config.stream:
            print("\n--- final ---\n")
            print(terminal.content)
        if terminal.error and terminal.kind.value != "completed":
            print(f"\nerror: {terminal.error}", file=sys.stderr)

    return terminal.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return asyncio.run(_cmd_run(args))

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
