# Examples Index

| Example | Path | Demonstrates |
| :--- | :--- | :--- |
| Daily triage | [examples/daily-triage](../examples/daily-triage/) | `loop`, skills, state, fixtures |
| Goal until green | [examples/goal-until-green](../examples/goal-until-green/) | `/goal`, evaluator |
| Custom tool | [examples/custom-tool](../examples/custom-tool/) | connectors, Python API |
| Webhook server | [examples/webhook-server](../examples/webhook-server/) | FastAPI HTTP wrapper |
| GitHub Actions | [examples/github-actions](../examples/github-actions/) | CI automation template |
| MCP bridge | [examples/mcp-bridge](../examples/mcp-bridge/) | MCP tools → ToolRegistry |

## Suggested order

1. `daily-triage` — Quick Start
2. `goal-until-green` — unattended safety
3. `custom-tool` — fork / 二开

## Run tests for examples (no API)

```powershell
pytest tests/test_orchestration.py -q
python examples/custom-tool/demo.py
```
