# Agentic Loop

Lightweight **Loop Engineering** orchestrator — self-hosted agent loops with tools, state memory, sub-agents, `/goal`, and scheduled automations.

Fork-friendly (MIT). See [docs/architecture.md](docs/architecture.md) and [docs/extending.md](docs/extending.md).

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env   # set OPENAI_API_KEY + DMXAPI base URL
```

```powershell
agentic-loop run "Summarize README" --dry-run
agentic-loop loop --every 5m "Triage issues" --once --dry-run
agentic-loop goal "tests pass" "Fix tests" --dry-run
agentic-loop state show
```

Example project: [examples/daily-triage](examples/daily-triage/)

## Commands

| Command | Purpose |
| :--- | :--- |
| `run` | Single agent loop with tools |
| `loop --every 5m` | Automation (Addy: Automations) |
| `goal "condition" "prompt"` | Run until evaluator confirms goal |
| `state show` | Persistent memory (state.json + triage) |

Common flags: `--cwd`, `--max-turns`, `--skill`, `--agent`, `--allow-bash`, `--dry-run`, `--no-stream`, `--json`

## Loop Engineering modules

| Module | CLI / path |
| :--- | :--- |
| Memory | `state show` → `.agentic-loop/state.json` |
| Skills | `--skill name` → `skills/*/SKILL.md` |
| Sub-agents | `--agent name` → `.agentic-loop/agents/*.toml` |
| Goal | `goal` + `EVALUATOR_MODEL` |
| Automations | `loop --every` |

Run logs: `.agentic-loop/runs/<run_id>.jsonl`

## Development

```powershell
pytest tests/ -q
```

## License

MIT — see [LICENSE](LICENSE).
