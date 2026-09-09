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
    return (
      <div className="glass-panel" style={{ padding: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--text-muted)" }}>
          <Database size={18} />
          <span style={{ fontSize: "0.9rem", fontStyle: "italic" }}>
            No active evidence bundle loaded. Waiting for Evidence Triage node...
          </span>
        </div>
      </div>
    );
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
          <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>
            Triaged Observability Evidence
          </h3>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {eventId && (
            <span className="mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              {eventId}
            </span>
          )}
          <span
            className={`badge ${evidence.logs_available ? "badge-nominal" : "badge-warning"}`}
          >
            {evidence.logs_available ? "Loki Logs Active" : "Log Gap Flagged"}
          </span>
        </div>
      </div>

      {/* Conditional Amber Anomaly Banner */}
      {evidence.anomaly && (
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "10px",
            padding: "12px 14px",
            background: "rgba(245, 158, 11, 0.12)",
            border: "1px solid rgba(245, 158, 11, 0.35)",
            borderRadius: "8px",
            marginBottom: "16px",
          }}
        >
          <AlertCircle size={18} color="var(--color-amber)" style={{ marginTop: "2px", flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--color-amber)" }}>
              Telemetry Anomaly Detected
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              {evidence.anomaly}
            </div>
          </div>
        </div>
      )}

      {/* Two Labeled Text Panels: Loki Logs & Tempo Traces */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        {/* Loki Logs Panel */}
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-card)",
            borderRadius: "8px",
            padding: "14px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "8px",
            }}
          >
            <button
              onClick={() => setShowLogs(!showLogs)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: "none",
                border: "none",
                color: "var(--text-primary)",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <FileText size={15} color="var(--color-cyan)" />
              Loki Log Summary
            </button>

            <button
              onClick={() => copyToClipboard(evidence.log_summary, false)}
              className="btn"
              style={{
                padding: "4px 8px",
                fontSize: "0.75rem",
                background: "rgba(255, 255, 255, 0.05)",
                color: "var(--text-secondary)",
              }}
              title="Copy Loki Log Summary"
            >
              {copiedLog ? <Check size={13} color="var(--color-emerald)" /> : <Copy size={13} />}
              {copiedLog ? "Copied" : "Copy"}
            </button>
          </div>

          {showLogs && (
            <div
              className="mono"
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                lineHeight: 1.45,
                background: "rgba(0, 0, 0, 0.2)",
                padding: "10px",
                borderRadius: "6px",
                maxHeight: "160px",
                overflowY: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {evidence.log_summary || "No relevant log lines retrieved for this drift window."}
            </div>
          )}
        </div>

        {/* Tempo Traces Panel */}
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-card)",
            borderRadius: "8px",
            padding: "14px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "8px",
            }}
          >
            <button
              onClick={() => setShowTraces(!showTraces)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: "none",
                border: "none",
                color: "var(--text-primary)",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <Network size={15} color="#a855f7" />
              Tempo Trace Summary
            </button>

            <button
              onClick={() => copyToClipboard(evidence.trace_summary, true)}
              className="btn"
              style={{
                padding: "4px 8px",
                fontSize: "0.75rem",
                background: "rgba(255, 255, 255, 0.05)",
                color: "var(--text-secondary)",
              }}
              title="Copy Tempo Trace Summary"
            >
              {copiedTrace ? <Check size={13} color="var(--color-emerald)" /> : <Copy size={13} />}
              {copiedTrace ? "Copied" : "Copy"}
            </button>
          </div>

          {showTraces && (
            <div
              className="mono"
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                lineHeight: 1.45,
                background: "rgba(0, 0, 0, 0.2)",
                padding: "10px",
                borderRadius: "6px",
                maxHeight: "160px",
                overflowY: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
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
