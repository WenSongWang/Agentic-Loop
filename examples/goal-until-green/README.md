# Goal Until Green Example

Uses `/goal` with an **independent evaluator model** (see `.env` `EVALUATOR_MODEL`).

## Dry-run

```powershell
agentic-loop goal "tests pass" "Fix tests in this repo" --dry-run --cwd .
```

## Real run

```powershell
agentic-loop goal "pytest tests/ -q passes with exit code 0" "Fix failing tests" --max-rounds 3 --allow-bash
```

The worker agent runs tools; a separate evaluator decides if the condition is satisfied.
