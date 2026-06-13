# Webhook Server Example

HTTP wrapper around `Orchestrator` for CI/bot integrations.

## Setup

```powershell
pip install -e ".[webhook]"
```

Optional auth:

```env
WEBHOOK_TOKEN=your-secret-token
```

## Run

```powershell
cd examples/webhook-server
..\..\.venv\Scripts\python.exe server.py
```

## Request

```powershell
curl -X POST http://127.0.0.1:8765/run `
  -H "Content-Type: application/json" `
  -d "{\"prompt\":\"List TODOs in README\",\"dry_run\":true}"
```

With token:

```powershell
curl -X POST http://127.0.0.1:8765/run `
  -H "Authorization: Bearer your-secret-token" `
  -H "Content-Type: application/json" `
  -d "{\"prompt\":\"Triage issues\",\"skill\":\"triage\"}"
```

## Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| GET | `/health` | Liveness |
| POST | `/run` | Trigger one orchestrated run |
