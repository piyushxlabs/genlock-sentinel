import React, { useState } from "react";
import { AlertOctagon, CheckCircle, DollarSign, Eye, XCircle } from "lucide-react";
import { HITLCard } from "../stream/agui-client";

interface ApprovalCardModalProps {
  card: HITLCard | null;
  sessionId: string;
  onDecisionSubmitted?: () => void;
}

export const ApprovalCardModal: React.FC<ApprovalCardModalProps> = ({
  card,
  sessionId,
  onDecisionSubmitted,
}) => {
  const [denyReason, setDenyReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!card) return null;

  const handleDecision = async (action: "approve" | "deny") => {
    setSubmitting(true);
    setErrorMsg(null);

    try {
      const payload: {
        action: "approve" | "deny";
        checkpoint_id: string;
        reason?: string;
      } = {
        action,
        checkpoint_id: `hitl_pause::${card.event_id}`,
      };

      if (action === "deny" && denyReason.trim()) {
        payload.reason = denyReason.trim();
      }

      const res = await fetch(`/sessions/${sessionId}/events/${card.event_id}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned status ${res.status}`);
      }

      if (onDecisionSubmitted) {
        onDecisionSubmitted();
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit supervisor decision");
    } finally {
      setSubmitting(false);
    }
  };

  const reasonLabels: Record<string, string> = {
    take_halt_required: "Take Halt Required (Stage Burn Risk)",
    capture_fallback_required: "Capture Fallback (Greenscreen Switch)",
    threshold_exceeded: "Threshold Exceeded (Cloud Failover Cost)",
    ambiguous_diagnosis: "Ambiguous Root Cause (Manual Decision)",
  };

  const actionLabels: Record<string, string> = {
    halt_live_take: "Halt Live Camera Take Immediately",
    fallback_to_greenscreen: "Fall Back to Greenscreen Capture Mode",
    execute_threshold_exceeding_failover: "Execute Threshold-Exceeding Cloud Failover",
  };

  return (
    <div
      className="modal-overlay"
      role="alertdialog"
      aria-live="assertive"
      aria-modal="true"
      aria-labelledby="hitl-title"
    >
      <div className="modal-dialog">
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            background: "rgba(245, 158, 11, 0.12)",
            borderBottom: "1px solid rgba(245, 158, 11, 0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <AlertOctagon size={26} color="var(--color-amber)" className="pulse-active" />
            <div>
              <h2
                id="hitl-title"
                style={{ fontSize: "1.15rem", fontWeight: 800, color: "var(--text-primary)" }}
              >
                Human-in-the-Loop Supervisor Sign-off Required
              </h2>
              <div style={{ fontSize: "0.775rem", color: "var(--color-amber)", marginTop: "2px" }}>
                Active ICVFX Stage Burn: $800–$2,500/minute. Graph execution durably paused.
              </div>
            </div>
          </div>

          <span className="badge badge-warning">
            {reasonLabels[card.escalation_reason] || card.escalation_reason}
          </span>
        </div>

        {/* Card Body */}
        <div style={{ padding: "24px" }}>
          {errorMsg && (
            <div
              style={{
                background: "rgba(244, 63, 94, 0.15)",
                border: "1px solid var(--color-rose)",
                color: "#fecdd3",
                padding: "10px 14px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                marginBottom: "16px",
              }}
            >
              {errorMsg}
            </div>
          )}

          {/* Action Proposition */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-card)",
              borderRadius: "10px",
              padding: "16px",
              marginBottom: "20px",
            }}
          >
            <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Proposed Remediation Actuator
            </div>
            <div
              style={{
                fontSize: "1.15rem",
                fontWeight: 700,
                color: "var(--color-cyan)",
                marginTop: "4px",
              }}
            >
              {actionLabels[card.proposed_action] || card.proposed_action}
            </div>
            <div className="mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px" }}>
              Target Node: {card.node_id} • Event ID: {card.event_id}
            </div>
          </div>

          {/* Metrics Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "20px" }}>
            <div
              style={{
                background: "var(--bg-secondary)",
                padding: "14px",
                borderRadius: "8px",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                <DollarSign size={15} color="var(--color-emerald)" />
                Cost Delta Estimate
              </div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "4px" }}>
                {card.cost_delta_estimate}
              </div>
            </div>

            <div
              style={{
                background: "var(--bg-secondary)",
                padding: "14px",
                borderRadius: "8px",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                <Eye size={15} color="var(--color-amber)" />
                Visual Impact Score
              </div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "4px" }}>
                {card.visual_impact_score}
              </div>
            </div>
          </div>

          {/* Root-Cause Summary */}
          <div style={{ marginBottom: "20px" }}>
            <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "6px" }}>
              Grounded Operational Summary
            </div>
            <div
              style={{
                background: "rgba(0, 0, 0, 0.25)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "8px",
                padding: "14px",
                fontSize: "0.875rem",
                lineHeight: 1.5,
                color: "#e2e8f0",
              }}
            >
              {card.root_cause_summary}
            </div>
          </div>

          {/* Optional Deny Reason Input */}
          <div style={{ marginBottom: "24px" }}>
            <label
              htmlFor="deny-reason"
              style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px" }}
            >
              Optional Supervisor Denial Reason (logged to audit trail on Deny):
            </label>
            <input
              id="deny-reason"
              type="text"
              value={denyReason}
              onChange={(e) => setDenyReason(e.target.value)}
              placeholder="e.g. Director called wrap; manual cluster reset preferred."
              disabled={submitting}
              style={{
                width: "100%",
                padding: "10px 14px",
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-card)",
                borderRadius: "8px",
                color: "var(--text-primary)",
                fontSize: "0.85rem",
                outline: "none",
              }}
            />
          </div>

          {/* Decision Buttons */}
          <div style={{ display: "flex", gap: "14px", justifyContent: "flex-end" }}>
            <button
              onClick={() => handleDecision("deny")}
              disabled={submitting}
              className="btn btn-deny"
              style={{ minWidth: "140px" }}
            >
              <XCircle size={16} />
              {submitting ? "Processing..." : "Deny Action"}
            </button>

            <button
              onClick={() => handleDecision("approve")}
              disabled={submitting}
              className="btn btn-approve"
              style={{ minWidth: "160px" }}
            >
              <CheckCircle size={16} />
              {submitting ? "Resuming..." : "Approve & Dispatch"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
