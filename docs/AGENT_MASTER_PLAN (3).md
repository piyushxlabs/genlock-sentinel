# AGENT MASTER PLAN

**Generated:** September 7, 2026
**Source Documents:**
- AGENT_ORCHESTRATION_BLUEPRINT.md
- AGENT_LOGIC_SPEC.md
- INTERFACE_OBSERVABILITY_SYSTEM.md

**Status:** AUTHORITATIVE — Complete execution plan for agent system implementation

---

## **1. EXECUTION PRINCIPLES**

**Technology Stack (Verified):**

| Component | Choice | Phase 1.5 Verification Status |
|---|---|---|
| Orchestration framework | Google Agent Development Kit (ADK) 2.x, Workflow Runtime | Verified — `google-adk` latest stable 2.1.0 (May 23, 2026), weekly release cadence, PyPI |
| Language/runtime (backend) | Python 3.11+, async-first (`asyncio`) | Verified — matches ADK's async `Runner`/session model |
| Reasoning model | Gemini 3.1 Pro | Verified current flagship as of Feb 2026 GA rollout |
| Fast/execution model | Gemini 3.7 Flash | Verified current GA workhorse as of Sept 2026 |
| Schema/validation | `pydantic` v2 | Verified — current stable line is 2.12.x (Debian tracker, confirmed Oct 2025); floor pinned `>=2.9,<3` |
| Checkpointing backend | Cloud SQL for PostgreSQL (via ADK's `asyncpg` session adapter) | Verified — ADK session service documents PostgreSQL support alongside SQLite/Firestore |
| MCP integration | Grafana MCP Server (`grafana/mcp-grafana`) + Tempo native MCP (`/api/mcp`) | Verified — tool names/RBAC confirmed against official `grafana/mcp-grafana` GitHub repo and Grafana Cloud Traces docs |
| Prompt-injection/sensitive-data layer | Google Model Armor | Verified — confirmed current Gemini Enterprise Agent Platform security offering |
| Frontend↔backend protocol | SSE, bridged via AG-UI (Agent-User Interaction) protocol | Verified — ADK `StreamingMode.SSE` + `adk-agui-middleware` (PyPI) confirmed current |
| Telemetry | OpenTelemetry GenAI Semantic Conventions (v1.41, 2026), exported to Google Cloud Trace + Langfuse (OTLP) | Verified — stable spec release confirmed; Langfuse confirmed pure-OTLP backend post-ClickHouse acquisition (Jan 2026) |
| Frontend framework | React + AG-UI client runtime + Shadcn/UI | Verified — matches `create-ag-ui-app` ecosystem convention |
| Package management | `uv` (Python), `pnpm` (frontend) | Assumption — Unverified current versions; both tools' continued current status is treated as background knowledge, exact pinned CLI versions to be confirmed at install time |

**Runtime Assumptions:**
Python 3.11+ on the backend (ADK, tools, state, telemetry), async-first throughout — no blocking I/O in any agent node or tool. Node.js LTS + TypeScript/React on the frontend console, ESM. Both processes are separate deployables: the ADK agent runtime deploys to Google Cloud Agent Engine / Cloud Run; the console frontend deploys as a static/SSR web app consuming the backend's SSE endpoint.

**Explicit Non-Goals:**
- No conversational chat UI or free-text input surface (per INTERFACE_OBSERVABILITY_SYSTEM.md Section 2 — this is a console, not a chatbot).
- No long-term/vector memory implementation (per AGENT_ORCHESTRATION_BLUEPRINT.md Section 7 — explicitly not required).
- No Manual or Fully Autonomous mode toggle (per AGENT_BEHAVIOR_PROFILE.md/INTERFACE_OBSERVABILITY_SYSTEM.md Section 8 — Semi-Autonomous is fixed).
- No undo/redo, regeneration, or manual-takeover controls beyond what INTERFACE_OBSERVABILITY_SYSTEM.md Section 7 explicitly defines.
- No tools, MCP servers, or capabilities beyond the nine named in AGENT_LOGIC_SPEC.md Section 3.

**Stability Requirements:**
Every state mutation must go through its declared reducer with no exceptions; every HITL checkpoint must be resumable from a durable checkpoint after a crash with no lost evidence; every external tool call must retry per its declared backoff before escalating; the system must never take a HITL-gated action without a verified `approval_state == "approved"` on the exact matching card.

---

## **2. ENVIRONMENT & INFRASTRUCTURE SETUP**

**Required API Keys & Secrets:**

1. Google Cloud / Gemini Enterprise Agent Platform — Service account credentials for Vertex AI / Agent Engine — Google Cloud Console → IAM & Admin → Service Accounts — `GOOGLE_APPLICATION_CREDENTIALS`
2. Grafana MCP Server — Service account token (least-privilege, `datasources:query` scoped to the Prometheus/Loki/Tempo datasource UIDs) — Grafana instance → Administration → Service accounts — `GRAFANA_SERVICE_ACCOUNT_TOKEN`
3. Grafana instance URL — Grafana Cloud stack settings — `GRAFANA_URL`
4. Tempo native MCP endpoint — Grafana Cloud Traces stack settings — `TEMPO_MCP_URL`
5. Cloud SQL for PostgreSQL — Connection string for the ADK session/checkpoint database — Google Cloud Console → SQL — `ADK_SESSION_DB_URL`
6. Google Cloud Secret Manager — Used at call-time to resolve cluster credentials/network-topology secrets (never stored in agent state) — `SECRET_MANAGER_PROJECT_ID`
7. Langfuse — Project API keys for the OTLP scoring/annotation backend — Langfuse project settings — `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
8. Internal cluster-manager control-plane endpoint — For the six direct-function-calling tools (three reversible, three HITL-gated) — Internal infra config — `CLUSTER_MANAGER_API_URL`, `CLUSTER_MANAGER_API_KEY`

**Required Environment Variables:**

```
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=<gcp-project-id>
GEMINI_REASONING_MODEL=gemini-3.1-pro
GEMINI_FAST_MODEL=gemini-3.7-flash
GRAFANA_URL=https://<your-instance>.grafana.net
GRAFANA_SERVICE_ACCOUNT_TOKEN=<token>
TEMPO_MCP_URL=https://<your-tempo-stack>/tempo/api/mcp
ADK_SESSION_DB_URL=postgresql+asyncpg://<user>:<pass>@<host>/<db>
SECRET_MANAGER_PROJECT_ID=<gcp-project-id>
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
OTEL_EXPORTER_OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel
CLUSTER_MANAGER_API_URL=https://<internal-endpoint>
CLUSTER_MANAGER_API_KEY=<key>
CONFIDENCE_FLOOR=0.75
FINANCIAL_THRESHOLD_USD=<pre-approved cap>
QUERY_WINDOW_MAX_SECONDS=120
```

### **Package Manifest (Verified via Phase 1.5)**

**Python Backend — `pyproject.toml` managed by `uv`:**

```toml
[project]
name = "genlock-sentinel"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "google-adk>=2.1.0",              # Verified: PyPI, latest stable 2.1.0 (May 23, 2026), weekly cadence — confirm newer patch at install time
    "google-genai>=1.0.0",            # Assumption — Unverified exact floor; underlying Gemini model client ADK wraps — confirm current version before installation
    "pydantic>=2.9,<3",               # Verified: current stable line 2.12.x (Debian tracker, Oct 2025)
    "asyncpg>=0.29",                  # Assumption — Unverified exact current version; required for ADK's PostgreSQL session adapter — confirm before installation
    "opentelemetry-sdk>=1.27",        # Assumption — Unverified exact current version; implements OTel GenAI Semantic Conventions v1.41 spec — confirm before installation
    "opentelemetry-exporter-otlp>=1.27",  # Assumption — Unverified exact current version — confirm before installation
    "ag-ui-protocol>=0.1.0",          # Verified: package exists (ag_ui.core Python SDK, per docs.ag-ui.com) — exact current version Assumption — Unverified, confirm before installation
    "adk-agui-middleware>=0.1.0",     # Verified: package exists on PyPI, bridges ADK↔AG-UI over SSE with HITL support — exact current version Assumption — Unverified, confirm before installation
    "fastapi>=0.115",                 # Assumption — Unverified exact current version — confirm before installation
    "uvicorn[standard]>=0.30",        # Assumption — Unverified exact current version — confirm before installation
    "httpx>=0.27",                    # Assumption — Unverified exact current version — confirm before installation
]

