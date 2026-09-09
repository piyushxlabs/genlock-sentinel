import React, { useState } from "react";
import { Brain, ChevronDown, ChevronUp, Sparkles, Terminal } from "lucide-react";
import { DiagnosisRecord } from "../stream/agui-client";

interface DiagnosisBadgeProps {
  diagnosis?: DiagnosisRecord | null;
  streamingReasoning?: string;
}

export const DiagnosisBadge: React.FC<DiagnosisBadgeProps> = ({
  diagnosis,
  streamingReasoning = "",
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!diagnosis && !streamingReasoning) {
    return (
      <div className="glass-panel" style={{ padding: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--text-muted)" }}>
          <Brain size={18} />
          <span style={{ fontSize: "0.9rem", fontStyle: "italic" }}>
            No diagnosis formulated yet. Root-Cause Correlation node in standby...
          </span>
        </div>
      </div>
    );
  }

  const category = diagnosis?.category || "ambiguous";
  const confidence = diagnosis?.confidence ?? 0.0;
  const rationale = diagnosis?.rationale || "";

  // Category styles
  const categoryConfig: Record<string, { label: string; badgeClass: string; color: string }> = {
    network_jitter: {
      label: "Network Jitter (PTP / Packet Delay)",
      badgeClass: "badge-warning",
      color: "var(--color-amber)",
    },
    thermal_throttle: {
      label: "Thermal Throttling (GPU Core)",
      badgeClass: "badge-critical",
      color: "var(--color-rose)",
    },
    asset_streaming_stall: {
      label: "Asset Streaming Stall (I/O Bottleneck)",
      badgeClass: "badge-info",
      color: "var(--color-cyan)",
    },
    ambiguous: {
      label: "Ambiguous (Supervisor Intervention Required)",
      badgeClass: "badge-critical",
      color: "var(--color-rose)",
    },
  };

  const config = categoryConfig[category] || {
    label: "Diagnosis Error",
    badgeClass: "badge-critical",
    color: "var(--color-rose)",
  };

  const pct = Math.round(confidence * 100);

  return (
    <div className="glass-panel" style={{ padding: "20px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Brain size={18} color="var(--color-cyan)" />
          <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>
            Root-Cause Correlation (Gemini 3.1 Pro)
          </h3>
        </div>

        <span className={`badge ${config.badgeClass}`}>
          {config.label}
        </span>
      </div>

      {/* Confidence Magnitude Meter */}
      <div style={{ marginBottom: "16px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "0.8rem",
            marginBottom: "6px",
          }}
        >
          <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
            Statistical Confidence Floor (Threshold: 75%)
          </span>
          <span
            className="mono"
            style={{
              fontWeight: 700,
              color: confidence >= 0.75 ? "var(--color-emerald)" : "var(--color-amber)",
            }}
          >
            {pct}% ({confidence.toFixed(2)})
          </span>
        </div>

        <div className="meter-track">
          <div
            className="meter-fill"
            style={{
              width: `${pct}%`,
              backgroundColor:
                confidence >= 0.85
                  ? "var(--color-emerald)"
                  : confidence >= 0.75
                  ? "var(--color-cyan)"
                  : "var(--color-amber)",
            }}
          />
        </div>
      </div>

      {/* Rationale Citation Text */}
      {rationale && (
        <div
          style={{
            fontSize: "0.85rem",
            color: "var(--text-primary)",
            lineHeight: 1.5,
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-card)",
            borderRadius: "8px",
            padding: "12px 14px",
            marginBottom: "12px",
          }}
        >
          <div
            style={{
              fontSize: "0.75rem",
              fontWeight: 700,
              textTransform: "uppercase",
              color: "var(--text-muted)",
              marginBottom: "4px",
            }}
          >
            Grounded Diagnostic Rationale
          </div>
          {rationale}
        </div>
      )}

      {/* View Reasoning Toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="btn"
        style={{
          width: "100%",
          padding: "8px 12px",
          fontSize: "0.8rem",
          background: "rgba(255, 255, 255, 0.04)",
          color: "var(--text-secondary)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <Sparkles size={14} color="var(--color-cyan)" />
        {expanded ? "Hide Native Reasoning Tokens" : "View Native Reasoning Tokens (Gemini 3.1 Pro)"}
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {/* Expandable Native Reasoning Panel */}
      {expanded && (
        <div
          style={{
            marginTop: "12px",
            background: "rgba(0, 0, 0, 0.35)",
            border: "1px solid rgba(6, 182, 212, 0.3)",
            borderRadius: "8px",
            padding: "12px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "0.75rem",
              color: "var(--color-cyan)",
              marginBottom: "6px",
              fontWeight: 600,
            }}
          >
            <Terminal size={12} /> Live Thinking Trace
          </div>
          <div
            className="mono"
            style={{
              fontSize: "0.775rem",
              color: "#cbd5e1",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
              maxHeight: "180px",
              overflowY: "auto",
            }}
          >
            {streamingReasoning || rationale || "No native thinking tokens captured."}
          </div>
        </div>
      )}
    </div>
  );
};
