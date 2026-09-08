# AGENT ORCHESTRATION BLUEPRINT

**Generated:** September 7, 2026
**Source:** AGENT_BEHAVIOR_PROFILE.md
**Status:** AUTHORITATIVE — Defines complete agent system architecture
**Purpose:** Cognitive architecture and orchestration specification

---

## **1. SYSTEM OVERVIEW**

**High-Level Description:**
Genlock Sentinel is architected as a single graph-based workflow agent running on Google's Agent Development Kit (ADK) 2.x Workflow Runtime, deployed to the Gemini Enterprise Agent Platform's managed Agent Engine. A continuous, non-LLM telemetry watcher triggers a bounded diagnostic-and-remediation graph cycle each time a node's genlock sync-offset breaches threshold, with a deterministic reasoning/execution model split and hard-gated human-in-the-loop checkpoints.

**Architectural Classification:** Single-Agent System

**Justification:**
The behavioral profile defines exactly one primary goal (detect and remediate genlock drift) with one cognitive role (correlate telemetry evidence into a root-cause category, then either act or escalate). There is no role specialization, no parallel independent objectives, and no benefit to inter-agent negotiation — a single agent expressed as a graph of deterministic and LLM-backed nodes fulfills the contract without the coordination overhead multi-agent design would add.

**Complexity Level:**
Medium — bounded conditional branching (three known root-cause categories, four HITL triggers, one ambiguity path), a real-time low-latency constraint, one external MCP integration, and durable pause/resume for human approval. Not Complex, because there is no multi-agent coordination, no long-term semantic memory, and no unbounded reasoning space.

---

## **2. AGENT TOPOLOGY**

**Number of Agents:** 1

### **Agent: Genlock Sentinel**
- **Responsibility:** Continuously watch cluster genlock telemetry, diagnose the root cause of any sync-offset breach against three known categories, and either dispatch a pre-approved autonomous remediation or escalate to a human supervisor via a structured HITL card.
- **Cognitive Scope:** Correlative diagnosis across metrics, logs, and traces limited to three known root-cause categories; no open-ended hypothesis generation; deterministic mapping from diagnosis to action.
- **Execution Authority:** May directly execute the three pre-approved, reversible remediation actions (standby failover, texture deprioritization, forced re-sync handshake). May not execute take-halting, capture-mode fallback, or threshold-exceeding actions without explicit human sign-off.

**Control Hierarchy:**
- **Pattern:** Graph-based (single agent, internally structured as an ADK Workflow Runtime graph of deterministic and LLM-backed nodes)
- **Control Flow:** A non-LLM stream-watcher node triggers graph entry on threshold breach; two Gemini-backed nodes (evidence triage, root-cause correlation) feed a deterministic decision node, which routes to either an autonomous-action node or a HITL-interrupt node
- **Coordination Mechanism:** Shared typed state object (Section 3) passed and mutated node-to-node within the single graph execution; no inter-agent message passing exists because no second agent exists

---

## **3. TYPE-SAFE CENTRAL STATE SCHEMA & REDUCERS**

**Schema Definition Style:** Pydantic BaseModel-equivalent, persisted via ADK's session state service

**Traceability:** `active_drift_events` and `evidence_bundle` formalize LLM-1's Input Contract (Prometheus/DCGM metrics, Loki logs, Tempo traces via Grafana MCP Server). `remediation_log` and `pending_hitl_card` formalize LLM-1's Deliverable Contract (remediation action records and structured HITL cards). No field redefines the meaning of that contract — this schema only gives it explicit types and mutation rules.

**Global State Schema:**
```
GenlockSentinelState:
  session_id: str                                    # reducer: immutable after init
  session_status: SessionStatus (enum)               # reducer: last-write-wins
  active_drift_events: dict[node_id, DriftEvent]     # reducer: merge-by-key, keyed by node_id
  evidence_bundle: dict[event_id, EvidenceRefs]      # reducer: merge-by-key, keyed by event_id
  diagnosis_history: list[DiagnosisRecord]           # reducer: append-only
  remediation_log: list[RemediationAction]           # reducer: append-only
  pending_hitl_card: HITLCard | None                 # reducer: last-write-wins
  approval_state: ApprovalStatus | None               # reducer: last-write-wins
  error_logs: list[ErrorRecord]                      # reducer: append-only
  config: RuntimeConfig                              # reducer: immutable after init
```

