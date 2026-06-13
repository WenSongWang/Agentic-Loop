# Daily Triage Example

Simulates a Loop Engineering automation: periodic triage → state update → triage inbox.

## Run (dry-run, no API cost)

```powershell
cd examples/daily-triage
..\..\.venv\Scripts\agentic-loop.exe loop --every 5m "Review fixtures/ci-failures.json and summarize findings" --skill triage --once --dry-run
```

## Run once (real API)

```powershell
..\..\.venv\Scripts\agentic-loop.exe loop --every 1m "Read fixtures/ci-failures.json, list failures, suggest fixes" --skill triage --once --cwd .
```

## Files

| File | Purpose |
| :--- | :--- |
| `skills/triage/SKILL.md` | Triage instructions (Loop Engineering skill) |
| `fixtures/ci-failures.json` | Mock CI failures |
| `.agentic-loop/agents/implementer.toml` | Sub-agent stub for Phase 3 extensions |

## State

After runs, check memory:

```powershell
..\..\.venv\Scripts\agentic-loop.exe state show --cwd .
```
