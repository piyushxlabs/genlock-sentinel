/**
 * Frontend Component & State Delta Verification Suite.
 *
 * Verifies that:
 * 1. All 7 Generative UI components export properly.
 * 2. applyStateDelta processes append-only, merge-by-key, and last-write-wins patches.
 * 3. AGUIStreamingClient handles event dispatching.
 */

import {
  applyStateDelta,
  GenlockState,
  StateDeltaOp,
  AGUIStreamingClient,
} from "../src/stream/agui-client";

// Import all 7 components to verify type-checking and export contract
import { SyncOffsetChart } from "../src/components/SyncOffsetChart";
import { StepTracker } from "../src/components/StepTracker";
import { EvidenceCard } from "../src/components/EvidenceCard";
import { DiagnosisBadge } from "../src/components/DiagnosisBadge";
import { ApprovalCardModal } from "../src/components/ApprovalCardModal";
import { RemediationLog } from "../src/components/RemediationLog";
import { FailureBanner } from "../src/components/FailureBanner";

function assert(condition: boolean, msg: string) {
  if (!condition) {
    throw new Error(`Assertion failed: ${msg}`);
  }
}

console.log("--- Verifying Frontend Generative UI Components & Client ---");

// 1. Verify Components Export
assert(typeof SyncOffsetChart === "function", "SyncOffsetChart is a valid component");
assert(typeof StepTracker === "function", "StepTracker is a valid component");
assert(typeof EvidenceCard === "function", "EvidenceCard is a valid component");
assert(typeof DiagnosisBadge === "function", "DiagnosisBadge is a valid component");
assert(typeof ApprovalCardModal === "function", "ApprovalCardModal is a valid component");
assert(typeof RemediationLog === "function", "RemediationLog is a valid component");
assert(typeof FailureBanner === "function", "FailureBanner is a valid component");
console.log("✅ All 7 Generative UI components verified.");

// 2. Verify RFC 6902 Reducer Projections in Client
const initialState: GenlockState = {
  session_id: "test-sess",
  session_status: "monitoring",
  approval_state: null,
  active_drift_events: {},
  evidence_bundle: {},
  diagnosis_history: [],
  pending_hitl_card: null,
  remediation_log: [],
  error_logs: [],
};

// 2a. Test last-write-wins replacement
const replaceOps: StateDeltaOp[] = [
  { op: "replace", path: "/session_status", value: "awaiting_approval" },
  { op: "replace", path: "/approval_state", value: "pending" },
];
const s1 = applyStateDelta(initialState, replaceOps);
assert(s1.session_status === "awaiting_approval", "last-write-wins replaced session_status");
assert(s1.approval_state === "pending", "last-write-wins replaced approval_state");
console.log("✅ last-write-wins reducer verified.");

// 2b. Test append-only array addition
const appendOps: StateDeltaOp[] = [
  {
    op: "add",
    path: "/remediation_log/-",
    value: {
      action_id: "act-01",
      event_id: "evt-01",
      node_id: "render-07",
      action_taken: "failover_cluster_leadership",
      timestamp: "2026-09-09T00:00:00Z",
      success: true,
    },
  },
];
const s2 = applyStateDelta(s1, appendOps);
assert(s2.remediation_log.length === 1, "append-only added action to remediation_log");
assert(s2.remediation_log[0].action_taken === "failover_cluster_leadership", "action_taken matches");
console.log("✅ append-only reducer verified.");

// 2c. Test merge-by-key dictionary addition
const mergeOps: StateDeltaOp[] = [
  {
    op: "add",
    path: "/active_drift_events/evt-01",
    value: {
      event_id: "evt-01",
      node_id: "render-07",
      timestamp: "2026-09-09T00:00:00Z",
      sync_offset_us: 182.4,
      severity: "critical",
      status: "detected",
    },
  },
  {
    op: "add",
    path: "/evidence_bundle/evt-01",
    value: {
      event_id: "evt-01",
      logs_available: true,
      log_summary: "Loki frame drop logs",
      trace_summary: "Tempo jitter span",
      anomaly: null,
    },
  },
];
const s3 = applyStateDelta(s2, mergeOps);
assert(s3.active_drift_events["evt-01"]?.sync_offset_us === 182.4, "merge-by-key merged active_drift_events");
assert(s3.evidence_bundle["evt-01"]?.logs_available === true, "merge-by-key merged evidence_bundle");
console.log("✅ merge-by-key reducer verified.");

// 3. Verify AGUIStreamingClient event handling
const client = new AGUIStreamingClient("test-sess");
let stateNotified = false;
client.onStateChange((st) => {
  if (st.session_id === "test-sess") stateNotified = true;
});
assert(stateNotified, "AGUIStreamingClient immediately notifies initial state");

let telemetryNotified = false;
client.onTelemetry((sample) => {
  if (sample.sync_offset_us === 140.0) telemetryNotified = true;
});
client.handleEvent({
  type: "SYNC_OFFSET_SAMPLE",
  node_id: "render-07",
  sync_offset_us: 140.0,
  threshold_us: 150.0,
  timestamp: "2026-09-09T00:00:00Z",
});
assert(telemetryNotified, "AGUIStreamingClient dispatches telemetry sample");

console.log("✅ AGUIStreamingClient dispatching verified.");
console.log("🎉 ALL FRONTEND VERIFICATION CHECKS PASSED SUCCESSFULLY!");
