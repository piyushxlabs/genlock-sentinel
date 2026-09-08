---
trigger: always_on
---

Bare `try-except` blocks with `pass` are strictly forbidden.

All errors must be explicitly typed using the custom `AgentError` hierarchy and logged to `error_logs` with event context.

All transient dependencies (Grafana MCP Server, Tempo MCP endpoint, Cloud SQL/PostgreSQL connections, Gemini API inference) must implement exponential backoff:

* 1s
* 2s
* 4s

Maximum 3 retry attempts.

If a query tool fails after retries, strictly enforce the silence-over-guessing policy:

* Set `logs_available: false` (or trace gap flag).
* Record the failure in `anomaly`.
* Proceed on remaining evidence or escalate to `category: "ambiguous"`.

NEVER fabricate plausible log lines or spans.

Cognitive nodes must use Google ADK's native Gemini structured outputs:

* `gemini-3.1-pro` for Root-Cause Correlation at `temperature=0.0`.
* `gemini-3.7-flash` for Evidence Triage and HITL Card Generation.

These models must be bound to strict Pydantic V2 schemas.

On permanent failure, circuit-breaker trip, or safety violation, route to the spec-defined terminal path:

1. Emit a `RUN_ERROR` event.
2. Surface a persistent System Message failure banner.
3. Log full diagnostic context to `error_logs`.

Never emit unvalidated or ungrounded actions to the on-set cluster.
