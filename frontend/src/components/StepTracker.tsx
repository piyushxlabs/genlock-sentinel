import React, { useEffect, useRef } from "react";
import { GitBranch } from "lucide-react";
import { StepEvent } from "../stream/agui-client";

interface StepTrackerProps {
  currentStep?: StepEvent["step_name"] | null;
  historySteps?: string[];
  route?: "autonomous" | "hitl" | null;
}

interface StepNodeDef {
  id: StepEvent["step_name"];
  label: string;
  sublabel: string;
  branch: "main" | "autonomous" | "hitl";
  shortLabel: string;
}

const ALL_PIPELINE_STEPS: StepNodeDef[] = [
  { id: "stream_watch",        label: "Stream Watch",      sublabel: "Telemetry Poll",     branch: "main",       shortLabel: "N1" },
  { id: "evidence_triage",     label: "Evidence Triage",   sublabel: "Gemini 3.7 Flash",   branch: "main",       shortLabel: "N2" },
  { id: "root_cause_correlation", label: "Correlation",   sublabel: "Gemini 3.1 Pro",     branch: "main",       shortLabel: "N3" },
  { id: "autonomous_dispatch", label: "Auto Dispatch",     sublabel: "Deterministic",      branch: "autonomous", shortLabel: "N4" },
  { id: "hitl_card_generation",label: "HITL Card Gen",     sublabel: "Gemini 3.7 Flash",   branch: "hitl",       shortLabel: "N5" },
  { id: "hitl_pause",          label: "HITL Pause",        sublabel: "Checkpoint Gate",    branch: "hitl",       shortLabel: "N6" },
  { id: "post_approval_handling", label: "Post-Approval", sublabel: "Deterministic",      branch: "hitl",       shortLabel: "N7" },
];

/** Tick counter for animated SVG dash offset */
function useTick(intervalMs = 40): number {
  const [tick, setTick] = React.useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return tick;
}

export const StepTracker: React.FC<StepTrackerProps> = ({
  currentStep,
  historySteps = [],
  route = null,
}) => {
  const tick = useTick(50);
  const containerRef = useRef<HTMLDivElement>(null);

  const getNodeState = (step: StepNodeDef, _idx: number): "active" | "completed" | "muted" | "idle" => {
    const isActive    = currentStep === step.id;
    const isCompleted = historySteps.includes(step.id) && !isActive;
    const isMuted     =
      (route === "autonomous" && step.branch === "hitl") ||
      (route === "hitl"       && step.branch === "autonomous");
    if (isActive)    return "active";
    if (isCompleted) return "completed";
    if (isMuted)     return "muted";
    return "idle";
  };

  // Connector is "energized" if the node to the left is completed/active
  const isConnectorLit = (nodeIdx: number): boolean => {
    if (nodeIdx === 0) return false;
    const prev = ALL_PIPELINE_STEPS[nodeIdx - 1];
    return historySteps.includes(prev.id) || currentStep === prev.id;
  };

  return (
    <div
      className="glass-panel"
      style={{ padding: "16px 20px" }}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
        <GitBranch size={17} color="var(--color-cyan)" />
        <h3
          style={{
            fontSize: "0.82rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--text-secondary)",
          }}
        >
          ADK 2.x • 7-Node Workflow Runtime
        </h3>
        {route && (
          <span
            className={`badge ${route === "hitl" ? "badge-warning" : "badge-info"}`}
            style={{ marginLeft: "auto" }}
          >
            Route: {route === "hitl" ? "HITL Approval" : "Autonomous"}
          </span>
        )}
      </div>

      {/* Node bus */}
      <div
        ref={containerRef}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0px",
          overflowX: "auto",
          paddingBottom: "4px",
        }}
      >
        {ALL_PIPELINE_STEPS.map((step, idx) => {
          const state = getNodeState(step, idx);
          const connLit = isConnectorLit(idx);
          const dashOffset = -(tick * 1.2) % 20;

          return (
            <React.Fragment key={step.id}>
              {/* Animated SVG connector between nodes */}
              {idx > 0 && (
                <svg
                  width="32"
                  height="24"
                  viewBox="0 0 32 24"
                  style={{ flexShrink: 0, overflow: "visible" }}
                >
                  {/* Base dim track */}
                  <line
                    x1={0} y1={12} x2={32} y2={12}
                    stroke="rgba(255,255,255,0.06)"
                    strokeWidth={2}
                  />
                  {/* Energized flow line */}
                  {connLit && (
                    <>
                      {/* Glowing energy */}
                      <line
                        x1={0} y1={12} x2={32} y2={12}
                        stroke="rgba(6,182,212,0.20)"
                        strokeWidth={6}
                        strokeLinecap="round"
                      />
                      {/* Moving dash */}
                      <line
                        x1={0} y1={12} x2={32} y2={12}
                        stroke="#06b6d4"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeDasharray="6 14"
                        strokeDashoffset={dashOffset}
                      />
                      {/* Arrow head */}
                      <polygon
                        points="26,8 32,12 26,16"
                        fill="rgba(6,182,212,0.75)"
                        style={{ filter: "drop-shadow(0 0 3px rgba(6,182,212,0.8))" }}
                      />
                    </>
                  )}
                  {!connLit && (
                    /* Dim arrow */
                    <polygon
                      points="26,10 30,12 26,14"
                      fill="rgba(255,255,255,0.10)"
                    />
                  )}
                </svg>
              )}

              {/* Node card */}
              <NodeCard step={step} idx={idx} state={state} />
            </React.Fragment>
          );
        })}
      </div>

      {/* Branch legend */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "20px",
          marginTop: "12px",
          paddingTop: "10px",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        <LegendDot color="var(--color-cyan)" label="Main path (N1–N3)" />
        <LegendDot color="var(--color-emerald)" label="Autonomous (N4)" />
        <LegendDot color="var(--color-amber)" label="HITL path (N5–N7)" />
        <LegendDot color="rgba(255,255,255,0.25)" label="Idle / muted" />
      </div>
    </div>
  );
};

