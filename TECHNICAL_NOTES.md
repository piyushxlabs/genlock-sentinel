# TECHNICAL NOTES

---
## Step 1 — Local SQLite Fallback alongside Cloud SQL
**Decision:** Configured `ADK_SESSION_DB_URL=sqlite+aiosqlite:///./sentinel_local.db` with `CLOUD_SQL_POSTGRES_URL` in `backend/.env` for offline development mode, while preserving PostgreSQL asyncpg in `.env.example` as the authoritative production checkpoint backend.
**Reason:** Allows rapid local development and air-gapped unit testing without mandatory live Cloud SQL access, strictly adhering to `AGENT_MASTER_PLAN.md` Section 2 guidelines while enforcing non-blocking `aiosqlite`.
**Impact:** Node-level tests can run locally without external database infrastructure, transitioning to Cloud SQL for end-to-end verification in Steps 19–21.
---
