# Agentic Loop

Lightweight **Loop Engineering** orchestrator — self-hosted agent loops with tools, run journal, and CLI.

Fork-friendly (MIT). Built for cron/CI and secondary development; see [docs/architecture.md](docs/architecture.md) (Phase 3).

## Quick Start

### 1. Virtual environment (Windows PowerShell)

```powershell
cd F:\githubs\Agentic-Loop
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

If `pip` still hits system Python, use the venv interpreter explicitly:

```powershell
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 2. Configure API (DMXAPI example)

Copy [`.env.example`](.env.example) to `.env`:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://www.dmxapi.com/v1
OPENAI_MODEL=deepseek-v4-flash
EVALUATOR_MODEL=hunyuan-lite
```

See [DMXAPI OpenAI format docs](https://doc.dmxapi.cn/fanwei.html).

### 3. Run

```powershell
# No API call — validate CLI
agentic-loop run "list files" --dry-run

# Real agent run
agentic-loop run "Use grep to find TODO in this repo" --max-turns 10
```

## CLI

```text
agentic-loop run "<prompt>" [options]

Options:
  --cwd PATH          Workspace root (default: current directory)
  --max-turns N       Max think-act-observe cycles (default: 20)
  --model NAME        Override OPENAI_MODEL
  --api-base URL      Override OPENAI_BASE_URL
  --allow-bash        Enable bash tool (default: off)
  --dry-run           Skip LLM call
  --no-stream         Disable streaming LLM output
  --json              Machine-readable output

Examples:
  agentic-loop run "Summarize README" --dry-run
  agentic-loop run "Find Python files" --max-turns 5
```

Run logs: `.agentic-loop/runs/<run_id>.jsonl`

## Development

```powershell
pytest tests/ -q
```

## License

MIT — see [LICENSE](LICENSE).