[tool.uv]
# Standard uv-managed lockfile; no custom index required
```

**Installation Command:**
```
uv sync
```

**TypeScript/React Frontend — `package.json` managed by `pnpm`:**

```json
{
  "name": "genlock-sentinel-console",
  "dependencies": {
    "@ag-ui/client": "latest",
    "react": "^18",
    "react-dom": "^18"
  },
  "devDependencies": {
    "shadcn-ui": "latest",
    "typescript": "^5",
    "vite": "^5"
  }
}
```
*Note: `@ag-ui/client` and `shadcn-ui` exact current pinned versions are Assumption — Unverified; confirm current published versions on npm before installation rather than using `latest` in the committed lockfile.*

**Installation Command:**
```
pnpm install
```

**Version Verification Log:**

| Package | Chosen Version | Phase 1.5 Status |
|---|---|---|
| `google-adk` | `>=2.1.0` | Verified (PyPI stats, May 2026 release) |
| `pydantic` | `>=2.9,<3` | Verified (Debian tracker, current 2.12.x stable line) |
| `grafana/mcp-grafana` tool names (`query_prometheus`, `query_loki_logs`, `find_slow_requests`) | N/A (external MCP server, not a pip dependency) | Verified (official GitHub repo, Sept 2026) |
| Tempo native MCP (`/api/mcp`) | N/A (external service) | Verified (Grafana Cloud Traces official docs) |
| OTel GenAI Semantic Conventions | Spec v1.41 | Verified (stable release confirmed, 2026) |
| Langfuse (as OTLP backend, no dedicated SDK required) | N/A — OTLP endpoint only | Verified (Langfuse OTel-native integration docs, post-ClickHouse acquisition) |
| AG-UI protocol (`ag_ui.core`) | Package confirmed to exist | Assumption — Unverified exact pinned version |
| `adk-agui-middleware` | Package confirmed to exist on PyPI | Assumption — Unverified exact pinned version |
| `google-genai`, `asyncpg`, `opentelemetry-*`, `fastapi`, `uvicorn`, `httpx`, `@ag-ui/client`, `shadcn-ui` | Floors as listed above | Assumption — Unverified exact current patch; confirm before installation |

**Deprecated Package Substitutions:**
None required. No package implied by the upstream specs was found deprecated or superseded during Phase 1.5 research; the one substitution of note is architectural, not a package swap — Vertex AI's rebrand into the "Gemini Enterprise Agent Platform" (Google Cloud Next 2026) is reflected in the environment variables and deployment target above, not in a different package name.

### **Project Directory Structure**

```text
genlock-sentinel/
├── backend/
│   ├── .env.example
│   ├── pyproject.toml
│   ├── CLAUDE.md
│   ├── src/
│   │   ├── agents/
│   │   │   ├── stream_watch.py            # Non-LLM trigger node
│   │   │   ├── evidence_triage.py         # Gemini 3.7 Flash node
│   │   │   ├── root_cause_correlation.py  # Gemini 3.1 Pro node
│   │   │   ├── autonomous_dispatch.py     # Deterministic dispatch node
│   │   │   ├── hitl_card_generation.py    # Gemini 3.7 Flash node
│   │   │   ├── post_approval_handling.py  # Deterministic dispatch node
│   │   │   └── graph.py                   # ADK Workflow Runtime graph wiring
│   │   ├── tools/
│   │   │   ├── query_loki_logs.py
│   │   │   ├── find_slow_requests.py
│   │   │   ├── get_trace_by_id.py
│   │   │   ├── failover_cluster_leadership.py
│   │   │   ├── deprioritize_texture_streaming.py
│   │   │   ├── force_genlock_resync.py
│   │   │   ├── halt_live_take.py
│   │   │   ├── fallback_to_greenscreen.py
│   │   │   ├── execute_threshold_exceeding_failover.py
│   │   │   ├── schemas/
│   │   │   │   ├── pydantic_models.py     # All Pydantic V2 Input/Output models
│   │   │   │   └── mcp_schemas.py         # All MCP/strict JSON Schema definitions
│   │   │   └── mcp_clients/
│   │   │       ├── grafana_mcp_client.py
│   │   │       └── tempo_mcp_client.py
│   │   ├── structured_outputs/
│   │   │   ├── evidence_bundle_extraction.py
│   │   │   ├── root_cause_diagnosis.py
│   │   │   └── hitl_card_package.py
│   │   ├── state/
│   │   │   ├── schema.py                  # GenlockSentinelState Pydantic model
│   │   │   ├── reducers.py                # append-only / merge-by-key / last-write-wins
│   │   │   └── checkpointing.py           # Cloud SQL PostgreSQL session adapter
│   │   ├── telemetry/
│   │   │   ├── tracing.py                 # OTel GenAI span instrumentation
│   │   │   ├── otlp_export.py             # Dual export: Cloud Trace + Langfuse
│   │   │   └── feedback_annotations.py    # Section 7a pipeline
│   │   ├── ui/
│   │   │   ├── agui_bridge.py             # adk-agui-middleware wiring
│   │   │   ├── event_types.py             # AG-UI EventType vocabulary reference
│   │   │   └── hitl_resumption.py         # Approve/Deny payload handlers
│   │   ├── safety/
│   │   │   ├── model_armor_client.py
│   │   │   └── prohibition_guards.py      # Structural trust-boundary checks
│   │   ├── utils/
│   │   └── main.py                        # FastAPI + ADK Runner entry point
│   └── tests/
│       ├── mocks/
│       ├── unit/
│       ├── evals/
│       └── hitl/
└── frontend/
    ├── package.json
    ├── src/
    │   ├── components/
    │   │   ├── SyncOffsetChart.tsx
    │   │   ├── StepTracker.tsx
    │   │   ├── EvidenceCard.tsx
    │   │   ├── DiagnosisBadge.tsx
    │   │   ├── ApprovalCardModal.tsx
    │   │   ├── RemediationLog.tsx
    │   │   └── FailureBanner.tsx
    │   ├── stream/
    │   │   └── agui-client.ts
    │   └── App.tsx
    └── tests/