/* ──────────────────────────────────────────────────────────────────── */
/* NodeCard sub-component                                               */
/* ──────────────────────────────────────────────────────────────────── */
interface NodeCardProps {
  step: StepNodeDef;
  idx: number;
  state: "active" | "completed" | "muted" | "idle";
}

const NodeCard: React.FC<NodeCardProps> = ({ step, idx, state }) => {
  const branchColor: Record<string, string> = {
    main: "var(--color-cyan)",
    autonomous: "var(--color-emerald)",
    hitl: "var(--color-amber)",
  };

  const accent = branchColor[step.branch] || "var(--color-cyan)";

  const styles: Record<typeof state, React.CSSProperties> = {
    active: {
      background: "rgba(6,182,212,0.10)",
      border: "1px solid rgba(6,182,212,0.55)",
      boxShadow: "0 0 20px rgba(6,182,212,0.30), inset 0 1px 0 rgba(6,182,212,0.15)",
    },
    completed: {
      background: "rgba(16,185,129,0.07)",
      border: "1px solid rgba(16,185,129,0.35)",
      boxShadow: "0 0 12px rgba(16,185,129,0.12)",
    },
    muted: {
      background: "rgba(255,255,255,0.02)",
      border: "1px solid rgba(255,255,255,0.05)",
      opacity: 0.30,
    },
    idle: {
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.08)",
    },
  };

  const dotColor = {
    active: "var(--color-cyan)",
    completed: "var(--color-emerald)",
    muted: "rgba(255,255,255,0.20)",
    idle: "rgba(255,255,255,0.20)",
  }[state];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        minWidth: "106px",
        padding: "10px 10px",
        borderRadius: "10px",
        transition: "all 0.25s ease",
        position: "relative",
        flexShrink: 0,
        ...(styles[state]),
        ...(state === "active" ? { animation: "halo-pulse 2s ease-in-out infinite" } : {}),
        ...(state === "completed" ? { animation: "halo-pulse-emerald 3s ease-in-out infinite" } : {}),
      }}
    >
      {/* Node number & status dot row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          marginBottom: "6px",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.65rem",
            fontWeight: 700,
            color: state === "muted" ? "rgba(255,255,255,0.25)" : accent,
            letterSpacing: "0.06em",
          }}
        >
          NODE {idx + 1}
        </span>

        {/* Animated status dot */}
        <div style={{ position: "relative", width: "10px", height: "10px" }}>
          {/* Ping ring (active only) */}
          {state === "active" && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                borderRadius: "50%",
                background: dotColor,
                opacity: 0,
              }}
              className="led-ping-ring"
            />
          )}
          <div
            style={{
              position: "absolute",
              inset: "2px",
              borderRadius: "50%",
              background: dotColor,
              boxShadow: state === "active" ? `0 0 6px ${dotColor}` : "none",
            }}
            className={state === "active" ? "pulse-active" : ""}
          />
        </div>
      </div>

      {/* Label */}
      <div
        style={{
          fontSize: "0.77rem",
          fontWeight: 700,
          color: state === "muted" ? "rgba(255,255,255,0.25)"
               : state === "active" ? "var(--color-cyan)"
               : state === "completed" ? "var(--color-emerald)"
               : "var(--text-secondary)",
          textAlign: "center",
          lineHeight: 1.2,
          marginBottom: "3px",
        }}
      >
        {step.label}
      </div>

      {/* Sublabel */}
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.60rem",
          color: state === "muted" ? "rgba(255,255,255,0.15)" : "var(--text-muted)",
          textAlign: "center",
          letterSpacing: "0.02em",
        }}
      >
        {step.sublabel}
      </div>

      {/* Branch tag */}
      <div
        style={{
          marginTop: "6px",
          width: "100%",
          height: "2px",
          borderRadius: "1px",
          background: state === "muted"
            ? "rgba(255,255,255,0.06)"
            : state === "active"
            ? accent
            : state === "completed"
            ? "var(--color-emerald)"
            : "rgba(255,255,255,0.08)",
          boxShadow: (state === "active" || state === "completed")
            ? `0 0 8px ${state === "active" ? accent : "var(--color-emerald)"}`
            : "none",
          transition: "all 0.3s ease",
        }}
      />
    </div>
  );
};

/* Legend dot */
const LegendDot: React.FC<{ color: string; label: string }> = ({ color, label }) => (
  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
    <div
      style={{
        width: "8px",
        height: "8px",
        borderRadius: "50%",
        background: color,
        flexShrink: 0,
      }}
    />
    <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontWeight: 500 }}>
      {label}
    </span>
  </div>
);
