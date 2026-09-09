import React, { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Film,
  Flame,
  Radio,
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
const STAGE_BURN_RATE_PER_MIN = 1800; // $1,800/min production loss

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
  const [elapsedMs, setElapsedMs] = useState<number>(0);
  const [haltingSession, setHaltingSession] = useState<boolean>(false);

  // High-res burn ticker (60fps ms counter)
  const msRef = useRef<number>(Date.now());
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const tick = () => {
      setElapsedMs(Date.now() - msRef.current);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current !== null) cancelAnimationFrame(rafRef.current); };
  }, []);

  // SSE connection
  useEffect(() => {
    const client = new AGUIStreamingClient(sessionId);

    client.onStateChange((newState) => {
      setState(newState);
      if (newState.error_logs.length > 0) {
        const latestErr = newState.error_logs[newState.error_logs.length - 1];
        setActiveError({ message: latestErr.message, code: latestErr.error_type });
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

    // 1-second session clock
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => {
      client.disconnect();
      clearInterval(timer);
    };
  }, [sessionId]);

  // Emergency Stop
  const handleEmergencyStop = async () => {
    if (!confirm("EMERGENCY STOP: This halts all autonomous actions immediately. Confirm?")) return;
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

  // Resolve state
  const latestDiagnosis =
    state.diagnosis_history.length > 0
      ? state.diagnosis_history[state.diagnosis_history.length - 1]
      : null;
  const activeEventId = latestDiagnosis?.event_id || Object.keys(state.active_drift_events)[0] || undefined;
  const activeEvidence = activeEventId ? state.evidence_bundle[activeEventId] : null;
  const activeRoute: "autonomous" | "hitl" | null =
    state.pending_hitl_card || state.session_status === "awaiting_approval"
      ? "hitl"
      : latestDiagnosis
      ? "autonomous"
      : null;

  // Stage burn cost — high precision
  const stageBurnUsd    = (elapsedMs / 60000) * STAGE_BURN_RATE_PER_MIN;
  const burnDollars     = Math.floor(stageBurnUsd);
  const burnCents       = Math.floor((stageBurnUsd - burnDollars) * 100);
  const burnMillis      = Math.floor(((stageBurnUsd - burnDollars) * 100 - burnCents) * 100);

  // Session clock format
  const hrs  = Math.floor(elapsedSeconds / 3600);
  const mins = Math.floor((elapsedSeconds % 3600) / 60);
  const secs = elapsedSeconds % 60;
  const clockStr = [hrs, mins, secs].map((v) => String(v).padStart(2, "0")).join(":");

  return (
    <div className="console-container">
      {/* ── Top Header Bar ─────────────────────────────────────────────── */}
      <header className="console-header">
        {/* Left: Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "44px",
              height: "44px",
              background: "rgba(6,182,212,0.12)",
              border: "1px solid rgba(6,182,212,0.35)",
              borderRadius: "10px",
              boxShadow: "0 0 16px rgba(6,182,212,0.12), inset 0 1px 0 rgba(6,182,212,0.15)",
              flexShrink: 0,
            }}
          >
            <Film size={22} color="var(--color-cyan)" />
          </div>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h1
                style={{
                  fontSize: "1.20rem",
                  fontWeight: 800,
                  letterSpacing: "-0.03em",
                  background: "linear-gradient(90deg, #f0f4ff 0%, #a5f3fc 80%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                GENLOCK SENTINEL
              </h1>
              <span className="badge badge-info">v0.1.0 · ICVFX nDisplay SRE</span>
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.68rem",
                color: "var(--text-muted)",
                marginTop: "2px",
                letterSpacing: "0.02em",
              }}
            >
              Session:{" "}
              <span style={{ color: "var(--text-secondary)" }}>{sessionId}</span>
              {" · "}
              Mode:{" "}
              <span style={{ color: "var(--color-cyan)", fontWeight: 700 }}>
                SEMI-AUTONOMOUS (LOCKED)
              </span>
              {" · "}
              Clock:{" "}
              <span style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                {clockStr}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Status strip */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {/* SSE connection status */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "7px",
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              color: "var(--text-secondary)",
            }}
          >
            <Radio size={13} color={connected ? "var(--color-emerald)" : "var(--color-amber)"} />
            <div
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                background: connected ? "var(--color-emerald)" : "var(--color-amber)",
                boxShadow: connected
                  ? "0 0 8px var(--color-emerald)"
                  : "0 0 8px var(--color-amber)",
              }}
              className={connected ? "" : "pulse-active"}
            />
            {connected ? "SSE CONNECTED" : "CONNECTING..."}
          </div>

          {/* ── Nuclear Stage Burn Badge ─────────────────────────────── */}
          <div className="burn-badge">
            <Flame
              size={18}
              color="var(--color-amber)"
              style={{ filter: "drop-shadow(0 0 6px rgba(245,158,11,0.7))", flexShrink: 0 }}
            />
            <div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.60rem",
                  fontWeight: 700,
                  color: "var(--color-amber)",
                  letterSpacing: "0.10em",
                  textTransform: "uppercase",
                }}
              >
                Stage Burn Accrued
              </div>
              {/* Live ticking burn value */}
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "1.05rem",
                  fontWeight: 800,
                  color: "#fef3c7",
                  lineHeight: 1,
                  letterSpacing: "-0.02em",
                }}
              >
                ${burnDollars.toLocaleString()}
                <span style={{ fontSize: "0.65rem", color: "var(--color-amber)", opacity: 0.8 }}>
                  .{String(burnCents).padStart(2, "0")}
                  <span className="burn-ticker" style={{ fontSize: "0.55rem", opacity: 0.55 }}>
                    {String(burnMillis).padStart(2, "0")}
                  </span>
                </span>
                <span style={{ fontSize: "0.70rem", color: "var(--color-amber)", fontWeight: 600, marginLeft: "4px" }}>
                  USD
                </span>
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.56rem",
                  color: "rgba(245,158,11,0.65)",
                  marginTop: "1px",
                  letterSpacing: "0.04em",
                }}
              >
                CALCULATED AT $1,800/MIN PRODUCTION LOSS
              </div>
            </div>
          </div>

          {/* Session status chip */}
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

          {/* ── Aircraft-Grade Emergency Stop ────────────────────────── */}
          <button
            onClick={handleEmergencyStop}
            disabled={haltingSession || state.session_status === "stopped"}
            className="btn btn-emergency-stop"
            title="Execute emergency halt of all autonomous agent actions"
          >
            <AlertTriangle size={14} />
            {state.session_status === "stopped" ? "SESSION HALTED" : "EMERGENCY STOP"}
          </button>
        </div>
      </header>

      {/* Persistent Error Banner */}
      <FailureBanner error={activeError} onDismiss={() => setActiveError(null)} />

      {/* 7-Node ADK Workflow Graph Tracker */}
      <div className="step-tracker-wrapper">
        <StepTracker
          currentStep={currentStep}
          historySteps={historySteps}
          route={activeRoute}
        />
      </div>

      {/* ── Main 12-Column Cockpit Grid ─────────────────────────────────
           Left  (xl: 7/12): SyncOffsetChart + LED matrix
           Right (xl: 5/12): Diagnosis · Evidence · Remediation
      ──────────────────────────────────────────────────────────────── */}
      <div className="cockpit-grid">
        {/* Left column — telemetry */}
        <div className="cockpit-col-left">
          <SyncOffsetChart samples={telemetrySamples} thresholdUs={150.0} />
        </div>

        {/* Right column — diagnosis, evidence, remediation */}
        <div className="cockpit-col-right cockpit-scroll">
          {/* Subtle scroll hint affordance */}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
              paddingRight: "2px",
              marginBottom: "-4px",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                color: "rgba(6, 182, 212, 0.7)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                background: "rgba(6, 182, 212, 0.06)",
                border: "1px solid rgba(6, 182, 212, 0.2)",
                padding: "2px 6px",
                borderRadius: "4px",
              }}
            >
              Scrollable Feed ↕
            </span>
          </div>

          <div className="shrink-0" style={{ flexShrink: 0 }}>
            <DiagnosisBadge diagnosis={latestDiagnosis} streamingReasoning={streamingReasoning} />
          </div>
          <div className="shrink-0" style={{ flexShrink: 0 }}>
            <EvidenceCard evidence={activeEvidence} eventId={activeEventId} />
          </div>
          <div className="shrink-0" style={{ flexShrink: 0 }}>
            <RemediationLog logs={state.remediation_log} />
          </div>
        </div>
      </div>

      {/* HITL Approval Modal */}
      {state.pending_hitl_card && state.session_status === "awaiting_approval" && (
        <ApprovalCardModal
          card={state.pending_hitl_card}
          sessionId={sessionId}
          onDecisionSubmitted={() => {
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
