---
trigger: always_on
---

The nodes in `backend/src/agents/` must strictly enforce the Node-Tool Access Matrix defined in `AGENT_LOGIC_SPEC.md` Section 6:

* **Stream Watch (Node 1, Non-LLM):** Polling/subscription only — bound to Prometheus sync-offset ingestion; writes `active_drift_events`. NO external write tools.

* **Evidence Triage (Node 2, Gemini 3.7 Flash):** Read-only observability — bound ONLY to `query_loki_logs`, `find_slow_requests`, and `get_trace_by_id` via Grafana MCP. NO remediation tools bound.

* **Root-Cause Correlation (Node 3, Gemini 3.1 Pro):** Structured Output only (`RootCauseDiagnosis`) — NO external tools or MCP servers bound.

* **Autonomous Remediation Dispatch (Node 4, Deterministic):** Bound ONLY to the 3 pre-approved reversible internal tools:

  * `failover_cluster_leadership`
  * `deprioritize_texture_streaming`
  * `force_genlock_resync`

  NO LLM calls, NO HITL-gated tools bound.

* **HITL Card Generation (Node 5, Gemini 3.7 Flash):** Structured Output only (`HITLCardPackage`) — NO external tools bound.

* **HITL Pause (Node 6, ADK LongRunningFunctionTool):** Durable graph interrupt/resume checkpoint — NO tools bound.

* **Post-Approval Handling (Node 7, Deterministic):** Bound ONLY to the 3 HITL-gated internal tools:

  * `halt_live_take`
  * `fallback_to_greenscreen`
  * `execute_threshold_exceeding_failover`

  Callable ONLY after supervisor approval resume. NO LLM calls.

No cognitive node may ever hold a tool binding to a remediation actuator.

Direct mutation of infrastructure tools outside their authorized deterministic dispatch nodes is an architectural violation and must fail lint/build verification.
