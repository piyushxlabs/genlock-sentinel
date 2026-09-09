import React from "react";
import { AlertTriangle, RefreshCw, X } from "lucide-react";

interface FailureBannerProps {
  error: { message: string; code: string } | null;
  onDismiss?: () => void;
}

export const FailureBanner: React.FC<FailureBannerProps> = ({ error, onDismiss }) => {
  if (!error) return null;

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "14px",
        padding: "14px 20px",
        background: "rgba(239, 68, 68, 0.2)",
        border: "1px solid rgba(239, 68, 68, 0.5)",
        borderRadius: "10px",
        marginBottom: "20px",
        color: "#fecaca",
        boxShadow: "0 0 24px rgba(239, 68, 68, 0.25)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <AlertTriangle size={22} color="#ef4444" style={{ flexShrink: 0 }} />
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "0.9rem", fontWeight: 700, color: "#ffffff" }}>
              Operational Agent Error
            </span>
            <span className="mono" style={{ fontSize: "0.75rem", background: "#7f1d1d", padding: "2px 6px", borderRadius: "4px" }}>
              {error.code}
            </span>
          </div>
          <div style={{ fontSize: "0.825rem", marginTop: "2px", color: "#fca5a5" }}>
            {error.message}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <button
          onClick={() => window.location.reload()}
          className="btn"
          style={{
            padding: "6px 10px",
            fontSize: "0.75rem",
            background: "rgba(255,255,255,0.1)",
            color: "#ffffff",
          }}
        >
          <RefreshCw size={13} /> Reconnect
        </button>
        {onDismiss && (
          <button
            onClick={onDismiss}
            style={{
              background: "none",
              border: "none",
              color: "#fca5a5",
              cursor: "pointer",
              padding: "4px",
            }}
          >
            <X size={18} />
          </button>
        )}
      </div>
    </div>
  );
};
