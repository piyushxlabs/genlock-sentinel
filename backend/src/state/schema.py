"""Genlock Sentinel — Type-Safe Central State Schema.

Defines GenlockSentinelState and its child Pydantic V2 models exactly per
AGENT_ORCHESTRATION_BLUEPRINT.md Section 3 and AGENT_LOGIC_SPEC.md.
All models use strict validation with extra="forbid".
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.structured_outputs.evidence_bundle_extraction import EvidenceBundleExtraction
from src.structured_outputs.hitl_card_package import HITLCardPackage
from src.structured_outputs.root_cause_diagnosis import RootCauseDiagnosis


def utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------------------
# State Enums
# ------------------------------------------------------------------------------

class SessionStatus(str, Enum):
    """Lifecycle status of the agent session or active cycle."""

    MONITORING = "monitoring"
    TRIAGING = "triaging"
    CORRELATING = "correlating"
    REMEDIATING = "remediating"
    AWAITING_APPROVAL = "awaiting_approval"
    RESUMED = "resumed"
    STOPPED = "stopped"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    """Supervisor approval status for HITL operations."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    HALTED = "halted"


# ------------------------------------------------------------------------------
# Child Models
# ------------------------------------------------------------------------------

class DriftEvent(BaseModel):
    """Active genlock sync-offset breach event detected by Stream Watch."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(..., description="Unique drift event identifier")
    node_id: str = Field(..., description="Target cluster render node (e.g. render-07)")
    frame_id: str = Field(..., description="Active camera frame ID (e.g. f-88213)")
    breach_ts: str = Field(..., description="ISO 8601 UTC timestamp of threshold breach")
    sync_offset_us: float = Field(..., description="Sync offset in microseconds")
    threshold_us: float = Field(default=150.0, description="Breach threshold in microseconds")
    status: Literal["detected", "triaged", "diagnosed", "remediated", "escalated", "resolved"] = Field(
        default="detected", description="Lifecycle status of this drift event"
    )


class EvidenceRefs(BaseModel):
    """Structured telemetry evidence bundle collected by Evidence Triage."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(..., description="Associated drift event identifier")
    node_id: Optional[str] = Field(default=None, description="Target render node ID")
    logs_available: bool = Field(default=True, description="Whether Loki logs were successfully queried")
    log_summary: Optional[str] = Field(default=None, description="Factual summary of Loki log lines")
    trace_summary: Optional[str] = Field(default=None, description="Factual summary of Tempo trace spans")
    anomaly: Optional[str] = Field(default=None, description="Any detected anomalies or query failures")
    timestamp: str = Field(default_factory=utc_now_iso, description="ISO 8601 UTC timestamp of evidence creation")
    raw_refs: Dict[str, Any] = Field(default_factory=dict, description="Pointers to trace IDs or log queries")

    @classmethod
    def from_extraction(
        cls,
        extraction: EvidenceBundleExtraction,
        node_id: Optional[str] = None,
        raw_refs: Optional[Dict[str, Any]] = None,
    ) -> EvidenceRefs:
        """Constructs an EvidenceRefs instance from an EvidenceBundleExtraction structured output."""
        return cls(
            event_id=extraction.event_id,
            node_id=node_id,
            logs_available=extraction.logs_available,
            log_summary=extraction.log_summary,
            trace_summary=extraction.trace_summary,
            anomaly=extraction.anomaly,
            timestamp=utc_now_iso(),
            raw_refs=raw_refs or {},
        )


