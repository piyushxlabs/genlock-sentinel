import React from "react";
import { CheckCircle2, Circle, Clock, GitBranch } from "lucide-react";
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
  branch?: "main" | "autonomous" | "hitl";
}

const ALL_PIPELINE_STEPS: StepNodeDef[] = [
  { id: "stream_watch", label: "Stream Watch", sublabel: "Telemetry Polling", branch: "main" },
  { id: "evidence_triage", label: "Evidence Triage", sublabel: "Gemini 3.7 Flash", branch: "main" },
  { id: "root_cause_correlation", label: "Correlation", sublabel: "Gemini 3.1 Pro", branch: "main" },
  { id: "autonomous_dispatch", label: "Autonomous Dispatch", sublabel: "Deterministic", branch: "autonomous" },
  { id: "hitl_card_generation", label: "HITL Card Gen", sublabel: "Gemini 3.7 Flash", branch: "hitl" },
  { id: "hitl_pause", label: "HITL Pause", sublabel: "Checkpoint Interrupt", branch: "hitl" },
  { id: "post_approval_handling", label: "Post-Approval", sublabel: "Deterministic", branch: "hitl" },
];

export const StepTracker: React.FC<StepTrackerProps> = ({
  currentStep,
  historySteps = [],
  route = null,
}) => {
  return (
    <div className="glass-panel" style={{ padding: "18px 20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
        <GitBranch size={18} color="var(--color-cyan)" />
        <h3 style={{ fontSize: "0.95rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>
          ADK 2.x 7-Node Workflow Runtime Graph
        </h3>
        {route && (
          <span
            className={`badge ${route === "hitl" ? "badge-warning" : "badge-info"}`}
            style={{ marginLeft: "auto" }}
          >
            Route: {route.toUpperCase()}
          </span>
        )}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(135px, 1fr))",
          gap: "10px",
          alignItems: "stretch",
        }}
      >
        {ALL_PIPELINE_STEPS.map((step, idx) => {
          const isActive = currentStep === step.id;
          const isCompleted = historySteps.includes(step.id) && !isActive;
          const isMutedBranch =
            (route === "autonomous" && step.branch === "hitl") ||
            (route === "hitl" && step.branch === "autonomous");

          let borderColor = "var(--border-subtle)";
          let bgColor = "var(--bg-secondary)";
          let textColor = "var(--text-secondary)";

          if (isActive) {
            borderColor = "var(--color-cyan)";
            bgColor = "rgba(6, 182, 212, 0.1)";
            textColor = "var(--color-cyan)";
          } else if (isCompleted) {
            borderColor = "rgba(16, 185, 129, 0.4)";
            bgColor = "rgba(16, 185, 129, 0.05)";
            textColor = "var(--color-emerald)";
          } else if (isMutedBranch) {
            opacity: 0.4;
          }

          return (
            <div
              key={step.id}
              style={{
                display: "flex",
                flexDirection: "column",
                padding: "10px 12px",
                background: bgColor,
                border: `1px solid ${borderColor}`,
                borderRadius: "8px",
                opacity: isMutedBranch ? 0.35 : 1,
                transition: "all 0.2s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                {isCompleted ? (
                  <CheckCircle2 size={14} color="var(--color-emerald)" />
                ) : isActive ? (
                  <Clock size={14} color="var(--color-cyan)" className="pulse-active" />
                ) : (
                  <Circle size={14} color="var(--text-muted)" />
                )}
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: textColor }}>
                  Node {idx + 1}
                </span>
              </div>

              <div style={{ fontSize: "0.825rem", fontWeight: 600, color: "var(--text-primary)" }}>
                {step.label}
              </div>
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "2px" }}>
                {step.sublabel}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
