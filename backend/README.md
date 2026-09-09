# ⚙️ Genlock Sentinel — Backend Runtime

> **Autonomous SRE & Frame-Sync Integrity Agent for Unreal Engine ICVFX Stages**  
> *Powered by Google ADK 2.x, Gemini 3.1 Pro, Grafana MCP, and Cloud SQL.*

---

## Architecture Overview

The backend orchestrates the authoritative 7-node ADK Workflow Runtime graph defined in `AGENT_ORCHESTRATION_BLUEPRINT.md`:

```
Node 1: Stream Watch (non-LLM)
  → Node 2: Evidence Triage (Gemini 3.7 Flash + Grafana MCP)
  → Node 3: Root-Cause Correlation (Gemini 3.1 Pro @ temp=0.0)
  → Decision Edge (Deterministic Python Routing)
      ├── Route: Autonomous → Node 4: Autonomous Remediation Dispatch
      └── Route: HITL Escalation → Node 5: HITL Card Generation
            → Node 6: HITL Pause (ADK Checkpoint Interrupt)
            → Node 7: Post-Approval Handling (Deterministic)
```

---

## Environment Configuration

Copy `backend/.env.example` to `backend/.env` and configure credentials:

```bash
# Core Models
GEMINI_REASONING_MODEL=gemini-3.1-pro
GEMINI_FAST_MODEL=gemini-3.7-flash
GEMINI_API_KEY=<your-gemini-api-key>

# Cloud SQL PostgreSQL Checkpointing
CLOUD_SQL_POSTGRES_URL=postgresql+asyncpg://postgres:secure_cluster_pass@136.113.87.178:5432/genlock_sentinel
ADK_SESSION_DB_URL=sqlite+aiosqlite:///./sentinel_local.db

# Grafana Cloud MCP Observability
GRAFANA_URL=https://magentaparfait3455.grafana.net
GRAFANA_SERVICE_ACCOUNT_TOKEN=<your-grafana-token>
GRAFANA_LOKI_DATASOURCE_UID=grafanacloud-logs
GRAFANA_TEMPO_DATASOURCE_UID=grafanacloud-traces

# Operational Thresholds
CONFIDENCE_FLOOR=0.75
FINANCIAL_THRESHOLD_USD=250.0
MAX_TOOL_RETRIES=3
SYNC_OFFSET_THRESHOLD_US=150.0
```

---

## Operations HTTP & SSE API

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/healthz` | Liveness and readiness health check probe. |
| `GET` | `/sessions/{id}/stream` | Server-Sent Events (SSE) stream for AG-UI console. |
| `POST` | `/sessions/{id}/inject-drift` | Synthetic drift telemetry ingestion endpoint. |
| `POST` | `/sessions/{id}/events/{id}/decision` | HITL supervisor decision endpoint (`approve` / `deny`). |
| `POST` | `/sessions/{id}/stop` | Emergency take stop button (irreversible session halt). |
| `POST` | `/sessions/{id}/events/{id}/feedback` | Post-hoc supervisor diagnosis accuracy annotation. |

---

## Running & Testing

```bash
# Install and lock dependencies
uv sync

# Run ASGI dev server
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Run full 227-test automated test suite
uv run pytest tests/ -v
```
