---
trigger: always_on
---

All backend Python code must be 100% type-hinted with Pydantic V2 models and use non-blocking `async`/`await` for all I/O operations (FastAPI endpoints, Cloud SQL PostgreSQL session adapter via `asyncpg`, SQLite fallback via `aiosqlite`, Gemini model calls via Google ADK/`google-genai`, and Grafana/Tempo MCP client lookups).

Synchronous blocking I/O (`requests`, `psycopg2`, `time.sleep`) is strictly prohibited in agent nodes and tools.

All structured outputs (`EvidenceBundleExtraction`, `RootCauseDiagnosis`, `HITLCardPackage`) must use native Pydantic V2 models with strict schema enforcement:

`model_config = ConfigDict(strict=True, extra="forbid")`

Never parse LLM reasoning, telemetry payloads, or JSON responses using manual string manipulation, slicing, or regex.
