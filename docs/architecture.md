# Architecture

Agentic Loop has two layers:

```text
Loop Engineering (Phase 3)          Agent Runtime (Phase 1–2)
─────────────────────────          ─────────────────────────
Orchestrator                       query_loop / run_loop
├── memory (state.json)            ├── LLM client (OpenAI-compatible)
├── skills (SKILL.md)              ├── tools (read/write/grep/bash)
├── sub-agents (*.toml)            ├── retry + streaming
├── goal + evaluator               └── JSONL run journal
├── automations (loop CLI)
├── worktree (git)
└── connectors (MCP shell)
```

## Addy Osmani's five modules ↔ this repo

| Module | Directory | CLI |
| :--- | :--- | :--- |
| Automations | `orchestration/automations.py` | `agentic-loop loop --every 5m` |
| Worktrees | `worktree/manager.py` | (API / future CLI) |
| Skills | `skills/loader.py` | `--skill triage` |
| Connectors | `connectors/base.py` | (register in code) |
| Sub-agents | `orchestration/subagents.py` | `--agent implementer` |
| Memory | `orchestration/memory.py` | `agentic-loop state show` |

## Read order

1. `agentic_loop/loop.py` — Think → Act → Observe
2. `agentic_loop/orchestration/orchestrator.py` — outer loop
3. `agentic_loop/observability/journal.py` — audit trail

References:

- [Loop Engineering (Addy Osmani)](https://addyo.substack.com/p/loop-engineering)
- [WeChat summary](https://mp.weixin.qq.com/s/fXA4L2Qo1JhTwvWuYRAuhQ)
