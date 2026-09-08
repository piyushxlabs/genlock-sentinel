# TECHNICAL NOTES

---
## Step 1 — Local SQLite Fallback alongside Cloud SQL
**Decision:** Configured `ADK_SESSION_DB_URL=sqlite+aiosqlite:///./sentinel_local.db` with `CLOUD_SQL_POSTGRES_URL` in `backend/.env` for offline development mode, while preserving PostgreSQL asyncpg in `.env.example` as the authoritative production checkpoint backend.
**Reason:** Allows rapid local development and air-gapped unit testing without mandatory live Cloud SQL access, strictly adhering to `AGENT_MASTER_PLAN.md` Section 2 guidelines while enforcing non-blocking `aiosqlite`.
**Impact:** Node-level tests can run locally without external database infrastructure, transitioning to Cloud SQL for end-to-end verification in Steps 19–21.
---

---
## Step 2 — pnpm v11 Build Scripts Approval & Pydantic V2 Model Configuration
**Decision:** Executed `pnpm approve-builds --all` in `frontend/` to approve native `esbuild` script execution required by Vite; configured `backend/scripts/simulate_drift.py` with `model_config = ConfigDict(strict=True, extra="forbid")`.
**Reason:** pnpm v11 enforces zero-trust execution of package lifecycle scripts by default. Pydantic V2 strict mode enforces the project's constitutional async I/O and schema validation mandate (`async-io-and-pydantic-validation-mandate.md`).
**Impact:** Guarantees standard Vite bundling in frontend tooling and ensures all synthetic drift events conform to strict schema boundaries.
---