class DiagnosisRecord(BaseModel):
    """Diagnostic correlation record produced by Root-Cause Correlation."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(..., description="Associated drift event identifier")
    node_id: Optional[str] = Field(default=None, description="Target render node ID")
    category: Literal["network_jitter", "thermal_throttle", "asset_streaming_stall", "ambiguous"] = Field(
        ..., description="Diagnosed root-cause category"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    rationale: str = Field(..., description="Evidence-grounded rationale citing logs, traces, or metrics")
    timestamp: str = Field(default_factory=utc_now_iso, description="ISO 8601 UTC timestamp of diagnosis")

    @classmethod
    def from_diagnosis(
        cls,
        diagnosis: RootCauseDiagnosis,
        node_id: Optional[str] = None,
    ) -> DiagnosisRecord:
        """Constructs a DiagnosisRecord from a RootCauseDiagnosis structured output."""
        return cls(
            event_id=diagnosis.event_id,
            node_id=node_id,
            category=diagnosis.category,
            confidence=diagnosis.confidence,
            rationale=diagnosis.rationale,
            timestamp=utc_now_iso(),
        )


class RemediationAction(BaseModel):
    """Record of an autonomous or HITL-approved remediation tool execution."""

    model_config = ConfigDict(strict=True, extra="forbid")

    action_id: str = Field(default_factory=lambda: f"act-{uuid4().hex[:8]}", description="Unique action ID")
    event_id: str = Field(..., description="Associated drift event identifier")
    node_id: Optional[str] = Field(default=None, description="Target render node ID")
    action_taken: str = Field(..., description="Name of the remediation tool executed")
    timestamp: str = Field(default_factory=utc_now_iso, description="ISO 8601 UTC timestamp of execution")
    success: bool = Field(..., description="Whether the remediation succeeded")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed tool output or metrics")


class HITLCard(BaseModel):
    """Structured package presented to supervisor for HITL approval."""

    model_config = ConfigDict(strict=True, extra="forbid")

    card_id: str = Field(default_factory=lambda: f"hitl-{uuid4().hex[:8]}", description="Unique card ID")
    event_id: str = Field(..., description="Associated drift event identifier")
    node_id: Optional[str] = Field(default=None, description="Target render node ID")
    escalation_reason: Literal[
        "ambiguous_diagnosis",
        "take_halt_required",
        "capture_fallback_required",
        "threshold_exceeded",
    ] = Field(..., description="Specific escalation trigger reason")
    proposed_action: str = Field(..., description="Tool or action requiring sign-off")
    cost_delta_estimate: str = Field(..., description="Estimated cost or financial delta")
    visual_impact_score: str = Field(..., description="Assessed impact on the recorded image")
    root_cause_summary: str = Field(..., description="Plain-language summary of root cause")
    created_at: str = Field(default_factory=utc_now_iso, description="ISO 8601 UTC creation timestamp")

    @classmethod
    def from_package(
        cls,
        package: HITLCardPackage,
        card_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> HITLCard:
        """Constructs a HITLCard from a HITLCardPackage structured output."""
        return cls(
            card_id=card_id or f"hitl-{uuid4().hex[:8]}",
            event_id=package.event_id,
            node_id=node_id,
            escalation_reason=package.escalation_reason,
            proposed_action=package.proposed_action,
            cost_delta_estimate=package.cost_delta_estimate,
            visual_impact_score=package.visual_impact_score,
            root_cause_summary=package.root_cause_summary,
            created_at=utc_now_iso(),
        )


class ErrorRecord(BaseModel):
    """Structured diagnostic error record appended to state error logs."""

    model_config = ConfigDict(strict=True, extra="forbid")

    error_id: str = Field(default_factory=lambda: f"err-{uuid4().hex[:8]}", description="Unique error identifier")
    event_id: Optional[str] = Field(default=None, description="Associated drift event ID if applicable")
    node_id: Optional[str] = Field(default=None, description="Associated cluster render node if applicable")
    error_type: str = Field(..., description="Classification of the error (e.g. ToolExecutionError)")
    message: str = Field(..., description="Descriptive error message")
    timestamp: str = Field(default_factory=utc_now_iso, description="ISO 8601 UTC timestamp of error occurrence")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Contextual diagnostic payload")


class RuntimeConfig(BaseModel):
    """Runtime configuration thresholds locked at session start."""

    model_config = ConfigDict(strict=True, extra="forbid")

    confidence_floor: float = Field(default=0.75, ge=0.0, le=1.0, description="Confidence floor for autonomy")
    financial_threshold_usd: float = Field(default=500.0, ge=0.0, description="Max spend allowed without HITL")
    query_window_max_seconds: int = Field(default=120, gt=0, description="Max lookback window for Loki/Tempo")
    max_tool_retries: int = Field(default=3, ge=1, le=5, description="Maximum retry attempts with backoff")
    sync_offset_threshold_us: float = Field(default=150.0, gt=0.0, description="Sync-offset drift threshold")


# ------------------------------------------------------------------------------
# Central State Schema (GenlockSentinelState)
# ------------------------------------------------------------------------------

class GenlockSentinelState(BaseModel):
    """The authoritative 10-field typed state for Genlock Sentinel.

    Defined in AGENT_ORCHESTRATION_BLUEPRINT.md Section 3:
      1. session_id: str                                    (immutable-after-init)
      2. session_status: SessionStatus                      (last-write-wins)
      3. active_drift_events: dict[str, DriftEvent]         (merge-by-key, keyed by node_id)
      4. evidence_bundle: dict[str, EvidenceRefs]           (merge-by-key, keyed by event_id)
      5. diagnosis_history: list[DiagnosisRecord]           (append-only)
      6. remediation_log: list[RemediationAction]           (append-only)
      7. pending_hitl_card: Optional[HITLCard]              (last-write-wins)
      8. approval_state: Optional[ApprovalStatus]           (last-write-wins)
      9. error_logs: list[ErrorRecord]                      (append-only)
      10. config: RuntimeConfig                             (immutable-after-init)
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    session_id: str = Field(..., description="Unique shoot session identifier (immutable)")
    session_status: SessionStatus = Field(
        default=SessionStatus.MONITORING, description="Current lifecycle phase (last-write-wins)"
    )
    active_drift_events: Dict[str, DriftEvent] = Field(
        default_factory=dict, description="Per-node active drift events (merge-by-key on node_id)"
    )
    evidence_bundle: Dict[str, EvidenceRefs] = Field(
        default_factory=dict, description="Per-event evidence bundles (merge-by-key on event_id)"
    )
    diagnosis_history: List[DiagnosisRecord] = Field(
        default_factory=list, description="Audit trail of all diagnoses (append-only)"
    )
    remediation_log: List[RemediationAction] = Field(
        default_factory=list, description="Audit trail of all remediation executions (append-only)"
    )
    pending_hitl_card: Optional[HITLCard] = Field(
        default=None, description="Currently active HITL approval card (last-write-wins)"
    )
    approval_state: Optional[ApprovalStatus] = Field(
        default=None, description="Supervisor approval resolution state (last-write-wins)"
    )
    error_logs: List[ErrorRecord] = Field(
        default_factory=list, description="Audit trail of all diagnostic errors (append-only)"
    )
    config: RuntimeConfig = Field(
        default_factory=RuntimeConfig, description="Locked session configuration (immutable)"
    )

    @field_validator("session_status", mode="before")
    @classmethod
    def _coerce_session_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            return SessionStatus(v)
        return v

    @field_validator("approval_state", mode="before")
    @classmethod
    def _coerce_approval_state(cls, v: Any) -> Any:
        if isinstance(v, str):
            return ApprovalStatus(v)
        return v
