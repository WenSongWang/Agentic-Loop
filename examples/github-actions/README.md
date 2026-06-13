# GitHub Actions Example

Copy [workflow-triage.yml](./workflow-triage.yml) to `.github/workflows/` in your repo.

## Required secrets

| Secret | Description |
| :--- | :--- |
| `OPENAI_API_KEY` | LLM API key (DMXAPI or OpenAI-compatible) |
| `OPENAI_BASE_URL` | Optional, e.g. `https://www.dmxapi.com/v1` |

## What it does

On a schedule (and manual dispatch):

1. `pip install agentic-loop` (or editable install from checkout)
2. `agentic-loop loop --every 1m "..." --once --skill triage`
3. Uploads `.agentic-loop/runs/*.jsonl` as artifact

## Local dry-run equivalent

```powershell
agentic-loop loop --every 5m "Triage open issues" --once --dry-run
```
