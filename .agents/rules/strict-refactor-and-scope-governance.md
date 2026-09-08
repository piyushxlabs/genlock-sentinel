---
trigger: always_on
---

Never refactor, rename, restructure, or modify working code or schemas without explicit permission.

If you believe a refactor is needed, state:

* What you want to change (specific state fields, reducers, ADK graph nodes, or tool schemas)

* Why it is needed (referencing the 5 locked specification documents)

* What could break (e.g., Cloud SQL/SQLite state serialization, ADK Workflow graph edge routing, AG-UI SSE streaming contract, Grafana MCP client bindings)

Then wait for approval.

Unauthorized refactoring of the 10 `GenlockSentinelState` fields, declared reducers, or 7 ADK graph nodes is a critical failure.
