# INTERFACE & OBSERVABILITY SYSTEM

**Generated:** September 7, 2026
**Source:** AGENT_LOGIC_SPEC.md
**Status:** AUTHORITATIVE — Defines complete human-agent interaction and telemetry layer
**Purpose:** Interface design, streaming protocol, and observability specification

---

## **1. INTERACTION PHILOSOPHY**

**Overall Interaction Model:** Task-First

**Description:**
Genlock Sentinel has no conversational back-and-forth — its single user, the on-set supervisor, is monitoring a continuous live process, not chatting with an assistant. The interface is a live operations console: a running timeline of drift events, diagnoses, and actions, punctuated by approval cards when the agent needs a decision.

**Human vs Agent Initiative:**
- **User-Driven:** The supervisor initiates only a session start/stop and, when engaged, an Approve/Deny decision.
- **Agent-Driven:** All continuous monitoring, evidence gathering, diagnosis, and the three pre-approved reversible remediations happen without any user action, per the Semi-Autonomous autonomy level.
- **Collaborative:** Every HITL escalation (ambiguous diagnosis, take halt, capture fallback, threshold-exceeding failover) is collaborative — the agent proposes with full evidence, the supervisor decides.

**This Agent's Initiative Model:**
Agent-driven by default, switching to Collaborative only at the four defined HITL triggers. There is no Manual mode and no Fully Autonomous mode to switch between — the autonomy split is fixed by LLM-1/LLM-2, so the console does not offer a mode toggle.

**Transparency vs Simplicity Balance:**

**Transparency Priority:**
Every autonomous action, every diagnosis, and every piece of evidence behind a HITL card must be visible and traceable — the profile's Zero Error risk tolerance and the hackathon's own requirement to demonstrate a visible Gemini reasoning trace both demand this.

**Simplicity Priority:**
During an active take, the console must not force the supervisor to read a full reasoning transcript to understand what's happening — a one-line timeline entry plus a confidence badge must be enough to follow along in real time.

**Balance Strategy:**
Show a compact, always-visible timeline by default; keep the Gemini 3.1 Pro node's native reasoning trace collapsed inline but one click away, and reserve full raw-prompt/trace detail for a debug panel.

**Interaction Principles:**
1. The console never hides an autonomous action after the fact — every reversible remediation appears on the timeline the moment it is dispatched, not just on request.
2. The supervisor's Approve/Deny decision is always the final word on the three HITL-gated actions; the console never auto-resolves a pending card.
3. Uncertainty is shown as a number, not implied — every diagnosis carries its confidence score, and "ambiguous" is rendered as a distinct, honest state, never dressed up as a low-confidence category guess.

---

## **2. PRIMARY USER INTERFACE**

**Core Interaction Surface:**
A live operations console — a single-screen dashboard for the duration of a shoot session, not a chat window or a task-list-and-tickets board.

**Layout Structure:**
Center column: a real-time sync-offset chart per active cluster node plus a vertical activity timeline below it. Right sidebar: per-node status chips (monitoring / diagnosing / awaiting_approval / remediated) for every node currently or recently in `active_drift_events`. A full-width approval-card overlay appears only when `session_status = awaiting_approval` for any event — it is modal and cannot be dismissed without an explicit Approve or Deny.

**Message Types:**

### **User Messages**
- **Format:** Structured actions only — Approve, Deny, Stop Session. No free-text chat input exists, since the cognitive spec defines no conversational tool or structured output that consumes free text from the supervisor.
- **Input Mechanisms:** Buttons on the approval card; a persistent Stop Session control in the console header.
- **Display:** Every supervisor action is stamped into the timeline immediately (e.g., "Supervisor approved threshold-exceeding failover for render-07").

### **Agent Messages**
- **Format:** Structured timeline entries and rich cards — never freeform prose, since no node in the cognitive spec produces conversational text output.
- **Display:** Each of the seven graph nodes' completions appends one timeline entry, populated as its events stream in.
- **Components:** Sync-offset chart, per-node status chips, diagnosis badges, evidence cards, approval-card overlay, remediation log entries.

### **System Messages**
- **Purpose:** Session start/end, failure alerts (Section 9/11 permanent failures), Model Armor content-block notices.
- **Display:** Distinct red/amber banner styling, always pinned above the timeline until acknowledged — these are never just another timeline row, since a failure alert is categorically different from a routine diagnosis per LLM-3 Section 9.

### **Tool Output Messages**
- **Purpose:** Results of `query_loki_logs`, `find_slow_requests`, `get_trace_by_id`, and the six internal remediation/HITL-gated tools.
- **Display:** Condensed into the Evidence card (Section 4a) and Remediation log entries — raw tool JSON is never shown in the main timeline, only in the debug panel (Section 6).
- **Interactivity:** Evidence cards are expandable; remediation log entries link back to the diagnosis and evidence that justified them.

**Technical Implementation Specs:**

**Frontend Tech Recommendations:**
- **Component/Streaming Library:** AG-UI (Agent-User Interaction Protocol) client runtime — verified (September 2026) as a maturing, ecosystem-wide standard for agent↔frontend streaming with native support for tool-call lifecycles, shared-state sync, and a dedicated `RUN_PAUSED` HITL primitive; adapters exist for LangGraph, CrewAI, Mastra, AG2, Agno, and LlamaIndex, and a dedicated `adk-agui-middleware` package bridges Google ADK's native event stream to AG-UI over SSE.
- **Component Library:** Shadcn/UI — the conventional pairing for AG-UI-based frontends (per the `create-ag-ui-app` starter), and suitable for the chart/card/badge components this console needs.
- **Reason:** ADK is the platform mandated for this build; rather than inventing a bespoke event schema, bridging ADK's native `Runner` events through the verified AG-UI protocol gives a standard, ecosystem-supported event vocabulary with first-class tool-call and HITL-pause semantics already defined.

**Connection Protocol:**
- **Protocol:** Server-Sent Events (SSE)
- **Verification Note:** Verified via live research (September 2026): ADK's `Runner` natively supports `StreamingMode.SSE` for partial-event, typewriter-style streaming, and ADK's own streaming guide recommends SSE specifically "when you don't need client-to-server streaming, such as when user input comes through separate HTTP POST requests" — which matches this console exactly, since Approve/Deny/Stop are discrete POSTs, not a continuous duplex conversation. ADK's `StreamingMode.BIDI` (WebSocket, via the Live API) exists only for voice/video interaction and is not applicable here.
- **Justification:** SSE is simpler infrastructure, is the ADK-native and AG-UI-native transport, and this agent has no requirement for low-latency bidirectional voice/video — Approve/Deny/Stop as separate HTTP POSTs is sufficient and is the pattern ADK's own documentation recommends for this exact shape of interaction.

**Accessibility (A11y) Standards:**
- **Live Regions:** The activity timeline and the approval-card overlay are both `aria-live="polite"` regions, except a newly-opened approval card, which is announced `aria-live="assertive"` once (not per streamed token) so a screen-reader supervisor is not interrupted mid-sentence but is unmissably alerted to a pending decision.
- **Keyboard Nav:** Approve/Deny/Stop are always reachable via keyboard shortcut, since a supervisor may be working with a keyboard-only setup during a live shoot; focus moves to the approval card automatically when it opens.
- **Screen Readers:** "Diagnosing render-07..." is announced once per node-transition (`STEP_STARTED`), not on every streamed reasoning token, to avoid spamming.