**Field-by-Field Reducer Rationale:**
- **active_drift_events:** merge-by-key on `node_id` — the cluster can have more than one node in drift concurrently; a per-node keyed dict prevents one node's event from silently overwriting another's during concurrent stream processing.
- **evidence_bundle:** merge-by-key on `event_id` — evidence for one drift event must never be mixed into or overwritten by evidence gathered for a different event, even if both are in flight.
- **diagnosis_history / remediation_log / error_logs:** append-only — these are audit trails required by the behavioral profile's evidence-trail obligation (Section 5, capability 7); overwriting any entry would destroy the record needed for post-event review.
- **pending_hitl_card / approval_state:** last-write-wins — only one HITL decision is ever pending at a time per event; the most recent supervisor action is authoritative.
- **session_status / config:** last-write-wins and immutable-after-init respectively — session_status reflects the single current phase of the one active cycle; config (thresholds, financial cap) is fixed for the duration of a shoot session and must not drift mid-session.

**Mutation Boundaries:**
The stream-watcher node may only write `active_drift_events`. The evidence-triage and root-cause-correlation nodes may only write `evidence_bundle` and append to `diagnosis_history`. The deterministic decision/dispatch node may append to `remediation_log` or write `pending_hitl_card`. Only the HITL-resume handler may write `approval_state`. `config` is read-only to every node after graph initialization.

---

## **4. EXECUTION FLOW**

