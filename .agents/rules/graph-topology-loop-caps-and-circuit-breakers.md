---
trigger: always_on
---

The agent workflow must strictly implement the 7-node ADK Workflow Runtime graph topology defined in `AGENT_ORCHESTRATION_BLUEPRINT.md` Section 4:

`Node 1: Stream Watch (non-LLM) → Node 2: Evidence Triage (Gemini 3.7 Flash) → Node 3: Root-Cause Correlation (Gemini 3.1 Pro) → Decision Edge → [Node 4: Autonomous Remediation Dispatch (deterministic) OR Node 5: HITL Card Generation (Gemini 3.7 Flash) → Node 6: HITL Pause (ADK LongRunningFunctionTool) → Node 7: Post-Approval Handling (deterministic)]`

Do NOT create open-ended ReAct-style agent loops, autonomous multi-turn conversations, or recursive sub-goal generation.

Every node has exactly one isolated, non-overlapping responsibility.

Execution boundaries and cycle caps are strictly enforced:

1. Exactly ONE diagnostic and remediation pass per `event_id` to a terminal state (resolved, denied, or failed) — an event in flight can never re-enter the diagnostic loop.

2. Transient MCP query tool failures are hard-capped at `MAX_TOOL_RETRIES = 3` with exponential backoff.

3. Structured output schema validation failures are hard-capped at 1 retry per node with appended error context.

4. Circuit Breaker: If the same `node_id` re-breaches threshold more than a configured count within a rolling window after an autonomous remediation was marked successful, code must force the next occurrence directly onto the HITL path to prevent infinite autonomous failover cycles.