**Responsive Strategy:**
- **Mobile View:** The sync-offset chart and per-node status chips collapse into a single scrollable status list; the approval card remains full-screen and is the only view a mobile session prioritizes, since a supervisor checking from a phone needs the decision surface first.
- **Desktop View:** Full three-panel layout (chart, timeline, node-status sidebar) plus a collapsible debug panel.

**Streaming Behavior:**

**Streaming Granularity:** Step-by-step for graph-node transitions; token-by-token only for the Gemini 3.1 Pro node's native reasoning trace when expanded.

**Streaming Strategy:**
- **Agent Text:** N/A — no node produces free conversational text; structured fields stream as they are produced by each structured-output node.
- **Agent Reasoning:** Native thinking tokens (Gemini 3.1 Pro, Root-Cause Correlation node) stream live into a collapsed panel via `REASONING_MESSAGE_CONTENT` deltas; graph-trace steps stream as discrete `STEP_STARTED`/`STEP_FINISHED` events, not token-by-token.
- **Tool Execution:** Each of the three Evidence Triage query tools streams `TOOL_CALL_START` → (result) → `TOOL_CALL_RESULT`; the console shows a per-tool status chip that resolves from spinner to check/cross.

**Real-Time Updates:**
- **Status Indicators:** Live per-node chips (monitoring / diagnosing / awaiting_approval / remediated / failed) update on every `STEP_STARTED`/`STEP_FINISHED`.
- **Progress Bars:** Not used — diagnostic cycles are short enough (Section 4 "Latency & Waiting States") that a spinner plus elapsed-time text suffices.
- **Cancellation:** The supervisor can issue Stop Session at any time; this is a hard interrupt (Section 7), not a per-tool cancel, since individual tool calls are short and internal.

**Message Threading:**
Grouped by drift event — every timeline entry for a given `event_id` is visually clustered (e.g., a card grouping "render-07 · f-88213: breach detected → evidence gathered → diagnosed: network_jitter (0.93) → failover dispatched → resolved"), so concurrent events on different nodes never interleave confusingly.

---

## **2a. TYPED STREAMING EVENT DATA CONTRACT**

**Protocol Verification Note:** Verified against the current AG-UI protocol specification and Python SDK (`ag_ui.core.EventType`, September 2026) and against ADK's native `StreamingMode.SSE` partial-event model. Event names below are drawn directly from AG-UI's verified `EventType` enum, not invented.

**Transport:** SSE, matching Section 2.

**Event Type Vocabulary:**

```
data: {"type": "RUN_STARTED", "runId": "...", "threadId": "..."}
data: {"type": "STEP_STARTED", "step_name": "evidence_triage", "event_id": "..."}
data: {"type": "TOOL_CALL_START", "toolCallId": "...", "toolCallName": "query_loki_logs"}
data: {"type": "TOOL_CALL_ARGS", "toolCallId": "...", "delta": "{\"datasource_uid\":..."}
data: {"type": "TOOL_CALL_END", "toolCallId": "..."}
data: {"type": "TOOL_CALL_RESULT", "toolCallId": "...", "content": "{\"success\":true,...}"}
data: {"type": "REASONING_START", "messageId": "..."}
data: {"type": "REASONING_MESSAGE_START", "messageId": "..."}
data: {"type": "REASONING_MESSAGE_CONTENT", "messageId": "...", "delta": "Weighing network RTT evidence against..."}
data: {"type": "REASONING_MESSAGE_END", "messageId": "..."}
data: {"type": "REASONING_END"}
data: {"type": "STATE_DELTA", "delta": [{"op": "add", "path": "/diagnosis_history/-", "value": {...}}]}
data: {"type": "RUN_PAUSED", "runId": "...", "reason": "hitl_approval_required"}
data: {"type": "STEP_FINISHED", "step_name": "root_cause_correlation", "event_id": "..."}
data: {"type": "RUN_ERROR", "message": "...", "code": "..."}
data: {"type": "RUN_FINISHED", "runId": "..."}
```

**Per-Event Field Definitions:**

### **RUN_STARTED**
- **When Emitted:** Once, at Stream Watch's session initialization (LLM-3 Section 2's graph entry).
- **Fields:** `runId` (session run identifier), `threadId` (maps to `session_id`).
- **UI Handling:** Console initializes the console shell and begins listening.

### **STEP_STARTED / STEP_FINISHED**
- **When Emitted:** On entry/exit of each of the seven graph nodes in LLM-3's Execution Flow, for a given `event_id`.
- **Fields:** `step_name` (one of: `stream_watch`, `evidence_triage`, `root_cause_correlation`, `autonomous_dispatch`, `hitl_card_generation`, `hitl_pause`, `post_approval_handling`), `event_id`.
- **UI Handling:** Advances the per-event cluster's step tracker (Section 3b) and updates the node's status chip.

