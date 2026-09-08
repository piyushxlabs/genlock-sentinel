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

---
## Step 6 — Dynamic Model Configuration & Dual-Mode Structured Outputs
**Decision:** Implemented `backend/src/agents/model_config.py` to dynamically pull `GEMINI_REASONING_MODEL` (e.g. `gemini-3.8-flash` / `gemini-3.1-pro`) and `GEMINI_FAST_MODEL` (e.g. `gemini-3.7-flash`) from `backend/.env` without hardcoding; enforced `temperature=0.0` for reasoning; codified shared static prompt for context caching; and implemented exponential backoff (1s, 2s, 4s) with Section 9.1 mock fallback.
**Reason:** Allows configuring independent models for reasoning vs triage/HITL roles dynamically; satisfies the constitutional zero-hallucination mandate; guarantees uninterrupted testing even during temporary upstream API demand spikes.
**Impact:** Nodes 2, 3, and 5 can consume their designated model tiers with strict Pydantic V2 type validation and resilient error recovery.
---

---
## Step 7 — State Reducers and Immutability Enforcement
**Decision:** Implemented pure functional reducer primitives (`reduce_immutable`, `reduce_merge_by_key`, `reduce_append_only`, `reduce_last_write_wins`) and a central mutation dispatcher `reduce_state` in `backend/src/state/reducers.py` with custom `StateValidationError` (derived from `AgentError`), strictly forbidding extra delta fields.
**Reason:** Satisfies `state-invariants-and-tool-preconditions.md` and `code-level-verification-over-model-discretion.md`. Enforces that `session_id` and `config` cannot drift mid-session, concurrent node drift events cannot collide, and audit trails (`diagnosis_history`, `remediation_log`, `error_logs`) can never lose entries under sequential or asynchronous state mutations.
**Impact:** Provides bulletproof typed state mutations for ADK Workflow runtime nodes, SSE streaming state-deltas, and session checkpointing backends.
---

---
## Step 8 — Checkpointing with ADK DatabaseSessionService & Async Engines
**Decision:** Implemented `backend/src/state/checkpointing.py` using `google.adk.sessions.DatabaseSessionService` backed by async database engines (`sqlite+aiosqlite` for local dev/testing and `postgresql+asyncpg` for production Cloud SQL), adding `sqlalchemy>=2.0` to `backend/pyproject.toml`; implemented atomic session updates via ADK `Event(actions=EventActions(state_delta=...))` and added pre-validators for enum deserialization.
**Reason:** Fulfills `AGENT_MASTER_PLAN.md` Section 4 Step 4 and Section 10 Step 8, strictly honoring `async-io-and-pydantic-validation-mandate.md` (no blocking DB calls). ADK's `DatabaseSessionService` handles table creation, row locking, and session lifecycle natively while maintaining zero-loss durability during HITL pause/resume.
**Impact:** Enables durable graph execution checkpointing, seamless recovery after interruptions or crashes, and smooth resumption of HITL approval workflows in subsequent steps.
---

---
## Step 9 — Confirmation of No Long-Term Memory
**Decision:** Confirmed and codified the strict absence of long-term memory systems, vector databases, and semantic search frameworks (`chromadb`, `pinecone`, `qdrant`, `weaviate`, `faiss`, `pgvector`, `milvus`, `langchain`, `crewai`, `llama-index`). Verified that `GenlockSentinelState` remains strictly session-scoped with no embedding models or cross-session persistence.
**Reason:** Fulfills `AGENT_MASTER_PLAN.md` Section 1 (Explicit Non-Goals), Section 4 Step 5, Section 10 Step 9, and `AGENT_ORCHESTRATION_BLUEPRINT.md` Section 7. Genlock Sentinel is an SRE cluster integrity agent operating on real-time deterministic metrics, logs, and traces. The three root causes are fixed deterministic categories, not retrieved documents. Adding vector storage would introduce unwarranted architectural bloat, token latency, and potential hallucination vectors.
**Impact:** Guarantees an air-gapped, lean, deterministic agent runtime with zero cross-session state contamination or credential leakage.
---

---
## Step 10 — Tool Registration Across Node-Tool Access Matrix
**Decision:** Implemented dual-schema bindings (Pydantic V2 models with `model_config = ConfigDict(strict=True, extra="forbid")` and strict MCP JSON schemas with `additionalProperties: False`) for all 9 agent tools. Bound Tools 1–3 to Evidence Triage with active drift event preconditions and silence-over-guessing error handling; bound Tools 4–6 to Autonomous Remediation with code-level diagnosis category and confidence floor verification; bound Tools 7–9 to Post-Approval Handling with mandatory `approval_state == "approved"` and matching proposed action verification.
**Reason:** Strictly implements `node-tool-access-matrix-restrictions.md`, `state-invariants-and-tool-preconditions.md`, `code-level-verification-over-model-discretion.md`, and `defensive-execution-structured-outputs-and-fallbacks.md`. Prevents cognitive nodes from holding actuation tools, blocks unauthorized state transitions before dispatch, and prevents hallucinated log or trace fabrications upon query failure.
**Impact:** Ensures all tools adhere to zero-trust structural boundaries and guarantees deterministic dispatch safety during graph execution in Step 11 and Step 12.
---
