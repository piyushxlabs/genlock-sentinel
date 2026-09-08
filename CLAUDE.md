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
