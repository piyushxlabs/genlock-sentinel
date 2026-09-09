import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Film,
  Flame,
} from "lucide-react";
import {
  AGUIStreamingClient,
  GenlockState,
  StepEvent,
  SyncOffsetSample,
} from "./stream/agui-client";
import { SyncOffsetChart } from "./components/SyncOffsetChart";
import { StepTracker } from "./components/StepTracker";
import { EvidenceCard } from "./components/EvidenceCard";
import { DiagnosisBadge } from "./components/DiagnosisBadge";
import { ApprovalCardModal } from "./components/ApprovalCardModal";
import { RemediationLog } from "./components/RemediationLog";
import { FailureBanner } from "./components/FailureBanner";

const DEFAULT_SESSION_ID = "sentinel-icvfx-stage-01";
const STAGE_BURN_RATE_PER_MIN = 1800; // $1,800/min stage burn ($108,000/hr)

export const App: React.FC = () => {
  const [sessionId] = useState(DEFAULT_SESSION_ID);
  const [state, setState] = useState<GenlockState>({
    session_id: DEFAULT_SESSION_ID,
    session_status: "monitoring",
    approval_state: null,
    active_drift_events: {},
    evidence_bundle: {},
    diagnosis_history: [],
    pending_hitl_card: null,
    remediation_log: [],
    error_logs: [],
  });

  const [telemetrySamples, setTelemetrySamples] = useState<SyncOffsetSample[]>([]);
  const [currentStep, setCurrentStep] = useState<StepEvent["step_name"] | null>("stream_watch");
  const [historySteps, setHistorySteps] = useState<string[]>(["stream_watch"]);
  const [streamingReasoning, setStreamingReasoning] = useState<string>("");
  const [activeError, setActiveError] = useState<{ message: string; code: string } | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [haltingSession, setHaltingSession] = useState<boolean>(false);

  // Initialize SSE streaming connection
  useEffect(() => {
    const client = new AGUIStreamingClient(sessionId);

    client.onStateChange((newState) => {
      setState(newState);
      if (newState.error_logs.length > 0) {
        const latestErr = newState.error_logs[newState.error_logs.length - 1];
        setActiveError({
          message: latestErr.message,
          code: latestErr.error_type,
        });
      }
    });

    client.onTelemetry((sample) => {
      setTelemetrySamples((prev) => [...prev.slice(-100), sample]);
      setConnected(true);
    });

    client.onStep((stepEvt) => {
      if (stepEvt.type === "STEP_STARTED") {
        setCurrentStep(stepEvt.step_name);
        setHistorySteps((prev) => [...new Set([...prev, stepEvt.step_name])]);
      } else if (stepEvt.type === "STEP_FINISHED") {
        setHistorySteps((prev) => [...new Set([...prev, stepEvt.step_name])]);
      }
    });

    client.onReasoning((token) => {
      setStreamingReasoning((prev) => prev + token);
    });

    client.onError((msg, code) => {
      setActiveError({ message: msg, code });
    });

    client.connect();
    setConnected(true);

    // Live session clock & stage burn ticker
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => {
      client.disconnect();
      clearInterval(timer);
    };
  }, [sessionId]);

  // Emergency Stop Handler
  const handleEmergencyStop = async () => {
    if (!confirm("Are you sure you want to execute an emergency stop? This halts all autonomous actions immediately.")) {
      return;
    }
    setHaltingSession(true);
    try {
      const res = await fetch(`/sessions/${sessionId}/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: "Supervisor manual emergency halt from console header.",
          supervisor_id: "on_set_lead",
        }),
      });
      if (res.ok) {
        setState((prev) => ({
          ...prev,
          session_status: "stopped",
          approval_state: "halted",
        }));
      }
    } catch (err) {
      console.error("Emergency stop failed:", err);
    } finally {
      setHaltingSession(false);
    }
  };

  // Resolve active drift event & evidence
  const latestDiagnosis =
    state.diagnosis_history.length > 0
      ? state.diagnosis_history[state.diagnosis_history.length - 1]
      : null;

  const activeEventId = latestDiagnosis?.event_id || Object.keys(state.active_drift_events)[0] || undefined;
  const activeEvidence = activeEventId ? state.evidence_bundle[activeEventId] : null;

  // Active route
  const activeRoute: "autonomous" | "hitl" | null =
    state.pending_hitl_card || state.session_status === "awaiting_approval"
      ? "hitl"
      : latestDiagnosis
      ? "autonomous"
      : null;

  // Stage burn cost calculation
  const stageBurnAccrued = Math.round((elapsedSeconds / 60) * STAGE_BURN_RATE_PER_MIN);

  return (
    <div className="console-container">
      {/* Top Header Bar */}
      <header className="console-header">
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "42px",
              height: "42px",
              background: "rgba(6, 182, 212, 0.15)",
              border: "1px solid rgba(6, 182, 212, 0.4)",
              borderRadius: "10px",
            }}
          >
            <Film size={22} color="var(--color-cyan)" />
          </div>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h1 style={{ fontSize: "1.25rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
                GENLOCK SENTINEL
              </h1>
              <span className="badge badge-info">
                v0.1.0 • ICVFX nDisplay SRE
              </span>
            </div>
            <div style={{ fontSize: "0.775rem", color: "var(--text-muted)", marginTop: "2px" }}>
              Session: <span className="mono" style={{ color: "var(--text-secondary)" }}>{sessionId}</span> • Mode: <span style={{ color: "var(--color-cyan)", fontWeight: 600 }}>Semi-Autonomous (Locked)</span>
            </div>
          </div>
        </div>

        {/* Status Metrics & Emergency Stop */}
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          {/* Connection Status */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: connected ? "var(--color-emerald)" : "var(--color-amber)",
              }}
              className={connected ? "" : "pulse-active"}
            />
            {connected ? "SSE Stream Connected" : "Connecting..."}
          </div>

          {/* Stage Burn Counter */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "rgba(245, 158, 11, 0.1)",
              border: "1px solid rgba(245, 158, 11, 0.3)",
              padding: "6px 14px",
              borderRadius: "8px",
            }}
          >
            <Flame size={16} color="var(--color-amber)" />
            <div>
              <div style={{ fontSize: "0.675rem", textTransform: "uppercase", color: "var(--color-amber)", fontWeight: 700 }}>
                Stage Burn Accrued
              </div>
              <div className="mono" style={{ fontSize: "0.95rem", fontWeight: 800, color: "var(--text-primary)" }}>
                ${stageBurnAccrued.toLocaleString()} USD
              </div>
            </div>
          </div>

          {/* Session Status Chip */}
          <span
            className={`badge ${
              state.session_status === "stopped"
                ? "badge-critical"
                : state.session_status === "awaiting_approval"
                ? "badge-warning pulse-active"
                : "badge-nominal"
            }`}
          >
            {state.session_status.toUpperCase()}
          </span>

          {/* Emergency Stop Button */}
          <button
            onClick={handleEmergencyStop}
            disabled={haltingSession || state.session_status === "stopped"}
            className="btn btn-emergency-stop"
          >
            <AlertTriangle size={15} />
            {state.session_status === "stopped" ? "Session Halted" : "Emergency Stop"}
          </button>
        </div>
      </header>

      {/* Persistent Error Banner */}
      <FailureBanner error={activeError} onDismiss={() => setActiveError(null)} />

      {/* 7-Node ADK Workflow Graph Tracker */}
      <div style={{ marginBottom: "24px" }}>
        <StepTracker
          currentStep={currentStep}
          historySteps={historySteps}
          route={activeRoute}
        />
      </div>

      {/* Main Console Split Layout */}
      <div className="console-grid console-grid-split">
        {/* Left Column: Observability & Diagnostics */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Prometheus Real-Time Sync-Offset Chart */}
          <SyncOffsetChart samples={telemetrySamples} thresholdUs={150.0} />

          {/* Root-Cause Diagnosis Badge & Reasoning Panel */}
          <DiagnosisBadge
            diagnosis={latestDiagnosis}
            streamingReasoning={streamingReasoning}
          />

          {/* Triaged Evidence Bundle (Loki & Tempo) */}
          <EvidenceCard evidence={activeEvidence} eventId={activeEventId} />
        </div>

        {/* Right Column: Remediation & Actuators */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Chronological Remediation Log */}
          <RemediationLog logs={state.remediation_log} />
        </div>
      </div>

      {/* HITL Modal Overlay for Supervisor Sign-off */}
      {state.pending_hitl_card && state.session_status === "awaiting_approval" && (
        <ApprovalCardModal
          card={state.pending_hitl_card}
          sessionId={sessionId}
          onDecisionSubmitted={() => {
            // Local state mutation will also be updated via SSE STATE_DELTA
            setState((prev) => ({
              ...prev,
              session_status: "monitoring",
            }));
          }}
        />
      )}
    </div>
  );
};