**Entry Point:**
Continuous Stream ingestion — a non-LLM subscriber node consumes the live Prometheus/DCGM genlock sync-offset metric for every cluster node for the duration of the shoot session (per LLM-1's Continuous Stream trigger).

**Flow Type:** Graph-based, with one cyclical outer loop (continuous monitoring) wrapping a bounded, non-cyclical inner diagnostic path per drift event.

**Detailed Execution Steps:**

1. **Stream Watch**
   - **Agent Responsible:** Non-LLM stream-watcher node
   - **Action:** Continuously evaluate incoming sync-offset samples per node against the vsync-variance threshold
   - **State Fields Read/Written:** Writes `active_drift_events`
   - **Decision Point:** Threshold breached? No → continue watching. Yes → spawn diagnostic cycle for that `node_id`.
   - **Next Step:** Evidence Triage (only on breach)

2. **Evidence Triage**
   - **Agent Responsible:** Gemini 3.7 Flash node
   - **Action:** Query Loki logs and Tempo traces for the breaching node/`frame_id` window via the Grafana MCP Server; condense into a structured evidence bundle
   - **State Fields Read/Written:** Reads `active_drift_events`; writes `evidence_bundle`
   - **Decision Point:** None (deterministic triage)
   - **Next Step:** Root-Cause Correlation

3. **Root-Cause Correlation**
   - **Agent Responsible:** Gemini 3.1 Pro node
   - **Action:** Correlate the evidence bundle against the three known root-cause categories (network jitter, thermal throttle, asset streaming stall) and produce a category plus confidence score
   - **State Fields Read/Written:** Reads `evidence_bundle`; appends to `diagnosis_history`
   - **Decision Point:** Diagnosis unambiguous and action within financial threshold? → Autonomous path. Diagnosis ambiguous, or maps to halt/fallback/threshold-exceeding action? → HITL path.
   - **Next Step:** Autonomous Remediation Dispatch OR HITL Card Generation

4. **Autonomous Remediation Dispatch**
   - **Agent Responsible:** Deterministic dispatch node (rule-based, category-to-action lookup — no free-form model call)
   - **Action:** Invoke the one pre-approved function bound to the diagnosed category (standby failover / texture deprioritization / forced re-sync)
   - **State Fields Read/Written:** Reads `diagnosis_history`; appends to `remediation_log`; writes `session_status`
   - **Decision Point:** None (deterministic mapping)
   - **Next Step:** Return to Stream Watch

5. **HITL Card Generation**
   - **Agent Responsible:** Gemini 3.7 Flash node
   - **Action:** Package the diagnosis, cost delta estimate, and visual impact score into a structured HITL card
   - **State Fields Read/Written:** Reads `diagnosis_history`, `evidence_bundle`; writes `pending_hitl_card`; writes `session_status = awaiting_approval`
   - **Decision Point:** None
   - **Next Step:** HITL Pause

6. **HITL Pause (Interrupt)**
   - **Agent Responsible:** ADK LongRunningFunctionTool pause/resume mechanism
   - **Action:** Graph execution suspends durably (checkpointed); supervisor is presented the HITL card out-of-band
   - **State Fields Read/Written:** Reads `pending_hitl_card`
   - **Decision Point:** Supervisor approves → resume with `approval_state = approved`. Supervisor denies → resume with `approval_state = denied`. No response → re-flag the card at each subsequent sample interval, remain paused.
   - **Next Step:** Post-Approval Handling

7. **Post-Approval Handling**
   - **Agent Responsible:** Deterministic dispatch node
   - **Action:** If approved, invoke the specific HITL-gated function (halt / fallback / threshold-exceeding failover) named in the card. If denied, take no action.
   - **State Fields Read/Written:** Reads `approval_state`; appends to `remediation_log` or `error_logs`; writes `session_status`
   - **Decision Point:** None
   - **Next Step:** Return to Stream Watch

**Decision Points:**
- **At Step 3:** If diagnosis ∈ {network jitter, thermal throttle, asset stall} AND confidence high AND action ≤ financial threshold → Step 4, else → Step 5
- **At Step 6:** If approved → dispatch action; if denied → log and discard; if unresponsive → re-flag, remain paused

**Termination Conditions:**
- **Success:** Sync-offset returns within threshold, or a HITL-approved action resolves it, with a complete evidence-linked record in `remediation_log`
- **Failure:** Any of the four failure conditions from the behavioral profile (defect captured before remediation, telemetry source unavailable, diagnosis remains ambiguous past the point HITL could still act, injection attempt detected in ingested content)
- **Timeout:** No autonomous timeout exists for HITL waits — per the behavioral profile, non-response never converts into a default action; the card is simply re-flagged
- **User Interrupt:** A supervisor stop/halt command immediately suspends all pending automatic actions and discards queued (not-yet-executed) actions, per LLM-1 Section 10

**Loop Prevention:**
Each drift event runs exactly one pass through Steps 2–7 to a terminal state (remediated, approved-and-acted, denied, or failed) before that event is closed; the outer Stream Watch loop is the only cyclical element, and it never re-enters the diagnostic subgraph for an event still in flight. A circuit breaker additionally escalates a node to mandatory HITL (rather than repeating autonomous action) if the same `node_id` re-breaches threshold more than a configured count within a short rolling window after an autonomous remediation was marked successful — preventing an infinite autonomous retry cycle on a node that isn't actually fixed.

---

## **5. ORCHESTRATION FRAMEWORK CHOICE**

**Selected Framework:** Google Agent Development Kit (ADK) 2.x — Workflow Runtime, deployed via the Gemini Enterprise Agent Platform's managed Agent Engine

**Verification Note:** Verified via live web search (September 2026). ADK 2.x (current release line, 2.5 as of July 2026) ships a graph-based Workflow Runtime with routing, fan-out/fan-in, loops, retry, typed state management, dynamic nodes, human-in-the-loop, and nested workflows; session/state persistence supports SQLite, PostgreSQL (asyncpg), and Firestore backends; `LongRunningFunctionTool` provides first-class pause/resume for HITL tool authorization; native MCP client support is confirmed as part of ADK's tool ecosystem. Vertex AI itself was confirmed rebranded and absorbed into the Gemini Enterprise Agent Platform as of Google Cloud Next 2026, with Agent Engine as its managed runtime layer.

**Justification:**
This is the only framework that simultaneously satisfies the competition's hard mandate (built on Google Cloud Agent Builder / Gemini Enterprise Agent Platform) and every structural requirement the behavioral profile imposes: typed graph state, durable checkpointing across a long-running continuous-stream lifecycle, and native interrupt/resume for the mandatory HITL gates — verified current and actively maintained, not assumed from training data.

**Key Capabilities Utilized:**
- Graph-based Workflow Runtime for the deterministic branching described in Section 4
- `LongRunningFunctionTool` pause/resume for the Section 4 HITL interrupt, matching the profile's "must not proceed until explicit approval" rule exactly
- Native MCP client support for reaching the Grafana MCP Server without a bolted-on integration layer

**Frameworks NOT Chosen:**
- **LangGraph (StateGraph/Pregel):** Offers equivalent typed-state and checkpointing capability, but sits outside the Google Cloud Agent Builder / Gemini Enterprise Agent Platform mandate the hackathon rules impose as a disqualification condition; adopting it would add a redundant orchestration layer with no capability gain over the platform-native engine.
- **CrewAI Flows / Pydantic-AI:** Both are viable current-generation engines in general, but neither is the platform-mandated toolchain here, and this system needs no crew-style role delegation (rejected on both fit and mandate grounds).
- **Simple SDK (direct Gemini API calls):** Insufficient — no native checkpointing or interrupt/resume primitive, which the mandatory long-running HITL pause requires.

**Deprecated Patterns Explicitly Avoided:**
Legacy LangChain `AgentExecutor` and unmanaged raw `while True` polling loops were both considered and rejected — the former is superseded by graph/typed-state engines industry-wide, and the latter would provide no checkpointing, no circuit breaker, and no typed state, directly violating the profile's evidence-trail and stop-condition requirements.

**Custom Components Required:**
The deterministic category-to-action lookup (Step 4) and the re-breach circuit breaker (Section 4) are thin custom logic layered on top of ADK's Workflow Runtime nodes — neither requires custom orchestration infrastructure beyond what ADK provides.

---

## **6. MCP & TOOL INVOCATION TOPOLOGY**

**Integration Model:** Hybrid — MCP client/server for observability reads, direct function-calling for remediation writes

**MCP Topology:**
- **Agent as MCP Client:** Confirmed — Genlock Sentinel's evidence-triage and root-cause-correlation nodes connect out to the Grafana MCP Server as an MCP client
- **MCP Servers Required (by capability):** A metrics/logs/traces query MCP server (Grafana MCP Server, as fixed by LLM-1's Input Contract — not a new selection made here)
- **Resource/Prompt/Tool Exposure:** Tools only (query operations against Prometheus/DCGM, Loki, and Tempo) — no MCP resources or prompts are consumed

**Direct Function-Calling Topology:**
- **Bound Functions (by capability):** Three reversible cluster-manager control functions (standby leadership failover, background texture-stream deprioritization, forced genlock re-sync handshake); three HITL-gated functions (take halt, capture-mode fallback, threshold-exceeding failover) bound separately and reachable only from the post-approval branch

**Trust Boundaries:**
Reasoning nodes (Gemini 3.1 Pro, Gemini 3.7 Flash) hold read-only MCP access to the Grafana MCP Server and no direct function bindings at all — they can observe and diagnose but cannot act, which structurally prevents excessive agency (the model itself never holds an actuator). The deterministic dispatch node holds bindings to exactly the three pre-approved reversible functions. The three HITL-gated functions exist as bindings only inside the post-approval branch of the graph, unreachable from any path that has not passed through the HITL Pause node with `approval_state = approved`. Google's Model Armor is configured as a policy-enforcement layer on the Grafana MCP Server tool-call/response boundary, sanitizing tool responses for prompt-injection and sensitive-data-disclosure content before that content ever reaches a Gemini context window — the architectural enforcement of LLM-1's prohibition against treating log/trace text as instructions.

---

## **7. MEMORY & CHECKPOINTING ARCHITECTURE**

**Memory Strategy:** Short-term (session-scoped) only

### **Short-Term Memory / Thread State**
- **Type:** Session state (the full `GenlockSentinelState` schema)
- **Duration:** Persists for the duration of one shoot session (matches LLM-1's Long-running Lifecycle Nature); a new session begins at each stage wrap
- **Contents:** Active drift events, evidence bundles, diagnosis history, remediation log, pending HITL card, approval state, error logs, config
- **Access:** Read/write per the Mutation Boundaries in Section 3
- **Checkpointing Backend:** Cloud SQL for PostgreSQL, via ADK's asyncpg session adapter — chosen over SQLite because the Long-running, high-stakes lifecycle requires production multi-node durability (a crashed worker must not lose in-flight diagnostic or HITL state), which SQLite's local-file model does not provide
- **Purpose:** Guarantees that a HITL pause, a worker restart, or a transient MCP outage never loses the evidence trail or forces a diagnostic cycle to restart from zero

### **Long-Term Memory**
- **Type:** None
- **Technology Class:** Not applicable
- **Contents:** Not applicable
- **Retrieval Strategy:** Not applicable
- **Update Strategy:** Not applicable
- **Purpose:** The behavioral profile contains no requirement for cross-session knowledge retrieval, semantic search, or learning from past shoot days — the three root-cause categories and their mappings are fixed and deterministic, not retrieved. Adding a vector store here would be unjustified persistence complexity for a system whose entire allowed capability set is served by session-scoped state.

**Memory Boundaries:**
- **What Must Be Remembered:** Every drift event's evidence, diagnosis, and resulting action for the duration of the shoot session, for audit and HITL card generation
- **What Must Be Forgotten:** Raw cluster credentials and network-topology secrets are never written into checkpointed state — they are resolved at call-time from Secret Manager and never persisted, per LLM-1's prohibition on leaking sensitive infrastructure detail
- **Retention Policy:** Session state is retained through the shoot session for audit purposes; retention beyond that is an operational/compliance decision outside this system's behavioral scope

**Memory and Behavioral Constraints:**
Because secrets are never written into `config` or any other state field, no downstream read of session state — including a HITL card rendered to a supervisor — can ever surface a credential, structurally enforcing LLM-1's Section 6 prohibition #5.

---

## **8. MODEL STRATEGY, ROUTING & COST**

**Verification Note:** Verified via live web search (September 2026). Current flagship is Gemini 3.1 Pro (GA rollout beginning February 2026, topping most tracked reasoning benchmarks). Current fast/workhorse model is Gemini 3.7 Flash (GA as of September 2026, Google's latest workhorse Flash release). The hackathon brief's reference to "Gemini 1.5 Pro/Flash" is superseded — the current Gemini Enterprise Agent Platform model catalog no longer centers on the 1.5 generation, so this blueprint specifies the current equivalents in the same Pro/Flash roles instead.

**Model Selection Philosophy:** Reasoning/execution split — a heavier model handles the one genuinely ambiguous cognitive task (multi-source root-cause correlation), while a fast, cheap model handles high-frequency structured work (evidence triage, HITL card packaging).

### **Primary (Reasoning) Model**
- **Model:** Gemini 3.1 Pro
- **Responsibility:** Root-Cause Correlation (Step 3) — the one step where evidence from three independent telemetry sources must be weighed against three candidate categories under a strict no-novel-hypothesis constraint
- **Why This Model:** Current flagship reasoning capability and strong structured-output reliability, needed because a wrong diagnosis either wastes a reversible action or, worse, misses an ambiguous case that should have gone to HITL

### **Secondary (Execution/Routing) Model**
- **Model:** Gemini 3.7 Flash
- **Responsibility:** Evidence Triage (Step 2) and HITL Card Generation (Step 5) — high-frequency, low-ambiguity structured extraction and formatting tasks
- **Why This Model:** Low latency is critical given the $800–$2,500/minute stage-burn cost of any delay, and both tasks are structured extraction/formatting rather than open-ended reasoning, which Flash handles reliably at a fraction of Pro's cost

**Routing Logic:**
Deterministic by node: Steps 2 and 5 always route to Flash; Step 3 always routes to Pro; Steps 1, 4, 6, and 7 never call a model at all (rule-based/mechanical).

**Reasoning vs Execution Split:** Yes
- **Reasoning Model:** Gemini 3.1 Pro reasons about which of three root-cause categories the evidence supports, and at what confidence
- **Execution Model:** Gemini 3.7 Flash executes the surrounding structured-extraction and formatting work
- **Handoff Logic:** Pro's diagnosis and confidence score are written to `diagnosis_history` in the shared state schema; Flash's HITL-card step reads that record directly rather than receiving it via a direct model-to-model handoff

**Prompt/Context Caching Strategy:**
The static system instruction (behavioral prohibitions, the three-category taxonomy, output JSON schemas) is identical across every diagnostic cycle within a shoot session and is cached via Gemini context caching, reused across every Step 2/3/5 call for that session rather than resent each time.

**Token Optimization Strategy:**
Raw Loki log lines and Tempo spans are pre-filtered to the breaching node's `frame_id` window before being passed to the Flash triage step — full unfiltered log/trace payloads never enter a model context window. The Pro correlation step receives only the current event's evidence bundle plus, at most, the last few related `diagnosis_history` entries for that `node_id` — not the full session history, which would otherwise grow unbounded over a long shoot day.

**Fallback Strategy:**
- **Primary Model Failure:** If Gemini 3.1 Pro is unavailable or errors, the event is marked ambiguous and routed to the HITL path rather than guessed at with a lesser model — consistent with the profile's rule that diagnostic uncertainty always converts to escalation
- **Fallback Model:** None substituted for Pro's role — degrading to Flash for root-cause correlation would violate the profile's reasoning-depth constraint
- **Escalation Path:** Repeated Pro failures within a session raise a "telemetry/model unavailable" failure condition per LLM-1 Section 10, halting new autonomous cycles and alerting the supervisor

**Cost & Scalability Analysis:**
- **Estimated Cost Per Task:** Low ( < $0.05 per diagnostic cycle) — one Pro call and two Flash calls per drift event, not per telemetry sample
- **Most Expensive Step:** Root-Cause Correlation (Step 3) — the only Pro call, and the one with the largest context (the full evidence bundle)
- **Scalability Bottleneck:** Cloud SQL checkpoint write contention if many cluster nodes drift simultaneously on a large volume — mitigated by keying `active_drift_events` and `evidence_bundle` per `node_id`/`event_id` so writes are independent rather than serialized through one monolithic row
- **Optimization Strategy:** Reasoning/execution split keeps the expensive model off the high-frequency path; context caching and per-event token trimming keep per-cycle cost flat rather than growing across a long shoot day

---

## **9. TOOL INVOCATION STRATEGY**

**Tool Usage Permission:**
Only the evidence-triage and root-cause-correlation nodes may invoke MCP query tools (read-only). Only the deterministic dispatch node may invoke remediation function calls (write), and only within the trust boundaries defined in Section 6.

**Invocation Pattern:**
- **Direct Invocation:** Yes, for the three pre-approved reversible actions
- **Approval Required:** Yes, for take-halt, capture-mode fallback, and threshold-exceeding failover
- **Batching:** No — each drift event is diagnosed and acted on individually; batching diagnostic cycles across nodes would blur the per-node evidence trail the profile requires

**Tool Access Control:**
Single-agent system — access control is enforced per node within the one agent's graph, as specified in Section 6's trust boundaries, rather than between multiple agents.

**Guardrails:**
- **Rate Limiting Strategy:** Token bucket on Grafana MCP Server query calls per session, sized to the expected telemetry sampling rate, to prevent a noisy cluster from starving the diagnostic path
- **Cost Control:** Session-level budget cap on Gemini API spend; if approached, new autonomous diagnostic cycles halt and escalate rather than silently degrading diagnosis quality
- **Permission Checks:** Every remediation function call is checked against the trust-boundary binding table in Section 6 before execution — a call with no matching binding is structurally impossible, not merely policy-blocked
- **Validation:** Every MCP tool response passes through Model Armor sanitization before being written into `evidence_bundle`; every remediation action is validated against the current `config` financial threshold before dispatch
- **Prohibited Actions:** Halt, capture-mode fallback, and threshold-exceeding failover calls have no binding outside the post-approval branch — per Section 6, these functions do not exist as callable options anywhere else in the graph

**Tool Call Flow:**
1. Evidence-triage/correlation node determines an MCP query or remediation call is needed
2. Model Armor sanitizes the MCP response (query path) before it re-enters the graph
3. Approval gate check (remediation path only) — post-approval branch or pre-approved category only
4. Tool/MCP execution
5. Result written into typed state via the field's declared reducer (Section 3)
6. Graph continues to the next step or pauses for HITL, per Section 4

**Tool Failure Handling:**
A failed MCP query retries with backoff (Section 11); a failed remediation function call is logged to `error_logs` and immediately escalated to HITL rather than silently retried, since a failed reversible action may indicate the diagnosis itself was wrong.

---

## **10. ASYNC EXECUTION & CHECKPOINTING STANDARDS**

**Execution Model:** Async-native (Python `asyncio`, matching ADK's async session and tool-call model)

**Justification:**
The Continuous Stream trigger and Long-running lifecycle from LLM-1 both require non-blocking I/O by nature — the stream watcher must keep consuming telemetry while a diagnostic cycle is in flight for a different node, and a HITL pause must not block the entire process while awaiting a human response that could take minutes. A synchronous design would serialize unrelated nodes' events behind one pending approval, which the profile's per-node concurrency (Section 3's merge-by-key reducers) explicitly anticipates.

**Checkpointing Cadence:**
State is checkpointed to Cloud SQL for PostgreSQL after every node transition in Section 4 — most critically, immediately before the HITL Pause node suspends, and immediately after a supervisor's approval/denial is received.

**Resumability:**
On a worker crash or restart, the graph resumes from the last checkpointed node for every session with a persisted `session_id`, using ADK's state-based recovery — no drift event's evidence or diagnosis is lost, and no HITL card that was already presented to a supervisor needs to be regenerated.

---

## **11. FAILURE & RECOVERY ARCHITECTURE**

**Failure Detection:**
Each node reports success/failure into `error_logs`; the graph's own step timing (time since threshold breach) is compared against the take's live-capture window to detect whether a diagnostic cycle is at risk of not resolving in time.

**Failure Categories:**

### **Transient Failures** (Retryable)
- **Examples:** Grafana MCP Server timeout, Gemini API rate limit, temporary Cloud SQL write contention
- **Response:** Retry with exponential backoff, max 3 attempts
- **Backoff Strategy:** 1s, 2s, 4s between attempts, then treat as a permanent failure for that cycle

### **Permanent Failures** (Non-Retryable)
- **Examples:** Telemetry source (Prometheus/Loki/Tempo) unavailable past retry budget, a prohibited action attempted, Model Armor flags an injection attempt in ingested log/trace content
- **Response:** Halt the diagnostic cycle for that event, log full context to `error_logs`, alert the supervisor immediately (not via the normal HITL card path — this is a failure alert, not a remediation approval request)

### **Ambiguous Failures** (Uncertain)
- **Examples:** Root-cause diagnosis does not cleanly resolve to one of the three known categories, confidence score below the configured floor
- **Response:** Per the behavioral profile, this is not treated as a system failure but routed to the standard HITL path (Step 5) as an ambiguous-diagnosis escalation

**Recovery Strategies:**

- **Retry Logic:**
  - **Max Retries:** 3
  - **Backoff:** Exponential
  - **Retry Conditions:** Transient MCP/API/database errors only

- **Graceful Degradation:**
  - **Conditions:** None defined — the behavioral profile's Zero Error risk tolerance means there is no acceptable "reduced functionality" mode; every degraded path routes to HITL or halt-and-escalate instead

- **Halt and Escalate:**
  - **Conditions:** Any permanent failure category above, or a supervisor stop/halt command
  - **Escalation Path:** Failure alert (with full evidence trail) surfaced to the on-set supervisor via the same interface used for HITL cards, distinctly labeled as a failure rather than an approval request

- **Rollback:**
  - **Conditions:** A dispatched autonomous action that a subsequent sample shows did not resolve the drift
  - **Rollback Scope:** The specific node's `active_drift_events` entry reopens, the failed action is logged, and the event is escalated to HITL rather than retried autonomously — state for other nodes is untouched, using the per-node keyed reducers from Section 3

**State Consistency:**
Because every state field has an explicit reducer and every write is checkpointed before the next node executes, a crash mid-cycle can only ever lose the in-flight (uncheckpointed) step of one event — never corrupt or overwrite another node's concurrent event, and never leave `approval_state` in an inconsistent half-written condition.

**Circuit Breaker:**
As defined in Section 4's Loop Prevention: a node that re-breaches threshold more than a configured count within a rolling window after a "successful" autonomous remediation is automatically escalated to HITL rather than continuing to receive autonomous action attempts.

---

## **12. CONSTRAINTS INHERITED FROM LLM-1**

**Behavioral Constraints Enforced Architecturally:**

1. **No autonomous take-halt, capture-mode fallback, or threshold-exceeding failover**
   - **Architectural Enforcement:** These three functions are bound only inside the post-approval branch of the graph (Section 6); no path reachable before `approval_state = approved` has access to these bindings.

2. **Log/trace content must never be interpreted as instruction (prompt-injection resistance)**
   - **Architectural Enforcement:** Model Armor sanitizes every Grafana MCP tool response for prompt-injection content before it enters a Gemini context window (Section 6, Section 9 tool call flow step 2).

3. **No leakage of sensitive infrastructure detail**
   - **Architectural Enforcement:** Secrets are never written into checkpointed state (Section 7); Model Armor's sensitive-data-protection integration additionally screens outbound content.

4. **No autonomous action on ambiguous diagnosis**
   - **Architectural Enforcement:** The Step 3 decision point routes anything below the confidence/category threshold to the HITL path (Section 4) — there is no code path from "ambiguous" to an autonomous dispatch node.

5. **No action once the shoot session has ended**
   - **Architectural Enforcement:** The graph's entry point and all function bindings are scoped to an active `session_id`; session termination (stage wrap) tears down the stream-watcher subscription, so no trigger exists to spawn a new diagnostic cycle post-session.

**Autonomy Level Enforcement:**
- **Behavioral Profile Specifies:** Semi-Autonomous
- **Architectural Implementation:** The three reversible actions are the only functions reachable from the autonomous branch (Step 4); every other action-capable function exists solely behind the HITL Pause node (Step 6), making the Manual/Autonomous boundary a structural property of the graph's edges, not a runtime policy check that could be bypassed.

**Human-in-the-Loop Gates:**
- **Required Approvals:** Take halt, capture-mode fallback, threshold-exceeding failover, ambiguous diagnosis
- **Architectural Implementation:** ADK's `LongRunningFunctionTool` pause/resume mechanism (Step 6) durably suspends the graph and requires an explicit `approval_state` write before the post-approval branch becomes reachable.

**Prohibited Actions:**
- **From Behavioral Profile:** General Kubernetes/SaaS administration, creative content generation, post-production operation, direct cast/crew communication
- **Architectural Prevention:** None of these capabilities have any corresponding node, tool binding, or MCP server connection anywhere in this graph — they are absent by construction, not filtered at runtime.

**Data Contract Fidelity:**
- **Input Contract (from LLM-1):** Prometheus/DCGM metrics, Loki logs, Tempo traces, via Grafana MCP Server, semi-structured
- **Output/Deliverable Contract (from LLM-1):** Remediation action records and structured HITL cards
- **Schema Enforcement:** `active_drift_events`/`evidence_bundle` (entry) and `remediation_log`/`pending_hitl_card` (exit) in Section 3 map one-to-one onto these contracts with no reinterpretation.

**Scope Boundaries:**
- **In Scope:** Genlock/frame-sync drift detection and remediation during live ICVFX capture only
- **Out of Scope:** General infrastructure monitoring, creative generation, post-production, budget/scheduling decisions beyond the threshold check, direct stakeholder communication
- **Architectural Enforcement:** As with Prohibited Actions above — out-of-scope capabilities have no represented node or tool binding in this graph at all.

**Verification Statement:**
This architecture fully respects all constraints defined in AGENT_BEHAVIOR_PROFILE.md.
No behavioral boundary can be violated by this orchestration design.

---

## **ARCHITECTURE INTEGRITY DECLARATION**

This orchestration blueprint is AUTHORITATIVE.

All downstream systems must:
- Implement agent topology exactly as specified
- Follow execution flow without deviation
- Implement the typed state schema and reducers exactly as specified
- Use the specified orchestration framework
- Implement MCP/tool topology as designed
- Implement memory and checkpointing architecture as designed
- Route to models as specified, including caching and cost strategy
- Enforce tool invocation guardrails
- Handle failures per recovery strategies
- Respect all inherited behavioral constraints

No architectural decision may be changed without invalidating this blueprint.

---
