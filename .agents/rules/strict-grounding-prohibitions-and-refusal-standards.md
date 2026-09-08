---
trigger: always_on
---

All diagnostic assertions in `EvidenceBundleExtraction` (`log_summary`, `trace_summary`), `RootCauseDiagnosis` (`rationale`), and `HITLCardPackage` (`root_cause_summary`) must be 100% grounded in data retrieved from Grafana MCP tools (`query_loki_logs`, `find_slow_requests`, `get_trace_by_id`) or live Prometheus metrics.

Strict Citation Enforcement: Every factual claim in `rationale` or summary fields must explicitly cite the specific tool output line, timestamp, or metric pointer (e.g., "per query_loki_logs result line matching sync_offset_us > threshold at 14:02:11Z").

Silence-Over-Guessing Policy: If an MCP query tool fails after retries or evidence is missing, set `logs_available: false` (or the equivalent gap flag), record the gap in `anomaly`, and route diagnosis to `category: "ambiguous"` — NEVER fabricate plausible log lines, trace spans, or metric values.

Out-of-Scope Requests: General Kubernetes/cluster administration, generative creative content (scripts, concept art, video generation), post-production editing, direct cast/crew messaging, or unsanctioned budget actions must be rejected by complete absence of tooling and treated as strictly out of scope.