### **TOOL_CALL_START / TOOL_CALL_ARGS / TOOL_CALL_END**
- **When Emitted:** When the Evidence Triage node invokes `query_loki_logs`, `find_slow_requests`, or `get_trace_by_id` (Tool/Function Calling mode per LLM-3), or when a dispatch node invokes a remediation/HITL-gated tool.
- **Fields:** `toolCallId`, `toolCallName`, `delta` (streamed argument JSON fragment, ARGS only).
- **UI Handling:** Shows the per-tool status chip transitioning spinner → in-progress; argument deltas are not rendered to the supervisor (internal-only, per Section 10's non-goals) but are captured in the debug panel.

### **TOOL_CALL_RESULT**
- **When Emitted:** On tool completion (success or failure).
- **Fields:** `toolCallId`, `content` (JSON string matching the tool's Output schema from LLM-3 Section 4).
- **UI Handling:** Resolves the tool chip to check/cross; feeds the Evidence card (Section 4a) once all three query tools for an event have resolved.

### **REASONING_START / REASONING_MESSAGE_START / REASONING_MESSAGE_CONTENT / REASONING_MESSAGE_END / REASONING_END**
- **When Emitted:** Only for the Gemini 3.1 Pro Root-Cause Correlation node's native thinking output, per Section 3a below.
- **Fields:** `messageId`, `delta` (reasoning text fragment).
- **UI Handling:** Populates the collapsed reasoning panel live if expanded; otherwise buffered silently until the supervisor expands it.

### **STATE_DELTA**
- **When Emitted:** Whenever a node writes to the shared typed state (LLM-2's `GenlockSentinelState`), expressed as a JSON Patch matching that field's declared reducer.
- **Fields:** `delta` (array of JSON Patch operations — `add` for append-only fields, custom merge semantics surfaced as `add`/`replace` at the keyed path for merge-by-key fields, `replace` for last-write-wins fields).
- **UI Handling:** Drives every card and chip in the console — the console holds no state the backend didn't explicitly write via a `STATE_DELTA` matching Section 2a of this contract to LLM-2's reducers.

### **RUN_PAUSED**
- **When Emitted:** When the graph enters the HITL Pause node (LLM-3 Section 4, Step 6).
- **Fields:** `runId`, `reason` (`"hitl_approval_required"`).
- **UI Handling:** Opens the modal approval-card overlay (Section 5); the card's content itself arrives via the immediately-preceding `STATE_DELTA` writing `pending_hitl_card`.

### **RUN_ERROR**
- **When Emitted:** On any permanent failure (LLM-3 Section 9) — telemetry source exhausted, Model Armor block, or an invalid-output retry exhaustion.
- **Fields:** `message`, `code`.
- **UI Handling:** Raises the System Message failure banner (Section 2); does not close the session unless the failure is session-fatal.

### **RUN_FINISHED**
- **When Emitted:** At shoot-session end (stage wrap).
- **Fields:** `runId`.
- **UI Handling:** Closes the console session and surfaces the session summary (all resolved/failed/escalated events).

**Ordering & Backpressure Guarantees:**
Events for a given `event_id` are strictly ordered (`STEP_STARTED` before any of that step's `TOOL_CALL_*`/`REASONING_*`/`STATE_DELTA` events, which precede that step's `STEP_FINISHED`), per AG-UI's run/step framing. Events for different concurrent `event_id`s carry no ordering guarantee relative to each other, matching the merge-by-key concurrency LLM-2 designed into `active_drift_events`/`evidence_bundle`. On client reconnect mid-stream, the console requests a `STATE_SNAPSHOT`-equivalent full-state resync from the backend's checkpointed session state (Cloud SQL for PostgreSQL, per LLM-2 Section 7) rather than replaying the event log from the start.

---

## **3. REASONING VISIBILITY MODEL**

**Visibility Philosophy:**
The graph-based execution flow (LLM-3 Section 2) has two categorically different kinds of "thinking" worth showing separately: the Gemini 3.1 Pro node's own token-level reasoning about which of three categories fits the evidence, and the higher-level fact of which graph node is currently active. Conflating them would either drown the supervisor in reasoning tokens during routine monitoring or hide the one place deep reasoning actually happens.

### **3a. Native Model Thinking Tokens**

**Applicability:** Yes — the Root-Cause Correlation node (Gemini 3.1 Pro) is the one node in this system doing genuinely deep, weighed reasoning (LLM-3 Section 1's prompt explicitly instructs it to "think step-by-step... weigh the metric, log, and trace evidence against each of the three category definitions explicitly"), so its native thinking output is the reasoning trace worth exposing. The Evidence Triage and HITL Card Generation nodes (Gemini 3.7 Flash) perform structured extraction/formatting, not weighed judgment, so no dedicated thinking-token panel is defined for them — their work is instead shown at the graph-trace level (Section 3b).

**UI Treatment:**
- **Component:** A collapsible "Diagnosis reasoning" panel attached to that event's cluster in the timeline, distinct from the step tracker.
- **Default State:** Collapsed. During an active take, the supervisor needs the diagnosis result and confidence score, not the reasoning transcript; the panel is one click away and its existence is signaled by a small "view reasoning" affordance next to every diagnosis badge.
- **Streaming Behavior:** `REASONING_MESSAGE_CONTENT` deltas populate the panel live if the supervisor has it expanded at the time; otherwise the full text is buffered and available instantly on expansion — the diagnosis badge itself does not wait for reasoning to finish, since `RootCauseDiagnosis` is the load-bearing structured output and reasoning is supplementary.
- **Safety Note:** Per Section 3c, if any reasoning content references evidence flagged as a suspected instruction-injection anomaly, that portion is replaced with `[reasoning based on flagged content — see anomaly note]` rather than displayed verbatim.

### **3b. Graph Node / Multi-Step Agent Traces**

**Applicability:** Yes — LLM-2's graph-based execution flow has seven distinct nodes per drift event, and making that sequence visible is exactly what the hackathon's own trailer requirement ("Gemini multi-step reasoning trace") calls for.

**UI Treatment:**
- **Component:** A horizontal step tracker inside each event's timeline cluster (Stream Watch → Evidence Triage → Root-Cause Correlation → [Autonomous Dispatch | HITL Card Generation → HITL Pause → Post-Approval Handling]).
- **What's Shown Per Step:** Node name, a one-line summary of its action (e.g., "Queried Loki + Tempo for render-07 window"), and which state fields it touched (e.g., "wrote evidence_bundle[f-88213]").
- **Streaming Behavior:** Driven entirely by `STEP_STARTED`/`STEP_FINISHED` plus the `TOOL_CALL_*` and `STATE_DELTA` events nested within each step's span.
- **Clutter Prevention:** Lives inside the collapsed event cluster, not as separate timeline rows — a routine, fully-autonomous event collapses to one summary line ("render-07 · network_jitter (0.93) → failover dispatched · resolved in 4.2s") with the full step tracker available on click.

**Visible Reasoning Components:**

### **Evidence Triage step**
- **What's Shown:** Which of the three query tools were called and whether each succeeded, condensed into the Evidence card (Section 4a).
- **When Shown:** Inline, as the step completes.
- **Format:** Three small tool-status icons plus the condensed evidence summary text.
- **User Control:** Expandable to see the full `log_summary`/`trace_summary` text.

### **Root-Cause Correlation step**
- **What's Shown:** The `RootCauseDiagnosis` badge (category + confidence) plus the collapsed native-reasoning panel (Section 3a).
- **When Shown:** Inline, as a prominent badge the moment the structured output resolves.
- **Format:** Colored badge (green for a clean autonomous-eligible category, amber for a HITL-gated category, red for ambiguous).
- **User Control:** Reasoning panel expandable per Section 3a; badge itself is always visible, never hidden.

### **HITL Card Generation / HITL Pause steps**
- **What's Shown:** The full `HITLCardPackage` content, rendered as the approval-card overlay (Section 5) — this is never summarized, since it is the one moment requiring full supervisor attention.
- **When Shown:** Immediately, as a blocking modal.
- **Format:** See Section 5.
- **User Control:** Not collapsible while pending.

**Summarization Strategy:**

**When to Summarize:** Every fully-autonomous, successfully-resolved event, once resolved — collapses to a one-line timeline summary.

**How to Summarize:** Show node_id, final category, confidence, action taken, and resolution time; hide the intermediate step tracker and reasoning panel behind a click.

**When to Show Full Detail:** Any event currently `awaiting_approval` (full HITL card, unsummarized) or any event whose diagnosis was `ambiguous` or that failed (full step tracker expanded by default, since these are the cases the supervisor most needs to understand).

**Progressive Disclosure:**

**Default View:** One-line summaries for resolved autonomous events; full detail for anything pending or failed.

**Expandable View:** Full step tracker, full evidence text, full native-reasoning transcript — available for any event, resolved or not.

**Hidden Entirely:** Raw tool-call argument JSON (`TOOL_CALL_ARGS` deltas) and raw ADK/session internals — these carry no decision-relevant information for the supervisor and are debug-panel-only (Section 6).

### **3c. Safety Filters for Sensitive Reasoning**

**Content That Must Be Filtered:**
- Any reasoning or evidence text a tool response flagged as a suspected prompt-injection attempt (per LLM-3 Section 8's grounding rules) — displaying it verbatim could itself surface the injected content to the supervisor's screen.
- Any raw infrastructure secret that should never have entered state in the first place (Section 7 of LLM-3) — defense-in-depth, in case one somehow appears in a tool result.

**Filtering Strategy:** Replaced with a short bracketed note (`[content withheld — flagged as anomaly, see evidence card]`) rather than silently omitted, so the supervisor knows something was filtered rather than assuming the evidence was simply thin.

**Transparency About Filtering:** Always disclosed — the anomaly banner on the Evidence card (Section 4a) explicitly states when this has occurred; nothing is filtered without a visible trace that filtering happened.

---

## **4. TOOL & ACTION OBSERVABILITY**

### **Grafana/Tempo MCP query tools (query_loki_logs, find_slow_requests, get_trace_by_id)**

**Before Execution:**
- **Announcement:** "Gathering logs and trace data for render-07..."
- **Streaming Event:** `TOOL_CALL_START`
- **Parameters Shown:** Node_id and time window only (summary); full LogQL/TraceQL query strings are debug-panel-only.
- **User Approval:** None required — read-only observability queries.

**During Execution:**
- **Status Indicator:** Small per-tool spinner chip (one per tool).
- **Streaming Event:** `TOOL_CALL_ARGS` (not rendered to the supervisor, captured for debug).
- **Estimated Duration:** Not shown — these calls are expected to resolve in low seconds.
- **Cancellation:** Not offered per-tool; the supervisor's only cancellation surface is the session-level Stop.

**After Execution:**
- **Streaming Event:** `TOOL_CALL_RESULT`
- **Success Display:** Chip resolves to a checkmark; feeds the Evidence card once all three tools for the event have resolved.
- **Output Visibility:** Condensed `EvidenceBundleExtraction` summary shown by default; raw tool output available in the debug panel.
- **Output Format:** Text summary in the Evidence card (Section 4a); raw JSON in debug mode.

**Failure Display:**
- **Streaming Event:** `TOOL_CALL_RESULT` with `success: false`, or `RUN_ERROR` if retries are exhausted.
- **Error Message:** "Loki logs unavailable for render-07 (query timeout after 3 attempts)."
- **Retry Option:** Automatic, per LLM-3's exponential backoff — no manual retry button, since this happens within the diagnostic cycle before the supervisor is ever engaged.
- **Fallback Communication:** The Evidence card shows `logs_available: false` plainly rather than omitting the log section.

### **Reversible remediation tools (failover_cluster_leadership, deprioritize_texture_streaming, force_genlock_resync)**

**Before Execution:**
- **Announcement:** "Dispatching standby failover for render-07 (network_jitter, confidence 0.93)."
- **Streaming Event:** `TOOL_CALL_START`
- **Parameters Shown:** The diagnosis category and confidence that justified the action.
- **User Approval:** None — pre-approved per Semi-Autonomous autonomy.

**During Execution:**
- **Status Indicator:** "Dispatching..." chip.
- **Streaming Event:** `TOOL_CALL_ARGS` (debug-only).
- **Estimated Duration:** Not shown.
- **Cancellation:** Not offered — these actions are near-instantaneous cluster-manager calls.

**After Execution:**
- **Streaming Event:** `TOOL_CALL_RESULT`
- **Success Display:** Green "Resolved" chip on the event cluster; appended to the Remediation log.
- **Output Visibility:** Action name and timestamp always shown.
- **Output Format:** Timeline entry with a link back to the diagnosis.

**Failure Display:**
- **Streaming Event:** `TOOL_CALL_RESULT` with `success: false`.
- **Error Message:** "Failover attempt on render-07 failed — escalating to supervisor."
- **Retry Option:** None automatic — per LLM-3, a failed reversible action escalates to HITL rather than retrying blind.
- **Fallback Communication:** The event immediately transitions to an approval-card overlay explaining the failed attempt.

### **HITL-gated tools (halt_live_take, fallback_to_greenscreen, execute_threshold_exceeding_failover)**

**Before Execution:**
- **Announcement:** Never shown as "about to execute" — these only fire after the supervisor's explicit Approve, at which point the approval card itself already fully described the action.
- **Streaming Event:** `TOOL_CALL_START` (fires only inside the post-approval branch).
- **Parameters Shown:** N/A — the card already showed everything before approval.
- **User Approval:** Required, per Section 5.

**During/After Execution:** Same status/result treatment as the reversible tools above, appended to the Remediation log with an "Approved by supervisor" tag.

**Failure Display:** "Take-halt command failed to execute — this requires immediate manual intervention," shown as a System Message failure banner (Section 2), since a failed HITL-approved safety action is the single highest-urgency failure state in this system.

**Input/Output Visibility Rules:**

**Always Show:** Diagnosis category, confidence, action taken, resolution status, cost delta and visual impact score on any HITL card.

**Show on Request:** Raw LogQL/TraceQL query strings, raw tool JSON, native reasoning transcript.

**Never Show:** Any cluster credential or network-topology secret (never present in state to begin with, per LLM-3 Section 7) and any content flagged as a prompt-injection anomaly (Section 3c).

**Success vs Failure Representation:**

**Success Indicators:** Green checkmark chip; "Resolved in 4.2s" text.

**Failure Indicators:** Red warning icon; plain-language failure reason; automatic escalation path stated.

**Partial Success:** "Logs available, trace data unavailable — diagnosis based on partial evidence" shown directly on the Evidence card rather than presented as a full-confidence result.

**Latency & Waiting States:**

**Short Operations (<2 seconds):** Subtle per-tool spinner only.

**Medium Operations (2–10 seconds):** Named status text ("Querying Tempo for render-07...").

**Long Operations (>10 seconds):** Elapsed-time counter added to the status text; no separate progress bar since exact completion time isn't predictable for a Sift investigation.

**Stuck/Timeout:** After the third retry fails, the chip turns red with "Unavailable — see evidence card" rather than spinning indefinitely.

**Heartbeat/Liveness Indicators:**
- **Mechanism:** A small pulse animation on the session header while `RUN_STARTED` is active and no `RUN_FINISHED`/`RUN_ERROR` has arrived.
- **Purpose:** Reassures the supervisor the console is still connected during quiet monitoring periods with no active drift event.

---

## **4a. GENERATIVE UI & RICH TOOL OUTPUT RENDERING**

### **EvidenceBundleExtraction**

**Output Shape (from LLM-3):** `event_id`, `logs_available`, `log_summary`, `trace_summary`, `anomaly`.

**Rendering Component:** Expandable "Evidence" card with two labeled text panels (Logs, Trace) and a conditional amber anomaly banner.

**Why This Component:** The two evidence sources are conceptually distinct and the supervisor may want to check one without reading the other — a single flat text blob would bury the anomaly flag.

**Interactivity:** Expand/collapse each panel independently; copy button on each panel's text.

**Streaming Behavior:** Renders only once the full structured output resolves — per LLM-3, this node's output mode is Structured Output, not a streamed tool result, so there is no meaningful partial state to show.

**Fallback:** If `EvidenceBundleExtraction` fails schema validation (LLM-3 Section 9), the card shows "Evidence unavailable — see error log" rather than rendering blank or malformed fields.

### **RootCauseDiagnosis**

**Output Shape (from LLM-3):** `event_id`, `category`, `confidence`, `rationale`.

**Rendering Component:** A colored diagnosis badge (category name) paired with a horizontal confidence meter (0–1 scale) and a "view reasoning" link.

**Why This Component:** A confidence score is inherently a magnitude — a meter communicates "how sure" at a glance far better than a bare decimal in text.

**Interactivity:** Clicking the badge expands the native-reasoning panel (Section 3a); hovering the meter shows the exact numeric confidence.

**Streaming Behavior:** The badge and meter render only once the structured output completes; the reasoning panel behind it streams live via `REASONING_MESSAGE_CONTENT` if already expanded.

**Fallback:** If `category` fails to validate against the four allowed literals, the badge renders as "Diagnosis error" in red rather than an empty or guessed category.

### **HITLCardPackage**

**Output Shape (from LLM-3):** `event_id`, `escalation_reason`, `proposed_action`, `cost_delta_estimate`, `visual_impact_score`, `root_cause_summary`.

**Rendering Component:** The full-width modal Approval Card (Section 5) — an interactive card, not a table or chart, since this is a single structured decision object requiring one binary human response.

**Why This Component:** The five fields form one coherent decision, not a list or comparison — a modal card keeps them together and keeps the decision impossible to miss or accidentally skip past.

**Interactivity:** Approve / Deny buttons only (see Section 5 on why no inline editing is offered); root-cause summary text is expandable to the full evidence and reasoning behind it.

**Streaming Behavior:** Renders as soon as the structured output completes and `RUN_PAUSED` fires; nothing about this card streams incrementally, since a partially-rendered approval decision would be actively dangerous to show.

**Fallback:** If the card is missing `cost_delta_estimate` or `visual_impact_score` (LLM-3 explicitly forbids writing such a card to state), the console never receives a `STATE_DELTA` for it at all — the failure surfaces as a `RUN_ERROR`/failure banner instead of a malformed card.

### **RemediationAction (remediation_log entries)**

**Output Shape (from LLM-2/LLM-3):** Append-only log entries recording action_taken, event_id, timestamp, success.

**Rendering Component:** Timeline list entries with a status icon and an expandable link to the diagnosis/evidence that justified the action.

**Why This Component:** This is inherently a chronological append-only record — a timeline list is the direct, honest representation of an append-only reducer, not a table that implies random access or reordering.

**Interactivity:** Click to jump to the originating diagnosis/evidence card.

**Streaming Behavior:** Each entry appears the moment its `STATE_DELTA` (append to `remediation_log`) arrives.

**Fallback:** N/A — this is an append-only log; there is no malformed-empty state to guard against beyond the general `RUN_ERROR` path.

### **Sync-offset telemetry (Prometheus, via Stream Watch)**

**Output Shape:** Time-series sync-offset value per node, with the configured threshold line.

**Rendering Component:** A live line chart, one series per active cluster node, with a horizontal threshold reference line — this is the component that directly visualizes the hackathon's "real-time telemetry spike" moment.

**Why This Component:** A trend over a threshold is the canonical case for a line chart — a table of raw numbers would not let the supervisor see the spike shape at a glance.

**Interactivity:** Hover for exact value/timestamp; a breach point is marked with a distinct marker linking to that event's timeline cluster.

**Streaming Behavior:** Appends new points continuously as Stream Watch's metric samples arrive — this is the one component that updates outside the `STEP_STARTED`/`STEP_FINISHED` cadence, since Stream Watch is a non-LLM, always-on node.

**Fallback:** If the Prometheus source is unavailable, the chart shows a "telemetry unavailable" placeholder rather than a flat or frozen line that could be mistaken for a genuinely stable signal.

---

## **5. HUMAN-IN-THE-LOOP INTERACTIVE GRAPH RESUMPTION**

**Approval Gates (from LLM-3 / LLM-2):**
Exactly one checkpoint exists in this system's graph — the HITL Pause node (LLM-3 Section 4, Step 6) — reached via four possible escalation reasons (`ambiguous_diagnosis`, `take_halt_required`, `capture_fallback_required`, `threshold_exceeded`). This is one gate with four variants, not four separate gates, matching LLM-2/LLM-3's single-node design.

### **Checkpoint: HITL Pause**

**Trigger:** The Root-Cause Correlation node returns `category: "ambiguous"`, or the HITL Card Generation node determines the diagnosed remediation is a take halt, capture-mode fallback, or threshold-exceeding failover.

**Paused-State Rendering:**
- **Streaming Event:** `RUN_PAUSED` (reason: `hitl_approval_required`), immediately preceded by the `STATE_DELTA` writing `pending_hitl_card`.
- **UI Presentation:** A full-width, non-dismissible modal overlay — given the profile's Zero Error risk tolerance and per-minute stage-burn cost, this must be impossible to miss or accidentally dismiss.
- **Information Shown:** `escalation_reason` (as a labeled badge), `proposed_action`, `cost_delta_estimate`, `visual_impact_score`, and `root_cause_summary` — every field of `HITLCardPackage`, with none omitted, and an expandable link to the full evidence/reasoning behind it.
- **Editable Fields:** None. LLM-3's schemas for the three HITL-gated tools (`halt_live_take`, `fallback_to_greenscreen`, `execute_threshold_exceeding_failover`) accept only `event_id`, `approval_state`, and `hitl_card_id` — none of which is meaningful for a supervisor to hand-edit. Offering an "edit" affordance here would imply a control the cognitive spec does not support, so this checkpoint is strictly Approve/Deny.

**Resumption Payload Contract:**

**On Approve:**
```json
{
  "action": "approve",
  "checkpoint_id": "hitl_pause::<event_id>",
  "modified_inputs": null
}
```

**On Approve with Edits:**
Not applicable at this checkpoint — no editable fields exist (see above). This payload shape is omitted rather than offered with a permanently-null body, so the frontend contract does not imply a capability that doesn't exist.

**On Deny:**
```json
{
  "action": "deny",
  "checkpoint_id": "hitl_pause::<event_id>",
  "reason": "optional supervisor-supplied text"
}
```

**Backend Resumption Behavior:**
- **On Approve:** ADK resumes the paused graph from the HITL Pause node using its checkpointed session state (Cloud SQL for PostgreSQL, per LLM-2 Section 7); `approval_state` is written as `"approved"` (last-write-wins), and the graph proceeds to Post-Approval Handling, which invokes the specific HITL-gated tool named in `proposed_action`.
- **On Approve with Edits:** N/A at this checkpoint.
- **On Deny:** `approval_state` is written as `"denied"`; Post-Approval Handling takes no action-tool call, appends the denial to `error_logs`/`remediation_log` as appropriate, and `session_status` returns to `monitoring` for that event.

**Timeout Behavior:** No timeout exists, per LLM-1/LLM-3's explicit rule that supervisor non-response never converts into a default action. The console instead escalates the modal's visual urgency the longer it remains open (e.g., the overlay's border color shifts from amber to red after a configurable interval) and re-announces it via the `aria-live="assertive"` region at each subsequent telemetry sample interval, matching LLM-3's "re-flag at each sample interval" behavior — but the graph itself simply remains paused indefinitely.

---

## **6. ACTIVITY, AUDIT LOGS & TELEMETRY/TRACING**

**Telemetry Standard Verification Note:** Verified via live research (September 2026): the OpenTelemetry GenAI Semantic Conventions reached a stable v1.41 release in 2026, with defined span shapes for model inference, tool execution, and agent/workflow invocation, plus `gen_ai.*` attributes for provider, model, and token usage, and event definitions for prompt/completion capture — this is the current, vendor-neutral standard. Separately, Langfuse (acquired by ClickHouse, January 2026) now operates purely as an OTLP-compatible backend: spans carrying `gen_ai.*` attributes are automatically rendered as "generations" with model/token/cost data, with everything else nested as regular observations.

**Chosen Tracing Backend:** Hybrid — instrument with OpenTelemetry GenAI Semantic Conventions throughout, exported to two destinations: Google Cloud Trace (native to the mandated Google Cloud Agent Builder / Gemini Enterprise Agent Platform deployment) for operational tracing, and Langfuse via its OTLP endpoint for scoring and evaluation-dataset construction (Section 7a). Instrumenting to the open standard rather than a vendor SDK means the backend choice can change without re-instrumenting the agent.

**Trace/Span Model:**
- **Trace:** One trace per shoot session (`session_id`), consistent with LLM-2's Long-running lifecycle.
- **Span Hierarchy:** Session trace → per-drift-event `invoke_agent` span (event_id) → per-node span (`step_name`, using OTel's workflow/tool-invocation span shapes) → per-tool-call span nested under Evidence Triage or a dispatch node.
- **Span Attributes Captured:** `gen_ai.provider.name` (`google`), `gen_ai.request.model`/`gen_ai.response.model` (`gemini-3.1-pro` or `gemini-3.7-flash`, per node), `gen_ai.operation.name` (`invoke_agent` / tool-call operation names), `gen_ai.tool.name`, `gen_ai.tool.status`, `usage.input_tokens`/`usage.output_tokens`, span latency, and — for cost — the token counts joined against current per-model pricing at export time rather than hardcoded into the span.

**Event Types Logged:**

### **Logged Events:**

**User Actions:**
- Session start/stop
- Approve/Deny decisions, including the `checkpoint_id` and any supervisor-supplied deny reason

**Agent Reasoning:**
- Native thinking-token spans for the Root-Cause Correlation node (per `gen_ai.*` prompt/completion event conventions, content-capture enabled since this is an internal operational tool, not end-user chat)
- Graph-trace step spans for all seven nodes

**Agent Actions:**
- All nine tool calls (three MCP query tools, three reversible remediations, three HITL-gated actions), with input/output captured per span, and latency/token/cost attributes on the two Gemini-backed calls
- Every `STATE_DELTA` write, tagged with the field name and reducer type

**System Events:**
- All error/failure conditions (Section 9 of LLM-3)
- Model Armor content-block events, if any
- The circuit-breaker firing (repeated re-breach forcing HITL)

**User-Visible vs Internal Logs:**

**User-Visible Activity Log:**
- **Purpose:** Give the supervisor a scannable record of the session.
- **Contents:** One row per drift event with its final diagnosis, action, and resolution status; approval decisions.
- **Format:** Reverse-chronological timeline list with timestamps.
- **Access:** Always visible in the console's main panel.

**Internal Debug/Trace Logs:**
- **Purpose:** Post-incident engineering review, hackathon demo trace, and evaluation dataset construction.
- **Contents:** Full OTel spans — raw tool inputs/outputs, full native-reasoning text, token/cost/latency per call.
- **Format:** Structured trace export, viewable directly in Cloud Trace's or Langfuse's own trace UI, or exported as JSON.
- **Access:** A "Debug" toggle in the console header, intended for engineering/production staff rather than the on-set supervisor during a live take.

**Timestamping & Trace Structure:**

**Timestamp Format:** Absolute time in the console (shoot days run on a wall-clock schedule); relative time ("4s ago") only in the compact timeline summary rows.

**Trace Linking:** W3C Trace Context propagation across the session → event → node → tool-call span hierarchy, per the verified OTel GenAI conventions' support for distributed trace propagation across agent orchestrators and tool calls.

**Session Boundaries:** One trace per shoot session; a new trace begins at each `RUN_STARTED`.

**Debug vs Normal User Modes:**

**Normal User Mode:**
- Shows: Timeline summaries, diagnosis badges, evidence cards, approval cards, remediation log.
- Hides: Raw tool arguments, full OTel span tree, raw prompts.
- Purpose: The supervisor needs to trust and act, not audit instrumentation, during a live take.

**Debug Mode:**
- Shows: Full span tree, raw tool call arguments and results, full native-reasoning transcripts, per-call token/cost/latency.
- Access: Debug toggle in the console header.
- Purpose: Engineering troubleshooting, hackathon demo narration, and evaluation review.

**Log/Trace Retention & Export:**

**Retention:** Per shoot session for the console's own activity log; trace retention in Cloud Trace/Langfuse follows those backends' own configured retention, which is an operational decision outside this system's cognitive/behavioral scope.

**Export:** JSON export of the session's activity log from the console; full trace export/linking directly into the Cloud Trace or Langfuse UI from the debug panel.

---

## **7. USER FEEDBACK & CONTROL LOOP**

**Interrupt Mechanisms:**

**How User Interrupts Agent:**
- **Stop Button:** A persistent "Stop Session" control in the console header — the only interrupt this system defines, matching LLM-3's single documented user-interrupt condition.
- **Pause Button:** Not offered as a separate control — the HITL Pause already occurs automatically at the four defined triggers; there is no cognitive-spec-backed "pause on demand" capability to expose.
- **Text Commands:** Not applicable — no free-text input surface exists.

**What Happens on Interrupt:**
1. Any pending automatic action is suspended immediately (per LLM-1/LLM-2 Section 10's stop condition).
2. Session state is checkpointed as-is (Cloud SQL for PostgreSQL) — no queued action is retroactively executed.
3. The console shows "Session stopped by supervisor" and freezes the timeline in its final state.

**Correction Mechanisms:**

**How User Corrects Agent:** Not applicable in the conventional sense — there is no conversational output for the supervisor to correct. The nearest equivalent is Deny on a HITL card, which is a rejection of a proposed action, not a correction of agent output.

**Undo/Redo:** Not offered — the three reversible autonomous actions are reversible at the infrastructure level (per their names), but this console does not expose an "undo" button, since no tool in LLM-3's inventory performs the inverse of a dispatched action; reversal, if needed, is itself a new supervisor-initiated HITL-gated request outside this system's current tool set.

**Approval / Rejection Mechanisms:** See Section 5 for the full resumption contract.
- **Approval Options:** Approve / Deny only — no "Modify" or "Ask for more info" option exists, since LLM-3 defines no editable fields or clarification-request tool at this checkpoint.
- **Timeout:** None — see Section 5.

**Regeneration vs Continuation:**

**Regeneration:** Not applicable — there is no single-turn "response" to regenerate; a denied HITL action simply returns the event to `monitoring`, and a fresh diagnostic cycle only begins on a new threshold breach.

**Continuation:**
- **Trigger:** Supervisor wants the session to keep running after acknowledging a failure banner.
- **Mechanism:** "Acknowledge" button on the failure banner (Section 2's System Messages).
- **Behavior:** The banner dismisses; monitoring continues uninterrupted, since a permanent failure on one event does not halt the whole session unless it is session-fatal.

**Confidence Signals Shown to User:**

**Agent Confidence Indicators:**
- **When Shown:** On every `RootCauseDiagnosis`.
- **How Shown:** The confidence meter (Section 4a) plus the category badge — `ambiguous` is its own distinct badge color, never presented as "low-confidence network_jitter" or similar.
- **Examples:**
  - High confidence: Green badge, meter near full, no qualifier text needed.
  - Medium/borderline confidence: Amber badge if it still cleared the confidence floor, meter partially filled.
  - Low/ambiguous: Red "Ambiguous" badge, routed straight to the approval card rather than shown as a routine diagnosis.

**User Trust Signals & Feedback Capture:**
- **Thumbs up/down:** Offered post-hoc on a resolved event's diagnosis ("Was this diagnosis correct?"), since this is an operational agent, not a conversational one — the natural feedback moment is confirming diagnostic accuracy after the fact, not rating a chat response.
- **Rating:** Not used — a binary correct/incorrect signal is more actionable for this domain than a star scale.
- **Detailed Feedback:** An optional free-text field appears if the supervisor marks a diagnosis incorrect, to capture what the actual root cause turned out to be.

---

## **7a. FEEDBACK-TO-TELEMETRY ANNOTATION PIPELINE**

**Purpose:** Route supervisor feedback into the tracing backend chosen in Section 6 as structured, queryable annotations, for building an evaluation dataset that can check whether the Root-Cause Correlation node's diagnoses hold up against ground truth.

**Feedback Signal → Annotation Mapping:**

| User Feedback Action | Captured At (Trace/Span) | Annotation Written | Backend Field (per verified schema) |
|---|---|---|---|
| Diagnosis correct/incorrect (post-hoc thumbs) | The `invoke_agent` span for that event's Root-Cause Correlation node | Binary score | Langfuse `score` object, `name: "diagnosis_accuracy"`, `value: 1/0`, linked via `session.id`/`user.id` span attributes per verified OTel→Langfuse mapping |
| Free-text correction (actual root cause, if marked incorrect) | Same span | Comment/annotation | Stored as a linked observation/comment on the span, alongside the original `RootCauseDiagnosis.category` for direct before/after comparison |
| Approve/Deny on a HITL card | The HITL Pause span | Categorical annotation | Span attribute (`hitl.decision: approved / denied`) plus a Langfuse score, `name: "hitl_decision"` |
| Deny reason (free text) | Same span | Comment/annotation | Span comment field |

**Write Timing:** Immediately on supervisor action — there is no batching, since each of these signals is infrequent (at most one per drift event) and low-volume enough to write synchronously.

**Dataset Use:** The `diagnosis_accuracy` scores, joined against each span's evidence and reasoning, form the evaluation set for checking the Root-Cause Correlation node's real-world accuracy per category over a shoot day or across shoot days — this is stated here only as what the annotation pipeline enables, not as an implementation of the evaluation itself.

---

## **8. AUTONOMY & SAFETY CONTROLS**

**Autonomy Level Indicators:**

**Current Autonomy Display:**
- **Location:** A fixed badge in the console header.
- **Format:** Text label — "Semi-Autonomous" — since this is the one, unchanging autonomy level LLM-1/LLM-2 defined; there is no need for an icon-based mode indicator when only one mode exists.
- **Clarity:** A hover tooltip states plainly: "3 reversible actions run automatically on a confident diagnosis; take-halt, capture fallback, and threshold-exceeding failover always require your approval."

**Autonomy Level Settings:**

**Semi-Autonomous (fixed):**
- **Default State:** Semi-Autonomous, and the only available state.
- **User Control:** None — per LLM-1/LLM-2, autonomy level is not a runtime-adjustable setting; offering a toggle here would imply a Manual or Fully Autonomous mode that does not exist in the cognitive spec.
- **Change Mechanism:** N/A.

**Mode Switching:** Not applicable — there is nothing to switch.

**Manual Override Mechanisms:**

**Override Controls:**
- **Stop:** Always available (Section 7).
- **Pause:** Not offered as a distinct control (see Section 7).
- **Takeover:** Not offered — this console has no manual-dispatch control that lets a supervisor directly fire `failover_cluster_leadership` or any other tool outside the agent's own decision flow, since LLM-3 defines no such supervisor-initiated tool.

**Override Availability:** The Stop control is available at all times, including while a HITL card is open.

**Human-in-the-Loop Trigger Visualization:** See Section 5.

**Visual Indicators:**
- **Pending Approval:** The modal overlay itself, plus a red pulsing dot on the affected node's status chip in the sidebar.
- **Timeout Warning:** No countdown, per Section 5 — instead, an escalating border-color shift the longer the card remains open.

**Escalation States:**

**When Agent Escalates to Human:** The four HITL triggers (Section 5) and any permanent failure (Section 9 of LLM-3).

**Escalation UI:**
- **Indicator:** The approval-card modal for HITL triggers; the red System Message banner for failures.
- **Explanation:** Full `HITLCardPackage` content for approvals; plain-language failure reason plus what was attempted for failures.
- **User Options:** Approve/Deny for HITL; Acknowledge for failures (Section 7).

**Failure or Escalation States:**

**Agent Failure Display:**
- **Type:** Tool failure (transient, retried silently), permanent failure (telemetry exhausted, injection block), safety-relevant failure (a failed HITL-approved action).
- **Message:** Plain-language, naming what was attempted and why it stopped, per LLM-3's own failure-message content.
- **Recovery Options:** Acknowledge and continue monitoring (non-fatal); for a failed HITL-approved safety action, the banner explicitly states manual intervention is required, since no automated retry path exists for that case.

**Safety Guardrail Activations:**

**When Guardrail Triggers:** Model Armor blocking a suspected prompt-injection tool response; a remediation tool call rejected because its diagnosis-category precondition wasn't met (should be structurally unreachable, but surfaced if it somehow occurs).

**User Communication:**
- **Visible:** Yes, always — per LLM-3's transparency requirements, a blocked or rejected action is never silently absorbed.
- **Message:** "Evidence for render-07 was flagged as a potential injection attempt and excluded from diagnosis" (named plainly, without printing the flagged content itself, per Section 3c).
- **Transparency:** The specific constraint is named in plain language; the underlying detection mechanics are not exposed (consistent with not teaching evasion of the safety layer).

---

## **9. ERROR & UNCERTAINTY UX**

**Uncertainty Communication Patterns:**

**Low Confidence / Ambiguous:**
- **Indicator:** Red "Ambiguous" badge, routed to the approval card rather than shown as a routine diagnosis.
- **Language:** "The available evidence did not confidently point to a single known cause."
- **User Guidance:** The approval card frames this explicitly as a decision point, not a suggestion to double-check the agent's work.

**Medium/Borderline Confidence:**
- **Indicator:** Amber badge (diagnosis cleared the confidence floor but not by a wide margin).
- **Language:** The `rationale` field states the evidence weighed, in the model's own words, per LLM-3's citation-enforcement rule.

**High Confidence:**
- **Indicator:** Green badge, meter near full.
- **Language:** Direct statement of the diagnosed category with no hedging.

**Ambiguity:**
- **When User Request is Ambiguous:** Not applicable — the supervisor issues no free-text requests for the agent to interpret.
- **When Tool Output is Ambiguous:** Conflicting evidence across sources is surfaced explicitly in the Evidence card (per LLM-3 Section 8's cross-examination rule) rather than silently resolved — e.g., "Log evidence suggests thermal throttle; trace evidence suggests network jitter" shown side-by-side.

**Failure Explanation Approach:**

**What Agent Admits:** Every tool failure, every ambiguous diagnosis, every data gap (`logs_available: false`), stated plainly.

**What Agent Explains:**
- **Why failure occurred:** The specific tool/source and failure mode (timeout, block, retry exhaustion).
- **What was attempted:** The retry count and sources queried.
- **What user can do:** Acknowledge and continue (non-fatal) or intervene manually (safety-relevant failures).

### **Tool-Specific Failure Mapping Table:**

| Critical Tool | Failure Scenario | User Error Message | Recovery Action (UI) |
|---|---|---|---|
| `query_loki_logs` | Timeout after 3 retries | "Loki logs unavailable for render-07" | None — evidence card shows `logs_available: false`, diagnosis proceeds on remaining evidence |
| `find_slow_requests` | Sift investigation timeout | "Tempo slow-request check unavailable for render-07" | None — evidence card notes the gap |
| `get_trace_by_id` | Trace not found for frame_id | "No trace found for f-88213" | None — evidence card notes the gap |
| Any reversible remediation tool | Dispatch failure | "Failover attempt on render-07 failed — escalating to supervisor" | Approval card opens automatically |
| Any HITL-gated tool | Post-approval execution failure | "Approved action failed to execute — manual intervention required" | Red failure banner, Acknowledge only (no automated retry) |
| Any of the three query tools | Model Armor blocks response content | "Evidence for render-07 flagged as a potential injection attempt and excluded" | None — event proceeds with that source excluded; if this leaves insufficient evidence, diagnosis routes to ambiguous |

**Failure Types:**

### **Tool Failure**
- **Message:** "The Loki query for render-07 failed after 3 attempts. Diagnosis will proceed on the remaining evidence."
- **User Options:** None required — this is absorbed into the diagnostic cycle automatically; the supervisor only sees the resulting evidence-gap note.

### **Reasoning Failure**
Not applicable in this system's terms — the Root-Cause Correlation node cannot "fail to find a logical path"; its only two outcomes are a categorized diagnosis or an explicit `ambiguous` verdict, both of which are valid, expected structured outputs, not failures.

### **Safety Violation Attempt**
- **Message:** "This action requires your approval and cannot be taken automatically" (shown only in the hypothetical case a downstream engineer probes a HITL-gated tool directly — under normal console operation, the supervisor never sees an attempted violation, since it is structurally unreachable).
- **User Options:** N/A under normal operation.

**Transparency vs Reassurance Balance:**

**Full Transparency When:** Any evidence gap, ambiguous diagnosis, or failure — always named plainly.

**Reassurance When:** A single-source evidence gap that did not prevent a confident diagnosis — the console notes the gap but does not alarm over it, since the diagnosis still cleared the confidence floor on the remaining evidence.

**Balance Strategy:** Every gap and failure is disclosed; the console's tone (badge color, banner urgency) scales with actual consequence, not with the mere fact that something didn't go perfectly.

**Trust Preservation Rules:**

**Never:** Show a diagnosis badge without its real confidence score; auto-dismiss a HITL card; silently drop a failed tool call without noting the gap.

**Always:** Show `logs_available`/evidence-gap flags plainly; name the specific failure reason; keep the Stop control available even mid-approval-card.

**Trust-Building Patterns:**
1. The confidence meter is always present, never omitted for a "confident-looking" diagnosis.
2. A denied HITL action is logged exactly as prominently as an approved one — the audit trail never favors one outcome.
3. The step tracker and evidence trail are available for every single event, not just the ones that went wrong.

---

## **10. EXPLICIT UI NON-GOALS**

**What the Interface Will NOT Show:**

1. **Raw LogQL/TraceQL query strings and raw tool-call argument JSON, by default**
   - **Reason:** Not decision-relevant to the supervisor in the moment; available in debug mode for engineering review.

2. **The Model Armor detection mechanics (what specifically triggered a content block)**
   - **Reason:** Naming the detection mechanics would teach how to evade them, consistent with not narrating safety-boundary internals.

3. **ADK session/checkpoint internals (e.g., Cloud SQL row structure, checkpoint cadence mechanics)**
   - **Reason:** Purely an implementation detail of durability, irrelevant to whether the supervisor should trust or act on a diagnosis.

**What Will NOT Be Exposed to Users:**

**Internal System Details:**
- Exact Gemini API call parameters and prompt-cache hit/miss status
- ADK graph internals beyond the seven named node steps already shown
- Reason: Not relevant to the supervisor's decision-making; available only in the debug/trace backend for engineering.

**Sensitive System Information:**
- Any cluster credential, network-topology secret, or Grafana service-account token
- The exact anomaly-detection heuristic used to flag suspected prompt injection
- Reason: Security — both because these should never be in state to begin with (LLM-3 Section 7) and because naming detection mechanics undermines them.

**What Is Intentionally Abstracted:**

**Technical Implementation:**
- The three MCP query tools are shown to the supervisor simply as "gathering evidence," not as three separately-named API calls, in the default (non-debug) view.
- Why abstracted: The supervisor cares that evidence was gathered and from where (Logs/Trace, per the Evidence card's two panels), not which specific MCP server or RPC handled it.

**System Complexity:**
- The seven-node graph collapses to a simple linear narrative in the default summarized view ("detected → diagnosed → resolved" or "detected → diagnosed → escalated → approved/denied → resolved").
- Why abstracted: The supervisor needs the causal story, not the orchestration engine's internal step count, unless they expand the full step tracker.

**Abstraction Strategy:** Collapse implementation detail into plain operational language by default (data sources, actions, decisions), while keeping every collapsed layer one click away from its full, unaltered underlying record — nothing is abstracted away permanently, only by default.

---

## **INTERFACE SYSTEM INTEGRITY DECLARATION**

This interface specification is AUTHORITATIVE.

All downstream systems must:
- Implement interaction model exactly as specified
- Stream responses per the defined typed event data contract
- Show reasoning visibility per specified rules, distinguishing native thinking tokens from graph traces
- Display tool actions and structured outputs with the defined observability and generative UI components
- Implement the exact HITL graph-resumption payload contract for every approval gate
- Capture telemetry per the verified tracing standard chosen in Section 6
- Wire user feedback into the telemetry annotation pipeline exactly as specified
- Provide activity logs as specified
- Enable user feedback and control mechanisms
- Surface autonomy and safety controls
- Communicate errors and uncertainty honestly
- Respect all explicit non-goals

The interface must faithfully reflect agent cognitive reality.
No simplification may hide what agent actually does.
No embellishment may fake capabilities agent doesn't have.
No streaming event or trace may be invented that doesn't correspond to a real step in LLM-3's cognitive design.

Trust is built through transparency, honesty, and control.

---
