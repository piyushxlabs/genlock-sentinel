---
trigger: always_on
---

Per `INTERFACE_OBSERVABILITY_SYSTEM.md` Section 10, the operations console must NOT include:

1. A conversational chat box, free-text message input, or multi-turn prompt interface (the console is a live operations dashboard with discrete Approve/Deny/Stop controls, not a chatbot).

2. Raw LogQL/TraceQL query strings or raw tool-call argument JSON in the default user view (debug panel only).

3. Raw internal Model Armor detection heuristics or internal filter mechanics.

4. ADK Workflow session/checkpoint internals (Cloud SQL row schemas, checkpoint timing).

5. Raw cluster credentials, network topology secrets, or Grafana service account tokens.

6. A configurable autonomy level toggle (Manual vs. Fully Autonomous) — the system is permanently locked to Semi-Autonomous.

7. Manual actuator takeover controls (firing remediation tools outside the agent's decision flow).

If any instruction implies adding these, flag it as an interface specification violation before building.
