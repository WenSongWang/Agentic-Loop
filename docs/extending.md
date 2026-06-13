# Extending Agentic Loop

MIT licensed — fork and adapt for your team's orchestrator.

## 1. Custom tool

```python
from agentic_loop.tools.registry import build_default_registry

registry = build_default_registry(cwd=Path("."), allow_bash=False)

async def lookup_ticket(args):
    return f"Ticket {args['id']}: open"

registry.register(
    "lookup_ticket",
    "Look up a support ticket by id",
    {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    },
    lookup_ticket,
)
```

## 2. Custom connector

```python
from agentic_loop import ConnectorRegistry, ConnectorResult

registry = ConnectorRegistry()

async def feishu(action: str, **params):
    if action == "notify":
        return ConnectorResult(ok=True, message="sent")
    return ConnectorResult(ok=False, message="unknown action")

registry.register("feishu", feishu)
```

See `examples/custom-tool/demo.py`.

## 3. Python API

```python
from agentic_loop import Orchestrator, RunConfig

config = RunConfig.from_env()
orch = Orchestrator(config)
terminal, run_id = await orch.run("Triage CI failures", skill="triage")
```

## 4. Sub-agents

Create `.agentic-loop/agents/verifier.toml`:

```toml
name = "verifier"
system_prompt = "You verify changes against tests. Read-only except bash for pytest."
allow_bash = true
max_turns = 10
```

Run: `agentic-loop run "Review changes" --agent verifier`

## 5. Goal + evaluator

```powershell
agentic-loop goal "all tests pass" "Fix failing tests" --max-rounds 5
```

Set `EVALUATOR_MODEL` to a cheaper model in `.env`.

## 6. Multi-repo / production checklist

| Item | Recommendation |
| :--- | :--- |
| Secrets | `.env` only, never commit |
| Token budget | cap `--max-turns`, monitor `.agentic-loop/runs/*.jsonl` |
| Verification | always use `/goal` or verifier sub-agent for unattended runs |
| Human triage | review `triage.json` pending items |
| Deploy | cron + `agentic-loop loop --every 5m ... --once` in CI |

## 7. HTTP wrapper (sketch)

Wrap `Orchestrator.run()` in FastAPI:

```python
@app.post("/run")
async def run(body: RunBody):
    orch = Orchestrator(RunConfig.from_env())
    terminal, run_id = await orch.run(body.prompt)
    return {"run_id": run_id, "terminal": terminal.to_dict()}
```
