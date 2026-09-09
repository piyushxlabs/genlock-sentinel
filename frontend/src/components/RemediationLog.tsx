import React from "react";
import { CheckCircle2, Shield, XCircle, Zap } from "lucide-react";
import { RemediationAction } from "../stream/agui-client";

interface RemediationLogProps {
  logs: RemediationAction[];
}

export const RemediationLog: React.FC<RemediationLogProps> = ({ logs }) => {
  // Sort reverse-chronological (most recent first)
  const sortedLogs = [...logs].reverse();

  return (
    <div className="glass-panel" style={{ padding: "20px" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          marginBottom: "16px",
        }}
      >
        <Zap size={18} color="var(--color-cyan)" />
        <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>
          Remediation & Actuator Execution Log
        </h3>
        <span
          className="badge badge-info"
          style={{ marginLeft: "auto" }}
        >
          {logs.length} Actions Recorded
        </span>
      </div>

      {sortedLogs.length === 0 ? (
        <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontStyle: "italic", padding: "16px 0" }}>
          No remediation actuators dispatched yet. Cluster operating within nominal sync bounds.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxHeight: "360px", overflowY: "auto" }}>
          {sortedLogs.map((item, idx) => {
            const isDenial = item.action_taken.startsWith("denied_") || item.action_taken.startsWith("supervisor_denied");
            const isApprovalAudit = item.action_taken.startsWith("supervisor_approved");

            let icon = <CheckCircle2 size={16} color="var(--color-emerald)" />;
            if (isDenial || !item.success) {
              icon = <XCircle size={16} color="var(--color-rose)" />;
            } else if (isApprovalAudit) {
              icon = <Shield size={16} color="var(--color-cyan)" />;
            }

            return (
              <div
                key={item.action_id || idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "12px",
                  padding: "12px 14px",
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "8px",
                }}
              >
                <div style={{ marginTop: "2px", flexShrink: 0 }}>{icon}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>
                      {item.action_taken}
                    </span>
                    <span className="mono" style={{ fontSize: "0.725rem", color: "var(--text-muted)" }}>
                      {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : ""}
                    </span>
                  </div>

                  <div className="mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "3px" }}>
                    Node: {item.node_id} • Event: {item.event_id}
                  </div>

                  {item.details && Object.keys(item.details).length > 0 && (
                    <div
                      className="mono"
                      style={{
                        fontSize: "0.725rem",
                        color: "var(--text-secondary)",
                        marginTop: "6px",
                        background: "rgba(0,0,0,0.2)",
                        padding: "6px 8px",
                        borderRadius: "4px",
                      }}
                    >
                      {JSON.stringify(item.details)}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
