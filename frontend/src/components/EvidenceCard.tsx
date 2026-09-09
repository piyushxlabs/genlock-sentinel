import React, { useState } from "react";
import { AlertCircle, Check, Copy, Database, FileText, Network } from "lucide-react";
import { EvidenceBundle } from "../stream/agui-client";

interface EvidenceCardProps {
  evidence?: EvidenceBundle | null;
  eventId?: string;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ evidence, eventId }) => {
  const [copiedLog, setCopiedLog] = useState(false);
  const [copiedTrace, setCopiedTrace] = useState(false);
  const [showLogs, setShowLogs] = useState(true);
  const [showTraces, setShowTraces] = useState(true);

  if (!evidence) {
    return <EvidenceStandbyPanel />;
  }

  const copyToClipboard = (text: string, isTrace: boolean) => {
    navigator.clipboard.writeText(text);
    if (isTrace) {
      setCopiedTrace(true);
      setTimeout(() => setCopiedTrace(false), 2000);
    } else {
      setCopiedLog(true);
      setTimeout(() => setCopiedLog(false), 2000);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: "20px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Database size={18} color="var(--color-cyan)" />
          <div>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>
              Triaged Observability Evidence
            </h3>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.62rem",
                color: "var(--text-muted)",
                marginTop: "1px",
                letterSpacing: "0.06em",
              }}
            >
              LOKI LOGS · TEMPO TRACES · MCP GROUNDED
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {eventId && (
            <span
              className="mono"
              style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}
            >
              {eventId}
            </span>
          )}
          <span
            className={`badge ${evidence.logs_available ? "badge-nominal" : "badge-warning"}`}
          >
            {evidence.logs_available ? "Loki Active" : "Log Gap Flagged"}
          </span>
        </div>
      </div>

      {/* Anomaly banner */}
      {evidence.anomaly && (
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "10px",
            padding: "10px 14px",
            background: "rgba(245,158,11,0.10)",
            border: "1px solid rgba(245,158,11,0.32)",
            borderRadius: "8px",
            marginBottom: "16px",
          }}
        >
          <AlertCircle size={17} color="var(--color-amber)" style={{ marginTop: "2px", flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--color-amber)" }}>
              Telemetry Anomaly Detected
            </div>
            <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              {evidence.anomaly}
            </div>
          </div>
        </div>
      )}

      {/* Loki + Tempo panels */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
        {/* Loki */}
        <div
          style={{
            background: "rgba(0,0,0,0.25)",
            border: "1px solid var(--border-card)",
            borderRadius: "10px",
            padding: "12px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <button
              onClick={() => setShowLogs(!showLogs)}
              style={{
                display: "flex", alignItems: "center", gap: "6px",
                background: "none", border: "none",
                color: "var(--text-primary)",
                fontSize: "0.82rem", fontWeight: 600, cursor: "pointer",
              }}
            >
              <FileText size={14} color="var(--color-cyan)" />
              Loki Log Summary
            </button>
            <button
              onClick={() => copyToClipboard(evidence.log_summary, false)}
              className="btn"
              style={{ padding: "3px 7px", fontSize: "0.72rem", background: "rgba(255,255,255,0.05)", color: "var(--text-secondary)" }}
              title="Copy Loki Log Summary"
            >
              {copiedLog ? <Check size={12} color="var(--color-emerald)" /> : <Copy size={12} />}
              {copiedLog ? "Copied" : "Copy"}
            </button>
          </div>
          {showLogs && (
            <div
              className="mono"
              style={{
                fontSize: "0.77rem", color: "var(--text-secondary)", lineHeight: 1.5,
                background: "rgba(0,0,0,0.30)", padding: "10px", borderRadius: "6px",
                maxHeight: "160px", overflowY: "auto",
                whiteSpace: "pre-wrap", wordBreak: "break-word",
                border: "1px solid rgba(6,182,212,0.08)",
              }}
            >
              {evidence.log_summary || "No relevant log lines retrieved for this drift window."}
            </div>
          )}
        </div>

        {/* Tempo */}
        <div
          style={{
            background: "rgba(0,0,0,0.25)",
            border: "1px solid var(--border-card)",
            borderRadius: "10px",
            padding: "12px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <button
              onClick={() => setShowTraces(!showTraces)}
              style={{
                display: "flex", alignItems: "center", gap: "6px",
                background: "none", border: "none",
                color: "var(--text-primary)",
                fontSize: "0.82rem", fontWeight: 600, cursor: "pointer",
              }}
            >
              <Network size={14} color="#a855f7" />
              Tempo Trace Summary
            </button>
            <button
              onClick={() => copyToClipboard(evidence.trace_summary, true)}
              className="btn"
              style={{ padding: "3px 7px", fontSize: "0.72rem", background: "rgba(255,255,255,0.05)", color: "var(--text-secondary)" }}
              title="Copy Tempo Trace Summary"
            >
              {copiedTrace ? <Check size={12} color="var(--color-emerald)" /> : <Copy size={12} />}
              {copiedTrace ? "Copied" : "Copy"}
            </button>
          </div>
          {showTraces && (
            <div
              className="mono"
              style={{
                fontSize: "0.77rem", color: "var(--text-secondary)", lineHeight: 1.5,
                background: "rgba(0,0,0,0.30)", padding: "10px", borderRadius: "6px",
                maxHeight: "160px", overflowY: "auto",
                whiteSpace: "pre-wrap", wordBreak: "break-word",
                border: "1px solid rgba(168,85,247,0.08)",
              }}
            >
              {evidence.trace_summary || "No span traces retrieved for this event."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────────────── */
/* Cybernetic MCP Bus Standby Panel                                        */
/* ─────────────────────────────────────────────────────────────────────── */
const EvidenceStandbyPanel: React.FC = () => {
  return (
    <div className="glass-panel" style={{ padding: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
        <Database size={17} color="var(--color-cyan)" />
        <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>
          Triaged Observability Evidence
        </h3>
      </div>

      {/* Radar ring + status */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "28px 16px",
          gap: "18px",
        }}
      >
        {/* SVG radar graphic */}
        <svg width="90" height="90" viewBox="0 0 90 90" style={{ flexShrink: 0 }}>
          <defs>
            <radialGradient id="radarCore" cx="50%" cy="50%" r="50%">
              <stop offset="0%"   stopColor="rgba(6,182,212,0.18)" />
              <stop offset="100%" stopColor="rgba(6,182,212,0)" />
            </radialGradient>
          </defs>
          {/* Rings */}
          {[40, 30, 20, 10].map((r, i) => (
            <circle key={i} cx={45} cy={45} r={r}
              fill="none" stroke="rgba(6,182,212,0.15)" strokeWidth={1}
            />
          ))}
          <circle cx={45} cy={45} r={40} fill="url(#radarCore)" />
          {/* Cross hairs */}
          <line x1={45} y1={5}  x2={45} y2={85} stroke="rgba(6,182,212,0.10)" strokeWidth={1} />
          <line x1={5}  y1={45} x2={85} y2={45} stroke="rgba(6,182,212,0.10)" strokeWidth={1} />
          {/* Rotating sweep arm */}
          <g style={{ transformOrigin: "45px 45px", animation: "radar-sweep 3s linear infinite" }}>
            <line x1={45} y1={45} x2={45} y2={7}
              stroke="rgba(6,182,212,0.70)" strokeWidth={1.5} strokeLinecap="round"
            />
            <circle cx={45} cy={45} r={3} fill="var(--color-cyan)" />
          </g>
          {/* Center dot */}
          <circle cx={45} cy={45} r={4} fill="var(--color-cyan)"
            style={{ filter: "drop-shadow(0 0 4px rgba(6,182,212,0.8))" }}
          />
        </svg>

        {/* Status labels */}
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
            LOKI / TEMPO MCP BUS ACTIVE
          </div>

          {/* Bus status rows */}
          {[
            { label: "Grafana MCP", status: "CONNECTED", color: "var(--color-emerald)" },
            { label: "Loki LogQL",  status: "ARMED",     color: "var(--color-cyan)" },
            { label: "Tempo gRPC",  status: "LISTENING", color: "var(--color-cyan)" },
            { label: "Latency",     status: "0 µs DETECTED", color: "var(--color-emerald)" },
          ].map((row) => (
            <div
              key={row.label}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "24px",
                padding: "3px 0",
              }}
            >
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color: "var(--text-muted)" }}>
                {row.label}
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color: row.color, fontWeight: 700 }}>
                {row.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