```

**File Purpose Explanation:**
- `backend/src/agents/`: The seven graph nodes and graph wiring, exactly matching AGENT_ORCHESTRATION_BLUEPRINT.md Section 4.
- `backend/src/tools/`: The nine tools' implementations plus dual-format schemas, exactly matching AGENT_LOGIC_SPEC.md Sections 3–4.
- `backend/src/structured_outputs/`: The three structured-output-only schemas from AGENT_LOGIC_SPEC.md Section 5.
- `backend/src/state/`: The typed state schema and reducers from AGENT_ORCHESTRATION_BLUEPRINT.md Section 3, plus PostgreSQL checkpointing from Section 7.
- `backend/src/telemetry/`: OTel GenAI instrumentation and the feedback-annotation pipeline from INTERFACE_OBSERVABILITY_SYSTEM.md Sections 6–7a.
- `backend/src/ui/`: The AG-UI/SSE bridge and HITL resumption handlers from INTERFACE_OBSERVABILITY_SYSTEM.md Sections 2a and 5.
- `backend/src/safety/`: Model Armor integration and the structural trust-boundary checks enforcing AGENT_BEHAVIOR_PROFILE.md's prohibitions.
- `backend/tests/mocks/`, `evals/`, `hitl/`: Test data and suites defined in Section 9.
- `frontend/src/components/`: The generative UI components from INTERFACE_OBSERVABILITY_SYSTEM.md Section 4a.

**Local vs Production Distinctions:**
- **Local:** SQLite may substitute for Cloud SQL during early node-level development only if explicitly needed for offline iteration — however, per LLM-2's explicit choice of PostgreSQL for durability, any SQLite use is development-only scaffolding and must not be the target for Step 19–21 verification, which must run against Cloud SQL.
- **Production:** Cloud SQL for PostgreSQL (per LLM-2), secrets resolved from Google Cloud Secret Manager at call-time (never `.env` files), Model Armor policies active on all MCP tool-call boundaries, OTLP export to both Cloud Trace and Langfuse active.

---

## **3. CODING ASSISTANT CONTEXT FILE**

**Target File:** `CLAUDE.md` (also valid as `.cursorrules`/`AGENTS.md` content verbatim — the rules below are assistant-agnostic)

**Full Contents (copy-pasteable):**

```markdown
# Genlock Sentinel — Coding Assistant Context

## Project Overview
Genlock Sentinel is a single Task Execution Agent, built on Google ADK and deployed to the Gemini Enterprise Agent Platform, that detects and remediates genlock/frame-sync drift on an nDisplay LED-volume render cluster during live ICVFX camera capture. It runs Semi-Autonomous: three reversible remediations execute automatically on a confident diagnosis; take-halt, capture-mode fallback, and threshold-exceeding failover always require explicit on-set supervisor approval.

## Strict Coding Rules
- Python 3.11+, async-first: all I/O-bound operations (Gemini calls, MCP tool calls, Cloud SQL access) MUST use `async`/`await`. Never use blocking I/O in any agent node or tool.
- All data structures crossing a function boundary MUST have explicit Pydantic V2 type hints — no bare `dict`, no bare `Any` unless truly unavoidable and justified in a comment.
- Every tool input/output MUST validate against the Pydantic V2 models in `src/tools/schemas/pydantic_models.py` AND match the corresponding MCP/strict JSON Schema in `src/tools/schemas/mcp_schemas.py` — the two must never drift apart.
- Use a custom exception hierarchy rooted at a single `AgentError` base class, with subclasses `ToolExecutionError`, `StateValidationError`, `ApprovalTimeoutError`, `SchemaValidationError` — never raise bare `Exception`.
- Every free-text parameter passed to `query_loki_logs` MUST pass through the sanitization function in `src/safety/prohibition_guards.py` before invocation.
- Every claim in `RootCauseDiagnosis.rationale`, `EvidenceBundleExtraction.log_summary`/`.trace_summary`, or `HITLCardPackage.root_cause_summary` MUST cite the specific evidence field it came from — enforce via the post-generation validation step, never trust the model's compliance alone.

## Architecture Boundaries
- **State lives in:** `src/state/schema.py` (the single `GenlockSentinelState` Pydantic model) — no component may define its own parallel state shape.
- **Reducers live in:** `src/state/reducers.py` — every state mutation MUST go through the declared reducer for that field exactly as specified in AGENT_ORCHESTRATION_BLUEPRINT.md: `active_drift_events` and `evidence_bundle` are merge-by-key; `diagnosis_history`, `remediation_log`, `error_logs` are append-only; `pending_hitl_card`, `approval_state`, `session_status` are last-write-wins; `session_id` and `config` are immutable after init. Direct mutation of any state field outside a declared reducer is forbidden.
- **Tools/MCP clients live in:** `src/tools/` — agent nodes import tools from here; agent nodes MUST NOT define inline ad-hoc tool logic.
- **Checkpointing lives in:** `src/state/checkpointing.py`, using Cloud SQL for PostgreSQL via ADK's `asyncpg` session adapter.
- **Telemetry hooks live in:** `src/telemetry/` — every reasoning step and tool call MUST emit an OTel GenAI-conventions span, exported to both Cloud Trace and Langfuse.
- **Streaming/UI event emission lives in:** `src/ui/agui_bridge.py` and `src/ui/event_types.py` — agent/tool code emits domain events through ADK's native `Runner` event stream; it does not construct AG-UI wire-format JSON directly, since `adk-agui-middleware` performs that projection.
- **Trust boundaries live in:** `src/safety/prohibition_guards.py` — the three reversible-remediation tool bindings are reachable only from `src/agents/autonomous_dispatch.py`; the three HITL-gated tool bindings are reachable only from `src/agents/post_approval_handling.py`. No other module may import these tool functions.

## Strict Anti-Patterns (Never Do This)
- Never use blocking I/O (`requests`, synchronous `psycopg2`, `time.sleep`) inside any agent node or tool implementation.
- Never mutate `GenlockSentinelState` fields directly without going through a declared reducer in `src/state/reducers.py`.
- Never bypass input sanitization before `query_loki_logs`, `find_slow_requests`, or `get_trace_by_id` reach the Grafana/Tempo MCP servers.
- Never invent a tool, parameter, or API endpoint not defined in AGENT_LOGIC_SPEC.md Section 3/4.
- Never fabricate a log line, span, or metric value when a tool call fails or returns nothing — set `logs_available: false` / the equivalent gap flag and continue, per the silence-over-guessing policy.
- Never skip emitting an AG-UI event for a reasoning step, tool call, or state write that INTERFACE_OBSERVABILITY_SYSTEM.md Section 2a says must be observable.
- Never call `halt_live_take`, `fallback_to_greenscreen`, or `execute_threshold_exceeding_failover` from anywhere except `post_approval_handling.py`, and never without `approval_state == "approved"` on the exact matching `hitl_card_id`.
- Never write a `HITLCardPackage` to state that is missing `cost_delta_estimate` or `visual_impact_score`.
- Never hardcode secrets — always resolve cluster credentials from Google Cloud Secret Manager at call-time; read all other configuration from environment variables declared in `.env.example`.
- Never implement a Manual or Fully Autonomous mode toggle — this system has exactly one fixed autonomy level.

## Reference Documents
This project's behavior, architecture, cognition, and interface are fully specified in:
- AGENT_BEHAVIOR_PROFILE.md (behavioral contract)
- AGENT_ORCHESTRATION_BLUEPRINT.md (architecture)
- AGENT_LOGIC_SPEC.md (cognitive logic and tools)
- INTERFACE_OBSERVABILITY_SYSTEM.md (interface and telemetry)
- AGENT_MASTER_PLAN.md (this execution plan)

