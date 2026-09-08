---
trigger: always_on
---

Before executing any graph node or tool call, enforce strict pre-condition invariants in Python code:

1. `session_id` and `config` are strictly immutable after initialization (`immutable-after-init`) — any attempted mutation must raise `StateValidationError`.

2. Evidence Triage (Node 2) tools (`query_loki_logs`, `find_slow_requests`, `get_trace_by_id`) must only execute if an active `DriftEvent` exists in `active_drift_events` for the target `node_id`.

3. `failover_cluster_leadership` must only execute if the latest `diagnosis_history` entry has `category == "network_jitter"` and `confidence >= config.confidence_floor`.

4. `deprioritize_texture_streaming` must only execute if the latest diagnosis has `category == "asset_streaming_stall"` and `confidence >= config.confidence_floor`.

5. `force_genlock_resync` must only execute if the latest diagnosis has `category == "thermal_throttle"` and `confidence >= config.confidence_floor`.

6. HITL-gated tools (`halt_live_take`, `fallback_to_greenscreen`, `execute_threshold_exceeding_failover`) in Node 7 (Post-Approval Handling) must only execute if `approval_state == "approved"` and `hitl_card_id` matches the `pending_hitl_card.event_id`.

7. All free-text query parameters (such as `logql`) must pass through input sanitization in `src/safety/prohibition_guards.py` before invocation to strip control characters and prevent cross-event parameter leakage.
