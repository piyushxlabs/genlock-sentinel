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

---
## Step 3 — Context File Generation
Step 3 — No deviations from spec.
---

---
## Step 4 — Directory Scaffolding
Step 4 — No deviations from spec.
---

---
## Step 5 — ADK 2.8.0 StreamingMode.SSE & Vertex AI Environment Adapter
**Decision:** Configured `StreamingMode.SSE` via `google.adk.agents._streaming_mode.StreamingMode` in `RunConfig` and implemented dynamic credential path normalization to absolute paths for `GOOGLE_APPLICATION_CREDENTIALS` with `GOOGLE_GENAI_USE_VERTEXAI="true"` in `backend/src/main.py`.
**Reason:** ADK 2.8.0 encapsulates `StreamingMode` within the agents package; relative credential paths like `./gcp-key.json` fail if invoked from subdirectories unless resolved relative to `backend/`. Vertex AI mode ensures seamless enterprise token resolution.
**Impact:** Guarantees deterministic SSE streaming and robust authentication across both CLI test runs and FastAPI ASGI worker processes.
---
