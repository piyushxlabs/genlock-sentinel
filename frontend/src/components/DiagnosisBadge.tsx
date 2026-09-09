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
    return <DiagnosisStandbyPanel />;
  }

  const category   = diagnosis?.category   || "ambiguous";
  const confidence = diagnosis?.confidence ?? 0.0;
  const rationale  = diagnosis?.rationale  || "";

  const categoryConfig: Record<string, { label: string; badgeClass: string; color: string }> = {
    network_jitter:       { label: "Network Jitter (PTP / Packet Delay)",          badgeClass: "badge-warning",  color: "var(--color-amber)" },
    thermal_throttle:     { label: "Thermal Throttling (GPU Core)",                 badgeClass: "badge-critical", color: "var(--color-rose)"  },
    asset_streaming_stall:{ label: "Asset Streaming Stall (I/O Bottleneck)",        badgeClass: "badge-info",     color: "var(--color-cyan)"  },
    ambiguous:            { label: "Ambiguous — Supervisor Intervention Required",  badgeClass: "badge-critical", color: "var(--color-rose)"  },
  };

  const config = categoryConfig[category] || { label: "Diagnosis Error", badgeClass: "badge-critical", color: "var(--color-rose)" };
  const pct = Math.round(confidence * 100);

  return (
    <div
      className="glass-panel cockpit-scroll"
      style={{
        padding: "16px 20px",
        maxHeight: "320px",
        overflowY: "auto",
      }}
    >
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
          <div>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>
              Root-Cause Correlation
            </h3>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-muted)", marginTop: "1px", letterSpacing: "0.06em" }}>
              GEMINI 3.1 PRO · TEMPERATURE 0.0 · STRUCTURED OUTPUT
            </div>
          </div>
        </div>
        <span className={`badge ${config.badgeClass}`}>{config.label}</span>
      </div>

      {/* Confidence meter */}
      <div style={{ marginBottom: "16px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "0.78rem",
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
                confidence >= 0.85 ? "var(--color-emerald)"
                : confidence >= 0.75 ? "var(--color-cyan)"
                : "var(--color-amber)",
              color:
                confidence >= 0.85 ? "var(--color-emerald)"
                : confidence >= 0.75 ? "var(--color-cyan)"
                : "var(--color-amber)",
            }}
          />
        </div>
      </div>

      {/* Rationale */}
      {rationale && (
        <div
          style={{
            fontSize: "0.83rem",
            color: "var(--text-primary)",
            lineHeight: 1.55,
            background: "rgba(0,0,0,0.25)",
            border: "1px solid var(--border-card)",
            borderRadius: "8px",
            padding: "12px 14px",
            marginBottom: "12px",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.65rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-muted)",
              marginBottom: "4px",
            }}
          >
            ▸ Grounded Diagnostic Rationale
          </div>
          {rationale}
        </div>
      )}

      {/* Reasoning toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="btn"
        style={{
          width: "100%",
          padding: "8px 12px",
          fontSize: "0.78rem",
          background: "rgba(6,182,212,0.05)",
          color: "var(--text-secondary)",
          border: "1px solid rgba(6,182,212,0.15)",
        }}
      >
        <Sparkles size={13} color="var(--color-cyan)" />
        {expanded ? "Hide Native Reasoning Tokens" : "View Native Reasoning Tokens (Gemini 3.1 Pro)"}
        {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {/* Reasoning panel */}
      {expanded && (
        <div
          style={{
            marginTop: "12px",
            background: "rgba(0,0,0,0.40)",
            border: "1px solid rgba(6,182,212,0.22)",
            borderRadius: "8px",
            padding: "12px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontFamily: "var(--font-mono)",
              fontSize: "0.68rem",
              color: "var(--color-cyan)",
              marginBottom: "6px",
              fontWeight: 700,
              letterSpacing: "0.06em",
            }}
          >
            <Terminal size={12} /> LIVE THINKING TRACE · GEMINI 3.1 PRO
          </div>
          <div
            className="mono"
            style={{
              fontSize: "0.75rem",
              color: "#b0bed4",
              lineHeight: 1.55,
              whiteSpace: "pre-wrap",
              maxHeight: "200px",
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

/* ─────────────────────────────────────────────────────────────────────── */
/* Root-Cause Correlation Standby Sensor                                   */
/* ─────────────────────────────────────────────────────────────────────── */
const DiagnosisStandbyPanel: React.FC = () => {
  return (
    <div className="glass-panel" style={{ padding: "16px 20px", maxHeight: "320px", overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
        <Brain size={17} color="var(--color-cyan)" />
        <div>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Root-Cause Correlation</h3>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-muted)", marginTop: "1px", letterSpacing: "0.06em" }}>
            GEMINI 3.1 PRO · TEMPERATURE 0.0
          </div>
        </div>
      </div>

      {/* Node armed indicator */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: "10px",
          padding: "10px 14px",
        }}
      >
        {/* Brain wave animation */}
        <svg width="120" height="48" viewBox="0 0 120 48" style={{ opacity: 0.75 }}>
          <defs>
            <linearGradient id="waveGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%"   stopColor="rgba(6,182,212,0)" />
              <stop offset="30%"  stopColor="rgba(6,182,212,0.6)" />
              <stop offset="70%"  stopColor="rgba(6,182,212,0.6)" />
              <stop offset="100%" stopColor="rgba(6,182,212,0)" />
            </linearGradient>
          </defs>
          {/* Flat baseline */}
          <line x1={0} y1={24} x2={30} y2={24} stroke="url(#waveGrad)" strokeWidth={1.5} />
          {/* Spike */}
          <polyline
            points="30,24 40,4 48,44 56,4 64,24"
            fill="none" stroke="url(#waveGrad)" strokeWidth={1.8}
            strokeLinecap="round" strokeLinejoin="round"
          />
          {/* Flat tail */}
          <line x1={64} y1={24} x2={120} y2={24} stroke="url(#waveGrad)" strokeWidth={1.5} />
          {/* Scanning dot */}
          <circle cx={64} cy={24} r={3} fill="var(--color-cyan)"
            style={{ filter: "drop-shadow(0 0 4px rgba(6,182,212,0.9))" }}
            className="pulse-active"
          />
        </svg>

        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              fontWeight: 700,
              color: "var(--color-cyan)",
              letterSpacing: "0.10em",
              textTransform: "uppercase",
              marginBottom: "6px",
            }}
            className="standby-blink"
          >
            NODE 3 ARMED · AWAITING EVIDENCE BUNDLE
          </div>

          {[
            { label: "Model",       value: "gemini-3.1-pro" },
            { label: "Temperature", value: "0.0 (deterministic)" },
            { label: "Schema",      value: "RootCauseDiagnosis" },
            { label: "Confidence",  value: "Floor: 75%" },
          ].map((row) => (
            <div
              key={row.label}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "20px",
                padding: "2px 0",
              }}
            >
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.67rem", color: "var(--text-muted)" }}>
                {row.label}
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.67rem", color: "var(--text-secondary)", fontWeight: 600 }}>
                {row.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
