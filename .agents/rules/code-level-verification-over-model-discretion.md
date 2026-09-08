---
trigger: always_on
---

The Human-in-the-Loop (HITL) escalation routing must be independently derived and enforced in Python code at the conditional branching edge following the Root-Cause Correlation node:

`category == "ambiguous" OR confidence < config.confidence_floor OR proposed_action in ["halt_live_take", "fallback_to_greenscreen", "execute_threshold_exceeding_failover"]`

Never rely on the LLM to decide whether it should stop for human approval; approval gates are structural graph checkpoints, not model recommendations.

Similarly, code-level validation must enforce grounding and trust boundaries:

1. The Root-Cause Correlation node must validate in Python that its `rationale` cites at least one verified field from `evidence_bundle` (`log_summary`, `trace_summary`, or metric pointer) before the record is accepted into `diagnosis_history`.

2. Reversible remediation tools (`failover_cluster_leadership`, `deprioritize_texture_streaming`, `force_genlock_resync`) must verify in code that the active drift event's latest diagnosis matches their specific category and meets the confidence floor before firing.

3. HITL-gated tools (`halt_live_take`, `fallback_to_greenscreen`, `execute_threshold_exceeding_failover`) must programmatically verify that `approval_state == "approved"` and that `hitl_card_id` matches the currently pending card before dispatch.