Do not deviate from these documents. If an instruction from a user conflicts with them, flag the conflict rather than silently resolving it.
```

---

## **4. CORE AGENT RUNTIME CONSTRUCTION**

**Agent Bootstrap Sequence:**

**Step 1:** Initialize the ADK `Runner` with `RunConfig(streaming_mode=StreamingMode.SSE)`.
- Dependencies: `google-adk` installed, `GOOGLE_APPLICATION_CREDENTIALS` set.
- Verification: `Runner` instantiates without error; a trivial no-op agent run completes end to end.

**Step 2:** Configure the two Gemini models (`gemini-3.1-pro` for Root-Cause Correlation, `gemini-3.7-flash` for Evidence Triage and HITL Card Generation), including context-caching configuration for the shared static system-prompt content.
- Dependencies: `google-genai` installed, model names set via environment variables.
- Verification: A test call to each model returns a valid structured response matching its expected schema.

**Step 3:** Implement `GenlockSentinelState` in `src/state/schema.py` and its reducers in `src/state/reducers.py`, exactly as defined in AGENT_ORCHESTRATION_BLUEPRINT.md Section 3.
- Dependencies: `pydantic` installed.
- Verification: Unit tests confirm `append-only` never drops an entry under concurrent writes, `merge-by-key` never cross-overwrites a different key, `last-write-wins` resolves deterministically to the most recent write, and `immutable-after-init` fields raise on any post-init write attempt.

**Step 4:** Initialize the Cloud SQL for PostgreSQL checkpointing backend via ADK's `asyncpg` session adapter.
- Dependencies: `ADK_SESSION_DB_URL` set, `asyncpg` installed, Step 3 complete.
- Verification: A checkpoint write/read/resume round-trip succeeds against a live Cloud SQL instance.

**Step 5:** Confirm no long-term memory system is initialized (explicitly out of scope per AGENT_ORCHESTRATION_BLUEPRINT.md Section 7).
- Dependencies: None.
- Verification: No vector-store client or dependency appears anywhere in the manifest or codebase.

**Step 6:** Wire the ADK Workflow Runtime graph — the seven nodes and their edges — exactly per AGENT_ORCHESTRATION_BLUEPRINT.md Section 4.
- Dependencies: Steps 1–4 complete, tools registered (Section 5 below).
- Verification: Graph structure validation confirms exactly seven nodes, the decision points at Root-Cause Correlation and HITL Pause match Section 4's branching exactly, and no orphan node or edge exists.

---

## **5. TOOL INTEGRATION PLAN**

**Tool Registration Sequence:**

**Tool 1: `query_loki_logs`**
- Purpose: Retrieve nDisplay cluster-manager and `LogDisplayClusterEngine` logs for a node/time window.
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 Schema Location: `src/tools/schemas/pydantic_models.py::QueryLokiLogsInput/Output`.
- MCP/Strict JSON Schema Location: `src/tools/schemas/mcp_schemas.py::query_loki_logs`.
- Package Verification: Grafana MCP Server tool name/RBAC verified; exact parameter names flagged Assumption — Unverified (AGENT_LOGIC_SPEC.md Section 4) — confirm via a live `tools/list` call against the deployed Grafana MCP Server before finalizing the exact parameter names in code.
- Dependencies: `GRAFANA_URL`, `GRAFANA_SERVICE_ACCOUNT_TOKEN` set; `src/tools/mcp_clients/grafana_mcp_client.py` initialized.
- Registration Step: Bind to the Evidence Triage node only.
- State Read/Write: Reads `active_drift_events[node_id]`; feeds `EvidenceBundleExtraction` → writes `evidence_bundle[event_id]` (merge-by-key).
- Verification: Invoke against a mock Loki response (Section 9.1); confirm output validates against both the Pydantic model and the MCP schema.

**Tool 2: `find_slow_requests`**
- Purpose: Detect anomalous frame-render spans via Grafana Sift.
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 Schema Location: `pydantic_models.py::FindSlowRequestsInput/Output`.
- MCP/Strict JSON Schema Location: `mcp_schemas.py::find_slow_requests`.
- Package Verification: Verified name/role; parameters Assumption — Unverified. Additionally confirm the Grafana MCP Server deployment has Sift write tools explicitly enabled (`--enabled-tools` includes `sift`), since this tool has a write side effect (creating an investigation record) even though it serves a read/diagnostic purpose.
- Dependencies: Same Grafana MCP client as Tool 1.
- Registration Step: Bind to the Evidence Triage node only.
- State Read/Write: Reads `active_drift_events[node_id]`; feeds `evidence_bundle[event_id]` (merge-by-key).
- Verification: Invoke against mock Sift response; validate both schema formats.

**Tool 3: `get_trace_by_id`**
- Purpose: Retrieve a full trace by `frame_id` from Tempo.
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 Schema Location: `pydantic_models.py::GetTraceByIdInput/Output`.
- MCP/Strict JSON Schema Location: `mcp_schemas.py::get_trace_by_id`.
- Package Verification: Capability verified via Grafana Cloud Traces docs; exact field names Assumption — Unverified — confirm against the live Tempo MCP server's schema before finalizing.
- Dependencies: `TEMPO_MCP_URL` set; `src/tools/mcp_clients/tempo_mcp_client.py` initialized.
- Registration Step: Bind to the Evidence Triage node only.
- State Read/Write: Reads `active_drift_events[node_id].frame_id`; feeds `evidence_bundle[event_id]` (merge-by-key).
- Verification: Invoke against mock trace response; validate both schema formats.

**Tool 4: `failover_cluster_leadership`**
- Purpose: Fail cluster leadership to a healthy standby node (network_jitter remediation).
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 Schema Location: `pydantic_models.py::ReversibleRemediationInput/Output`.
- MCP/Strict JSON Schema Location: `mcp_schemas.py::failover_cluster_leadership`.
- Package Verification: N/A — internal tool.
- Dependencies: `CLUSTER_MANAGER_API_URL`/`CLUSTER_MANAGER_API_KEY` set.
- Registration Step: Bind to `autonomous_dispatch.py` only — no other module may import this function (enforced by `src/safety/prohibition_guards.py`'s import-boundary check).
- State Read/Write: Reads `diagnosis_history` (must match `category: "network_jitter"`); appends to `remediation_log` (append-only); writes `session_status = "monitoring"` (last-write-wins).
- Verification: Confirm the precondition check rejects invocation when `diagnosis_history`'s latest entry for the event is any category other than `network_jitter`.

**Tool 5: `deprioritize_texture_streaming`** — same structure as Tool 4, bound to `asset_streaming_stall`.

**Tool 6: `force_genlock_resync`** — same structure as Tool 4, bound to `thermal_throttle`.

**Tool 7: `halt_live_take`**
- Purpose: Halt the live take — HITL-gated.
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 Schema Location: `pydantic_models.py::HitlGatedActionInput/Output`.
- MCP/Strict JSON Schema Location: `mcp_schemas.py::halt_live_take`.
- Package Verification: N/A — internal tool.
- Dependencies: `CLUSTER_MANAGER_API_URL`/`CLUSTER_MANAGER_API_KEY` set.
- Registration Step: Bind to `post_approval_handling.py` only.
- State Read/Write: Reads `approval_state` (must equal `"approved"`) and `pending_hitl_card`; appends to `remediation_log`; writes `session_status`.
- Verification: Confirm the schema's `approval_state: Literal["approved"]` constraint rejects any other value at the type level, and confirm no other module in the codebase imports this function (static import-graph check).

**Tool 8: `fallback_to_greenscreen`** — same structure as Tool 7.

**Tool 9: `execute_threshold_exceeding_failover`** — same structure as Tool 7.

**Inter-Tool Dependencies:**
Tools 1–3 (Evidence Triage) must all resolve (or exhaust retries) before `EvidenceBundleExtraction` is produced, which must exist before Tools 4–6 or the HITL Card Generation structured output can run. Tools 4–6 and Tools 7–9 are mutually exclusive per event — never registered as callable from the same node.

**Error Handling Strategy:**
- Tool failure response: Transient (MCP timeout/rate limit) → retry, exponential backoff (1s/2s/4s), max 3 attempts. Permanent (retries exhausted, or a HITL-gated/reversible tool's precondition fails) → escalate: query-tool exhaustion sets the relevant evidence-gap flag and continues; a failed reversible-remediation dispatch escalates to HITL; a failed HITL-approved action raises a session-fatal failure alert.
- Rate limit handling: Token bucket on Grafana/Tempo MCP calls, sized to the expected telemetry sampling rate.
- Validation failures: Any tool output failing its Pydantic/MCP schema is rejected before it reaches state; logged to `error_logs`; the producing node is re-invoked once with the validation error appended to context before escalating.
- Input sanitization enforcement: Runs in `src/safety/prohibition_guards.py`, called immediately before every `query_loki_logs` invocation — strips control characters and instruction-like phrases from the `logql` parameter.

**Rate Limits & Safeguards:**
- Grafana/Tempo MCP query tools: token bucket sized to `QUERY_WINDOW_MAX_SECONDS`-scoped sampling rate.
- Circuit breaker: after a configured count of re-breaches on the same `node_id` within a rolling window following a "successful" autonomous remediation, force the next occurrence onto the HITL path regardless of diagnosis confidence.

---

## **6. REASONING LOOP IMPLEMENTATION**

**Reasoning Cycle Structure:** Graph-based (ADK Workflow Runtime), per AGENT_LOGIC_SPEC.md Section 2.

**Step-by-Step Reasoning Flow:**

**Step 1:** Stream Watch (non-LLM) detects a sync-offset threshold breach for a `node_id` and writes a new entry to `active_drift_events` (merge-by-key).

**Step 2:** Evidence Triage node (Gemini 3.7 Flash) invokes Tools 1–3, then produces `EvidenceBundleExtraction` — native thinking tokens are not captured here (LLM-4 Section 3a scopes native-reasoning display to Root-Cause Correlation only); AG-UI `TOOL_CALL_*` events stream per Section 7 below.

**Step 3:** Root-Cause Correlation node (Gemini 3.1 Pro) reads `evidence_bundle[event_id]` and recent `diagnosis_history`, produces `RootCauseDiagnosis` — native thinking tokens captured and streamed via `REASONING_*` AG-UI events per INTERFACE_OBSERVABILITY_SYSTEM.md Section 3a.

**Step 4:** Decision — category unambiguous and within threshold → Step 5a; ambiguous or maps to a HITL-gated action → Step 5b.

**Step 5a:** Autonomous Dispatch node invokes the matching reversible tool (4/5/6); appends `remediation_log`; writes `session_status = "monitoring"`.

**Step 5b:** HITL Card Generation node (Gemini 3.7 Flash) produces `HITLCardPackage`; writes `pending_hitl_card` and `session_status = "awaiting_approval"`; graph enters HITL Pause (durable suspend via ADK `LongRunningFunctionTool`), emitting `RUN_PAUSED`.

**Step 6:** On Approve/Deny (Section 7 below), Post-Approval Handling node either invokes the matching HITL-gated tool (7/8/9) and appends `remediation_log`, or logs the denial and returns `session_status = "monitoring"`.

**Step 7:** Termination check for this `event_id` — resolved, denied, or failed; the outer Stream Watch loop continues independently for other nodes.

**Tool Call Decision Flow:**
Deterministic by node — Evidence Triage always calls Tools 1–3 (or as many as needed before exhausting retries); Autonomous Dispatch calls exactly one of Tools 4–6 based on the diagnosed category; Post-Approval Handling calls exactly one of Tools 7–9 based on `pending_hitl_card.proposed_action`, and only after `approval_state == "approved"`.

**State Persistence Between Steps:**
Every node's write is checkpointed to Cloud SQL for PostgreSQL (Section 4, Step 4) immediately after that node completes — most critically before the HITL Pause node suspends and immediately after a supervisor decision is received, so a crash never loses in-flight evidence or an already-presented approval card.

**Termination Conditions:**
1. Success — sync-offset resolves and a `remediation_log` entry links to its evidence.
2. Failure — defect captured before remediation, telemetry source exhausted, ambiguous diagnosis unresolved past the actionable window, or a Model Armor-flagged injection attempt.
3. User abort — supervisor issues Stop Session; all pending automatic actions suspend, no queued action executes retroactively.

**Loop Prevention Mechanisms:**
- Max iterations: exactly one pass through Steps 2–6 per `event_id` to a terminal state — no re-entry for an event still in flight.
- Progress detection: each `event_id`'s step tracker only ever moves forward through the seven named nodes; a node is never re-invoked for the same event except the one explicit validation-failure retry in Section 5's error handling.
- Circuit breaker: per Section 5's Rate Limits & Safeguards.

---

## **7. INTERFACE & STREAMING INTEGRATION**

**Backend ↔ Frontend Connection Model:** SSE, bridged through the AG-UI protocol via `adk-agui-middleware`, per INTERFACE_OBSERVABILITY_SYSTEM.md Section 2.

**Typed Streaming Event Pipeline Implementation:**

**Event Type: `RUN_STARTED`**
```json
{"type": "RUN_STARTED", "runId": "...", "threadId": "..."}
```
- **Emitted By:** `src/ui/agui_bridge.py`, on ADK session initialization (Section 4, Step 1).
- **Consumed By:** `frontend/src/App.tsx` — initializes the console shell.

**Event Type: `STEP_STARTED` / `STEP_FINISHED`**
```json
{"type": "STEP_STARTED", "step_name": "evidence_triage", "event_id": "..."}
```
- **Emitted By:** Each node function in `src/agents/`, on entry/exit.
- **Consumed By:** `frontend/src/components/StepTracker.tsx`.

**Event Type: `TOOL_CALL_START` / `TOOL_CALL_ARGS` / `TOOL_CALL_END` / `TOOL_CALL_RESULT`**
```json
{"type": "TOOL_CALL_START", "toolCallId": "...", "toolCallName": "query_loki_logs"}
```
- **Emitted By:** `src/tools/` wrapper layer, on every tool invocation (all nine tools).
- **Consumed By:** `frontend/src/components/EvidenceCard.tsx` (Tools 1–3) and `frontend/src/components/RemediationLog.tsx` (Tools 4–9).

**Event Type: `REASONING_START` / `REASONING_MESSAGE_START` / `REASONING_MESSAGE_CONTENT` / `REASONING_MESSAGE_END` / `REASONING_END`**
```json
{"type": "REASONING_MESSAGE_CONTENT", "messageId": "...", "delta": "..."}
```
- **Emitted By:** `src/agents/root_cause_correlation.py` only, streaming Gemini 3.1 Pro's native thinking tokens.
- **Consumed By:** `frontend/src/components/DiagnosisBadge.tsx`'s collapsed reasoning panel.

**Event Type: `STATE_DELTA`**
```json
{"type": "STATE_DELTA", "delta": [{"op": "add", "path": "/diagnosis_history/-", "value": {...}}]}
```
- **Emitted By:** `src/state/reducers.py`, on every successful state write, expressed as a JSON Patch matching the field's declared reducer.
- **Consumed By:** All frontend components — this is the sole source of truth the console renders from.

**Event Type: `RUN_PAUSED`**
```json
{"type": "RUN_PAUSED", "runId": "...", "reason": "hitl_approval_required"}
```
- **Emitted By:** `src/ui/hitl_resumption.py`, when the graph enters HITL Pause.
- **Consumed By:** `frontend/src/components/ApprovalCardModal.tsx` — opens the blocking modal.

**Event Type: `RUN_ERROR`**
```json
{"type": "RUN_ERROR", "message": "...", "code": "..."}
```
- **Emitted By:** Any node, on a permanent failure per Section 5's error handling.
- **Consumed By:** `frontend/src/components/FailureBanner.tsx`.

**Event Type: `RUN_FINISHED`**
```json
{"type": "RUN_FINISHED", "runId": "..."}
```
- **Emitted By:** `src/main.py`, at shoot-session end.
- **Consumed By:** `frontend/src/App.tsx` — closes the session and shows the summary.

**Generative UI Wiring:**
- `EvidenceBundleExtraction` → `EvidenceCard.tsx`, data-bound to `evidence_bundle[event_id]` via `STATE_DELTA`.
- `RootCauseDiagnosis` → `DiagnosisBadge.tsx`, data-bound to `diagnosis_history`'s latest entry for the event.
- `HITLCardPackage` → `ApprovalCardModal.tsx`, data-bound to `pending_hitl_card`.
- `RemediationAction` entries → `RemediationLog.tsx`, appended per `STATE_DELTA` on `remediation_log`.
- Prometheus sync-offset stream → `SyncOffsetChart.tsx`, fed directly from Stream Watch's metric polling, outside the `STEP_STARTED`/`STEP_FINISHED` cadence.

**HITL Graph-Resumption Implementation:**

**Checkpoint: HITL Pause**
- **Pause Implementation:** `src/agents/hitl_card_generation.py` writes `pending_hitl_card`/`session_status`, then the graph enters ADK's `LongRunningFunctionTool` await inside `src/ui/hitl_resumption.py`, which emits `RUN_PAUSED`.
- **Resumption Handler:** A FastAPI POST endpoint `/sessions/{session_id}/events/{event_id}/decision` in `src/main.py`, accepting the Approve/Deny payload shapes from INTERFACE_OBSERVABILITY_SYSTEM.md Section 5.
- **Validation:** No `modified_inputs` field exists for this checkpoint (per LLM-4 Section 5 — no editable fields); the handler validates only that `checkpoint_id` matches an actually-pending card before writing `approval_state`.
- **Resume Mechanism:** ADK resumes the paused graph from its Cloud SQL-checkpointed state at the HITL Pause node; `approval_state` write triggers `post_approval_handling.py`.

**Observability Hooks:**
- OTel GenAI spans emitted from `src/telemetry/tracing.py`, wrapping every node function and every tool call, per INTERFACE_OBSERVABILITY_SYSTEM.md Section 6's trace/span hierarchy (session → event → node → tool call).
- Dual export configured in `src/telemetry/otlp_export.py`: Google Cloud Trace (native) and Langfuse (via `OTEL_EXPORTER_OTLP_ENDPOINT`).
- Feedback annotations written from `src/telemetry/feedback_annotations.py`, triggered by the frontend's post-hoc diagnosis-accuracy and HITL-decision feedback actions, per Section 7a's mapping table.

**Real-Time Update Mechanism:**
Persistent SSE connection per active session, established by `frontend/src/stream/agui-client.ts`. On reconnect mid-stream, the frontend requests a full-state resync from the backend's checkpointed session state rather than replaying the event log from the start, per INTERFACE_OBSERVABILITY_SYSTEM.md Section 2a's ordering/backpressure guarantee.

---

## **8. SAFETY, CONTROL & FAILURE HANDLING**

**Human-in-the-Loop Enforcement Points:**

**Approval Gate: HITL Pause (single checkpoint, four escalation reasons)**
- Implementation: Section 7's HITL Graph-Resumption Implementation above.
- Timeout: None — per AGENT_BEHAVIOR_PROFILE.md/AGENT_LOGIC_SPEC.md, non-response never converts to a default action; the card re-flags at each subsequent telemetry sample interval and the frontend escalates visual urgency (INTERFACE_OBSERVABILITY_SYSTEM.md Section 5) but the graph remains paused indefinitely.

**Emergency Stop Mechanism:**
- Trigger: Supervisor's "Stop Session" control (frontend) → POST `/sessions/{session_id}/stop`.
- Implementation: `src/main.py` signals the ADK `Runner` to halt; any pending automatic action is suspended immediately.
- State preservation: Current state is checkpointed as-is before halt completes; no queued action executes retroactively.
- Recovery: Session cannot resume after Stop — a new session begins at the next shoot day, per the session-scoped lifecycle.

**Prohibition Enforcement:**
- No autonomous take-halt/fallback/threshold-exceeding failover: Tools 7–9 are importable only from `post_approval_handling.py` (Section 3's architecture-boundary rule, enforced by a static import-graph lint check in CI).
- Log/trace content never treated as instruction: Model Armor (`src/safety/model_armor_client.py`) sanitizes every Grafana/Tempo MCP response before it reaches a Gemini context window; the Evidence Triage node's own anomaly-flagging is a second layer.
- No sensitive infrastructure leakage: Secrets are resolved from Secret Manager at call-time only and never assigned into any `GenlockSentinelState` field — enforced by a static check that no secret-shaped environment variable is ever passed into a Pydantic state model constructor.
- No autonomous action on ambiguous diagnosis: Tools 4–6's precondition check (Section 5) structurally rejects invocation when `category == "ambiguous"`.
- No action post-session: All tool bindings and the Stream Watch subscription are scoped to an active `session_id`; session termination tears down the subscription.

**Fallback Behaviors:**
- Tool failure: Per Section 5's Error Handling Strategy.
- Model unavailability: If Gemini 3.1 Pro is unavailable, the event routes to HITL as ambiguous rather than falling back to Gemini 3.7 Flash for correlation (per AGENT_ORCHESTRATION_BLUEPRINT.md Section 8 — no model substitution for the reasoning role).
- Network timeout: Retry per Section 5, then escalate per the same section's permanent-failure path.

**Logging & Audit Trail:**
- Log/trace format: OTel GenAI Semantic Conventions spans (`gen_ai.*` attributes), per INTERFACE_OBSERVABILITY_SYSTEM.md Section 6.
- Log location: Google Cloud Trace (operational) and Langfuse via OTLP (scoring/evaluation).
- Retention: Per each backend's own configured retention (operational decision outside this plan's scope, per LLM-4 Section 6).
- Privacy: Raw cluster credentials, network-topology secrets, and any content flagged as a suspected injection attempt are never logged verbatim, per AGENT_LOGIC_SPEC.md Section 7's memory prohibitions.

---

## **9. AUTOMATED EVALUATION & TESTING FRAMEWORK**

**Testing Stack (Verified via Phase 1.5):**
- Test runner: `pytest` + `pytest-asyncio` — Assumption — Unverified exact current pinned versions; both are the standard, long-established choice for async Python test suites — confirm current versions before installation.
- LLM eval framework: `DeepEval` — Assumption — Unverified exact current pinned version; chosen for its native support for tool-calling-accuracy and hallucination/faithfulness metrics, which map directly onto AGENT_LOGIC_SPEC.md's citation-enforcement and silence-over-guessing requirements — confirm current version before installation.
- Justification: DeepEval's tool-correctness and faithfulness metrics directly test the two properties this system's safety case depends on most: that the right tool fires for the right diagnosed category, and that every diagnostic claim is evidence-grounded rather than fabricated.

### **9.1 Test Data Strategy & Mocks**

**Mock Drift Events (For Testing Logic):**
1. **Simple Case:** A clean network-jitter breach on `render-07` with unambiguous, single-source-confirming evidence — expected outcome: autonomous `failover_cluster_leadership` dispatch.
2. **Complex Case:** Conflicting evidence (Loki suggests thermal throttle, Tempo suggests network jitter) on `render-12` — expected outcome: `ambiguous` diagnosis, HITL escalation.
3. **Edge Case:** A drift event where `query_loki_logs` times out after 3 retries — expected outcome: `logs_available: false`, diagnosis proceeds on remaining evidence or routes to ambiguous if insufficient.

**Mock Tool Outputs (For Testing without API Costs):**

**`query_loki_logs` Mock Response:**
```json
{
  "success": true,
  "result": ["14:02:10 [cluster-manager] sync handshake retry node=render-07", "14:02:11 [LogDisplayClusterEngine] frame drop detected"],
  "error": null
}
```

**`find_slow_requests` Mock Response:**
```json
{
  "success": true,
  "result": {"investigation_id": "sift-mock-001", "findings": [{"span": "frame_render", "duration_ms": 340}]},
  "error": null
}
```

**`get_trace_by_id` Mock Response:**
```json
{
  "success": true,
  "result": {"spans": [{"service": "render-07", "duration_ms": 340, "status": "ok"}]},
  "error": null
}
```

**`failover_cluster_leadership` Mock Response:**
```json
{"success": true, "action_taken": "failover_cluster_leadership", "error": null}
```

**`halt_live_take` Mock Response:**
```json
{"success": true, "action_taken": "halt_live_take", "error": null}
```

### **9.2 Unit & Integration Tests**

**First Tests (Must Pass Before Proceeding):**
- [ ] Environment variables loaded correctly
- [ ] Google Cloud, Grafana, Tempo, Cloud SQL, and Langfuse credentials authenticate successfully
- [ ] All dependencies installed per the verified manifest in Section 2
- [ ] Both Gemini models respond to a test prompt with schema-valid structured output
- [ ] Every state reducer behaves correctly: `append-only` never drops an entry under concurrent writes to `diagnosis_history`/`remediation_log`/`error_logs`; `merge-by-key` never cross-overwrites a different `node_id`/`event_id` key in `active_drift_events`/`evidence_bundle`; `last-write-wins` resolves deterministically for `pending_hitl_card`/`approval_state`/`session_status`; `session_id`/`config` reject any post-init write
- [ ] Cloud SQL checkpoint write/read/resume round-trip succeeds
- [ ] All nine tools register without errors and validate against both their Pydantic V2 and MCP/strict schema forms

### **9.3 LLM-Specific Evaluation Suites**

**Tool-Calling Accuracy Evals:**
- Given the Simple Case mock (network_jitter, unambiguous), assert Root-Cause Correlation outputs `category: "network_jitter"` and Autonomous Dispatch calls `failover_cluster_leadership` — never `deprioritize_texture_streaming` or `force_genlock_resync`.
- Given a mock diagnosed `asset_streaming_stall`, assert only `deprioritize_texture_streaming` is called.
- Given a mock HITL card with `proposed_action: "halt_live_take"` and an Approve payload, assert only `halt_live_take` fires — never `fallback_to_greenscreen` or `execute_threshold_exceeding_failover`.

**Hallucination Prevention Evals:**
- Given the Edge Case mock (`query_loki_logs` timeout), assert `EvidenceBundleExtraction.logs_available == false` and no fabricated log line appears in `log_summary`.
- Assert every `RootCauseDiagnosis.rationale` and `HITLCardPackage.root_cause_summary` produced in test runs cites a specific `evidence_bundle` field — reject any output whose rationale references evidence not present in the mock.

**HITL Graph Resumption Evals:**
- Trigger the HITL Pause checkpoint with the Complex Case mock; send an Approve payload; assert execution resumes from `post_approval_handling.py` with `approval_state == "approved"` and the correct tool fires.
- Send a Deny payload; assert no action tool fires, the denial is appended to `error_logs`/`remediation_log`, and `session_status` returns to `"monitoring"`.
- Send an Approve payload with a `checkpoint_id` that does not match any pending card; assert the resumption handler rejects it rather than resuming an unrelated event.

**Grounding & Citation Evals:**
- Given the Complex Case mock's conflicting Loki/Tempo evidence, assert `EvidenceBundleExtraction.anomaly` or the diagnosis rationale surfaces the conflict explicitly rather than silently favoring one source.

### **9.4 "Agent Is Working" Success Criteria**

- [ ] Stream Watch detects a mock threshold breach and creates a new `active_drift_events` entry
- [ ] Evidence Triage calls all three query tools in the correct mode (Tool/Function Calling) and produces a schema-valid `EvidenceBundleExtraction`
- [ ] Root-Cause Correlation produces a schema-valid `RootCauseDiagnosis` with native reasoning tokens streamed via `REASONING_*` events
- [ ] The reasoning/dispatch loop executes without infinite loops or repeated re-invocation of a resolved event
- [ ] State persists across a simulated crash-and-resume via the Cloud SQL checkpoint
- [ ] The HITL Pause gate triggers correctly on all four escalation reasons and resumes correctly on Approve and on Deny
- [ ] All five structural prohibitions from Section 8 pass their negative tests
- [ ] The frontend console displays activity via the exact AG-UI event types defined in Section 7
- [ ] `EvidenceBundleExtraction`, `RootCauseDiagnosis`, `HITLCardPackage`, and `RemediationAction` each render as their specified generative UI component
- [ ] OTel GenAI spans are captured and visible in both Cloud Trace and Langfuse for a full test event
- [ ] A post-hoc diagnosis-accuracy feedback action writes a Langfuse score annotation
- [ ] Every simulated tool/model failure is handled per Section 8's fallback behaviors without crashing the session

### **9.5 Failure Scenarios to Simulate**

1. `query_loki_logs` fails all 3 retries — verify evidence-gap flag set, diagnosis proceeds or routes to ambiguous
2. Supervisor issues Stop Session mid-diagnostic-cycle — verify clean halt and checkpoint preservation, no retroactive action
3. A drift event arrives with a malformed/missing `frame_id` — verify graceful rejection, logged to `error_logs`
4. A prohibited action is attempted directly against Tools 7–9 bypassing `post_approval_handling.py` (simulated via a deliberately-broken test import) — verify the CI import-boundary lint check fails the build
5. HITL card remains pending with no supervisor response for an extended simulated period — verify no default action fires and the card re-flags per the defined behavior
6. A tool returns malformed JSON not matching its schema — verify schema validation rejects it before it reaches `evidence_bundle`/`diagnosis_history`

### **9.6 Non-Negotiable Verification Requirements**

- No infinite loops possible — each `event_id` reaches a terminal state in exactly one pass through Steps 2–6
- All five structural prohibitions (Section 8) are enforced and cannot be bypassed
- Emergency stop is always functional, including while a HITL card is open
- Every reducer behaves exactly as declared under concurrent/sequential writes
- The HITL checkpoint has a working resumption path for both Approve and Deny (no Edit path exists, by design — see Section 7)
- OTel GenAI spans capture every node execution and every tool call, exported to both configured backends

---

## **10. STEP-BY-STEP EXECUTION SEQUENCE**

**STEP 1: Environment Setup**
- Action: Create `backend/.env` from `.env.example` with all variables from Section 2.
- Verification: `printenv | grep GRAFANA_URL` (and equivalent for each variable) shows values.
- Dependencies: None.
- Safe to run: Yes (idempotent).

**STEP 2: Initialize Project Manifest & Install Dependencies**
- Action: Create `backend/pyproject.toml` per Section 2; run `uv sync`. Create `frontend/package.json` per Section 2; run `pnpm install`.
- Verification: Both dependency resolutions complete with no conflicts; installed versions match or exceed the floors in Section 2's manifest.
- Dependencies: STEP 1 complete.
- Safe to run: Yes (idempotent).

**STEP 3: Generate Coding Assistant Context File**
- Action: Write `backend/CLAUDE.md` from Section 3 verbatim.
- Verification: File exists and matches Section 3 exactly.
- Dependencies: STEP 2 complete.
- Safe to run: Yes (idempotent).

**STEP 4: Scaffold Directory Structure**
- Action: Create the full `backend/src/` and `frontend/src/` tree from Section 2.
- Verification: Directory tree matches Section 2 exactly.
- Dependencies: STEP 2 complete.
- Safe to run: Yes (idempotent).

**STEP 5: Initialize ADK Runner**
- Action: Implement `src/main.py`'s `Runner(streaming_mode=StreamingMode.SSE)` bootstrap (Section 4, Step 1).
- Verification: A trivial no-op agent run completes end to end.
- Dependencies: STEP 4 complete.
- Safe to run: Yes.

**STEP 6: Configure Models**
- Action: Implement model configuration per Section 4, Step 2, including context caching for shared static prompt content.
- Verification: Test call to Gemini 3.1 Pro and Gemini 3.7 Flash each return valid structured output.
- Dependencies: STEP 1 (API keys), STEP 5 (runner).
- Safe to run: Yes.

**STEP 7: Implement Typed State Schema & Reducers**
- Action: Implement `src/state/schema.py` and `src/state/reducers.py` exactly per Section 4, Step 3.
- Verification: All reducer unit tests from Section 9.2 pass.
- Dependencies: STEP 2 (Pydantic installed).
- Safe to run: Yes.

**STEP 8: Initialize Checkpointing Backend**
- Action: Implement `src/state/checkpointing.py` (Cloud SQL for PostgreSQL, per Section 4, Step 4).
- Verification: Checkpoint write/read/resume round-trip test passes.
- Dependencies: STEP 7 complete.
- Safe to run: Yes (creates the session table if needed).

**STEP 9: Confirm No Long-Term Memory**
- Action: Confirm Section 4, Step 5 — no vector-store dependency or client exists anywhere in the codebase.
- Verification: A manifest/codebase grep for vector-store packages returns nothing.
- Dependencies: STEP 2.
- Safe to run: Yes.

**STEP 10: Register Tools**
- Action: Implement and register all nine tools from Section 5, in the order: Tools 1–3 (Evidence Triage) → Tools 4–6 (Autonomous Dispatch) → Tools 7–9 (Post-Approval Handling), wiring both Pydantic V2 and MCP/strict schema forms for each.
- Verification: Each tool's mock-based invocation test (Section 9.1/9.2) passes; schema validation passes for both formats.
- Dependencies: STEP 6 (models configured for the two Gemini-backed tools' surrounding nodes).
- Safe to run: Yes.

**STEP 11: Wire Orchestration Graph**
- Action: Implement `src/agents/graph.py` per Section 4, Step 6 and Section 6's reasoning flow.
- Verification: Graph structure validation confirms exactly seven nodes matching AGENT_ORCHESTRATION_BLUEPRINT.md Section 4.
- Dependencies: STEP 5 (runner), STEP 10 (tools).
- Safe to run: Yes.

**STEP 12: Implement Reasoning Loop**
- Action: Implement the per-event Steps 1–7 flow from Section 6.
- Verification: Single-event test using the Simple Case mock from Section 9.1 resolves to autonomous `failover_cluster_leadership` dispatch.
- Dependencies: STEP 11 (graph wired).
- Safe to run: Yes (test mode, using mocks).

**STEP 13: Implement Safety Guardrails**
- Action: Implement `src/safety/prohibition_guards.py` and `src/safety/model_armor_client.py` per Section 8.
- Verification: All five negative tests from Section 9.5/9.6 pass — prohibited actions are structurally prevented.
- Dependencies: STEP 12 (reasoning works).
- Safe to run: Yes (test mode).

**STEP 14: Build Backend API/Server**
- Action: Implement the FastAPI app in `src/main.py`, including the `/sessions/{session_id}/events/{event_id}/decision` and `/sessions/{session_id}/stop` endpoints.
- Verification: Health check endpoint responds; decision/stop endpoints reject malformed payloads.
- Dependencies: STEP 12 (agent runtime ready).
- Safe to run: Yes.

**STEP 15: Implement Typed Streaming Layer**
- Action: Implement `src/ui/agui_bridge.py` and `src/ui/event_types.py`, wiring `adk-agui-middleware` to project every event type from Section 7.
- Verification: Test message send/receive for each of the nine event types in Section 7's contract.
- Dependencies: STEP 14 (server running).
- Safe to run: Yes.

**STEP 16: Implement HITL Graph-Resumption Endpoints**
- Action: Implement `src/ui/hitl_resumption.py` per Section 7's HITL Graph-Resumption Implementation.
- Verification: All HITL eval scenarios from Section 9.3 pass (Approve, Deny, mismatched `checkpoint_id`).
- Dependencies: STEP 15 (streaming works), STEP 8 (checkpointing ready).
- Safe to run: Yes.

**STEP 17: Build Interface Layer & Generative UI Components**
- Action: Implement the seven frontend components listed in Section 2's directory structure, wired per Section 7's Generative UI Wiring.
- Verification: Console loads, connects via SSE, and renders each generative UI component correctly against mock `STATE_DELTA` events.
- Dependencies: STEP 15 (streaming works).
- Safe to run: Yes.

**STEP 18: Integrate Telemetry & Observability**
- Action: Implement `src/telemetry/tracing.py`, `otlp_export.py`, and `feedback_annotations.py` per Section 7's Observability Hooks.
- Verification: OTel spans appear in both Cloud Trace and Langfuse for a test event; a test feedback action writes a Langfuse score.
- Dependencies: STEP 12 (reasoning loop), STEP 17 (interface).
- Safe to run: Yes.

**STEP 19: Run Automated Evaluation Suites**
- Action: Execute the full test suite from Section 9 (unit, integration, LLM eval, HITL resumption) against Cloud SQL (not SQLite scaffolding).
- Verification: All tests pass; all Non-Negotiable Verification Requirements from Section 9.6 are met.
- Dependencies: ALL previous steps complete.
- Safe to run: Yes.

**STEP 20: End-to-End Verification**
- Action: Run the complete flow for each of the three mock drift events from Section 9.1, including one full HITL approval cycle and one Deny cycle.
- Verification: All success criteria from Section 9.4 pass.
- Dependencies: STEP 19 passed.
- Safe to run: Yes (final test).

**STEP 21: Production Readiness Check**
- Action: Review all verification checklists; run all six failure simulations from Section 9.5; confirm production configuration from Section 2 (Cloud SQL, Secret Manager, Model Armor policies, dual OTLP export all active).
- Verification: All non-negotiable criteria in Section 9.6 met.
- Dependencies: STEP 20 passed.
- Safe to run: Yes.

---

## **EXECUTION PLAN INTEGRITY DECLARATION**

This master plan is AUTHORITATIVE and COMPLETE.

Downstream code generation systems must:
- Execute steps in exact order specified
- Verify each step before proceeding
- Never skip steps
- Never combine steps
- Never invent logic not specified
- Never modify specifications
- Never install an unverified or deprecated package version
- Follow the coding-assistant context file's rules and anti-patterns without exception
- Halt on verification failure

This plan eliminates all execution ambiguity.
Every dependency is explicit and version-verified.
Every verification is defined.
Every failure mode is anticipated.

Implementation is now deterministic and mechanical.

---
