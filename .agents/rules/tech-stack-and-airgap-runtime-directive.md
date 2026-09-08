---
trigger: always_on
---

You MUST strictly use the project's authorized Google Cloud & Grafana stack:

* **LLM Models:** Gemini 3.1 Pro (Reasoning in Node 3) and Gemini 3.7 Flash (Execution/Triage in Nodes 2 & 5) via Google ADK 2.x and `google-cloud-aiplatform[agent_engines,adk]>=1.101.0`.

* **Orchestration:** Google Agent Development Kit (ADK) 2.x Workflow Runtime (7 graph nodes) with `LongRunningFunctionTool` for durable HITL pause/resume.

* **Observability Integration:** Grafana MCP Server (`grafana/mcp-grafana`) for Prometheus metrics and Loki logs; Tempo native MCP (`/api/mcp`) for distributed tracing.

* **Database & Checkpointer:** Cloud SQL for PostgreSQL (`asyncpg`) with local development fallback to SQLite (`aiosqlite`) via ADK session adapter — NOT synchronous DB drivers.

* **Security Layer:** Google Model Armor for MCP tool-response prompt-injection and sensitive-data sanitization.

* **Backend Framework:** Python 3.11+, FastAPI, Uvicorn, HTTPX, Pydantic V2 (`pydantic>=2.9,<3`).

* **Frontend Console:** React 18, TypeScript, Vite, Tailwind CSS, Shadcn/UI, connected via Server-Sent Events (SSE) using `@ag-ui/client` and `adk-agui-middleware`.

* **Package Managers:** `uv` (backend) and `pnpm` (frontend).

UNDER NO CIRCUMSTANCES should you write code importing unauthorized or legacy libraries (e.g., `langchain`, `crewai`, `openai`, `anthropic`, synchronous `requests`, or raw `while True` polling loops).
