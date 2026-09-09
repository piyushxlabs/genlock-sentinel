"""Unit Tests for Genlock Sentinel State Schema and Reducers.

Verifies the 10-field typed state and deterministic reducers per
AGENT_MASTER_PLAN.md Section 9.2 and AGENT_ORCHESTRATION_BLUEPRINT.md Section 3:
  - Immutable-after-init fields raise on mutation
  - Merge-by-key preserves distinct keys and updates matching keys
  - Append-only never drops entries
  - Last-write-wins resolves deterministically
  - Strict Pydantic V2 schema validation with extra="forbid"
"""

import asyncio
from typing import Any, Dict, List
import pytest
from pydantic import ValidationError

from src.state.reducers import (
    reduce_append_only,
    reduce_immutable,
    reduce_last_write_wins,
    reduce_merge_by_key,
    reduce_state,
    reduce_state_batch,
)
from src.state.schema import (
    ApprovalStatus,
    DiagnosisRecord,
    DriftEvent,
    ErrorRecord,
    EvidenceRefs,
    GenlockSentinelState,
    HITLCard,
    RemediationAction,
    RuntimeConfig,
    SessionStatus,
)
from src.structured_outputs.evidence_bundle_extraction import EvidenceBundleExtraction
from src.structured_outputs.hitl_card_package import HITLCardPackage
from src.structured_outputs.root_cause_diagnosis import RootCauseDiagnosis
from src.utils.errors import StateValidationError


def test_state_initialization_defaults_and_forbid_extra() -> None:
    """GenlockSentinelState initializes cleanly with 10 declared fields and forbids extras."""
    state = GenlockSentinelState(session_id="shoot-stage-01-take-04")

    assert state.session_id == "shoot-stage-01-take-04"
    assert state.session_status == SessionStatus.MONITORING
    assert state.active_drift_events == {}
    assert state.evidence_bundle == {}
    assert state.diagnosis_history == []
    assert state.remediation_log == []
    assert state.pending_hitl_card is None
    assert state.approval_state is None
    assert state.error_logs == []
    assert isinstance(state.config, RuntimeConfig)
    assert state.config.confidence_floor == 0.75
    assert state.config.financial_threshold_usd == 500.0

    # Verify extra="forbid" raises ValidationError
    with pytest.raises(ValidationError):
        GenlockSentinelState(
            session_id="shoot-01",
            unauthorized_field="malicious_payload",  # type: ignore[call-arg]
        )


def test_immutable_after_init_session_id() -> None:
    """session_id must reject any post-initialization mutation attempt."""
    state = GenlockSentinelState(session_id="session-immutable-01")

    # Mutation attempt via reduce_state must raise StateValidationError
    with pytest.raises(StateValidationError) as exc_info:
        reduce_state(state, {"session_id": "session-tampered-02"})
    assert "immutable after initialization" in str(exc_info.value)

    # Identical value re-assertion must succeed
    same_state = reduce_state(state, {"session_id": "session-immutable-01"})
    assert same_state.session_id == "session-immutable-01"


def test_immutable_after_init_config() -> None:
    """config must reject any mid-session modification."""
    state = GenlockSentinelState(session_id="session-config-01")

    # Mutating financial threshold mid-session must be rejected
    with pytest.raises(StateValidationError) as exc_info:
        reduce_state(
            state,
            {"config": RuntimeConfig(financial_threshold_usd=9999.0)},
        )
    assert "immutable after initialization" in str(exc_info.value)

    # Dictionary representation of modified config also raises
    with pytest.raises(StateValidationError):
        reduce_state(
            state,
            {"config": {"financial_threshold_usd": 100.0}},
        )


def test_merge_by_key_active_drift_events() -> None:
    """active_drift_events merge-by-key ensures concurrent node events never collide."""
    state = GenlockSentinelState(session_id="session-drift-01")

    event_node7 = DriftEvent(
        event_id="evt-007",
        node_id="render-07",
        frame_id="f-100",
        breach_ts="2026-09-08T14:00:00Z",
        sync_offset_us=190.5,
    )
    event_node12 = DriftEvent(
        event_id="evt-012",
        node_id="render-12",
        frame_id="f-101",
        breach_ts="2026-09-08T14:00:01Z",
        sync_offset_us=210.0,
    )

    # Add node 7
    s1 = reduce_state(state, {"active_drift_events": {"render-07": event_node7}})
    assert "render-07" in s1.active_drift_events
    assert len(s1.active_drift_events) == 1

    # Add node 12 (must preserve node 7)
    s2 = reduce_state(s1, {"active_drift_events": {"render-12": event_node12}})
    assert "render-07" in s2.active_drift_events
    assert "render-12" in s2.active_drift_events
    assert len(s2.active_drift_events) == 2

    # Update node 7 status to triaged
    event_node7_updated = DriftEvent(
        event_id="evt-007",
        node_id="render-07",
        frame_id="f-100",
        breach_ts="2026-09-08T14:00:00Z",
        sync_offset_us=190.5,
        status="triaged",
    )
    s3 = reduce_state(s2, {"active_drift_events": {"render-07": event_node7_updated}})
    assert s3.active_drift_events["render-07"].status == "triaged"
    assert s3.active_drift_events["render-12"].status == "detected"

    # Remove node 7 via None value (resolution of drift event)
    s4 = reduce_state(s3, {"active_drift_events": {"render-07": None}})
    assert "render-07" not in s4.active_drift_events
    assert "render-12" in s4.active_drift_events
    assert len(s4.active_drift_events) == 1


def test_merge_by_key_evidence_bundle() -> None:
    """evidence_bundle merge-by-key ensures per-event evidence is never cross-overwritten."""
    state = GenlockSentinelState(session_id="session-ev-01")

    ev1 = EvidenceRefs(
        event_id="evt-001",
        node_id="render-07",
        logs_available=True,
        log_summary="handshake timeout",
    )
    ev2 = EvidenceRefs(
        event_id="evt-002",
        node_id="render-12",
        logs_available=False,
        anomaly="timeout on Loki",
    )

    s1 = reduce_state(state, {"evidence_bundle": {"evt-001": ev1}})
    s2 = reduce_state(s1, {"evidence_bundle": {"evt-002": ev2}})

    assert "evt-001" in s2.evidence_bundle
    assert "evt-002" in s2.evidence_bundle
    assert s2.evidence_bundle["evt-001"].logs_available is True
    assert s2.evidence_bundle["evt-002"].logs_available is False


def test_append_only_diagnosis_history() -> None:
    """diagnosis_history preserves chronological audit trail without dropping entries."""
    state = GenlockSentinelState(session_id="session-diag-01")

    diag1 = DiagnosisRecord(
        event_id="evt-001",
        category="network_jitter",
        confidence=0.92,
        rationale="Loki logs confirm sync handshake retry",
    )
    diag2 = DiagnosisRecord(
        event_id="evt-002",
        category="ambiguous",
        confidence=0.40,
        rationale="Conflicting thermal vs network evidence",
    )

    s1 = reduce_state(state, {"diagnosis_history": diag1})
    s2 = reduce_state(s1, {"diagnosis_history": [diag2]})

    assert len(s2.diagnosis_history) == 2
    assert s2.diagnosis_history[0].event_id == "evt-001"
    assert s2.diagnosis_history[1].event_id == "evt-002"


def test_append_only_remediation_and_error_logs() -> None:
    """remediation_log and error_logs strictly append new records."""
    state = GenlockSentinelState(session_id="session-logs-01")

    action = RemediationAction(
        event_id="evt-001",
        node_id="render-07",
        action_taken="failover_cluster_leadership",
        success=True,
    )
    err = ErrorRecord(
        event_id="evt-002",
        error_type="ToolExecutionError",
        message="Loki query timed out",
    )

    s1 = reduce_state(state, {"remediation_log": action, "error_logs": err})
    assert len(s1.remediation_log) == 1
    assert len(s1.error_logs) == 1
    assert s1.remediation_log[0].action_taken == "failover_cluster_leadership"
    assert s1.error_logs[0].error_type == "ToolExecutionError"


def test_last_write_wins_fields() -> None:
    """session_status, pending_hitl_card, and approval_state resolve to latest write."""
    state = GenlockSentinelState(session_id="session-lww-01")

    # Update session status
    s1 = reduce_state(state, {"session_status": SessionStatus.TRIAGING})
    assert s1.session_status == SessionStatus.TRIAGING

    s2 = reduce_state(s1, {"session_status": "awaiting_approval"})
    assert s2.session_status == SessionStatus.AWAITING_APPROVAL

    # Update pending HITL card
    card = HITLCard(
        event_id="evt-002",
        escalation_reason="ambiguous_diagnosis",
        proposed_action="halt_live_take",
        cost_delta_estimate="$1,500/min take hold",
        visual_impact_score="High",
        root_cause_summary="Sync jitter across 3 frames",
    )
    s3 = reduce_state(s2, {"pending_hitl_card": card})
    assert s3.pending_hitl_card is not None
    assert s3.pending_hitl_card.proposed_action == "halt_live_take"

    # Update approval state
    s4 = reduce_state(s3, {"approval_state": ApprovalStatus.APPROVED})
    assert s4.approval_state == ApprovalStatus.APPROVED

    s5 = reduce_state(s4, {"approval_state": "denied", "pending_hitl_card": None})
    assert s5.approval_state == ApprovalStatus.DENIED
    assert s5.pending_hitl_card is None


def test_unauthorized_state_field_rejected() -> None:
    """State deltas with undeclared fields raise StateValidationError."""
    state = GenlockSentinelState(session_id="session-sec-01")

    with pytest.raises(StateValidationError) as exc_info:
        reduce_state(state, {"unauthorized_delta": 42})
    assert "Unauthorized state field 'unauthorized_delta'" in str(exc_info.value)


def test_structured_output_to_state_conversions() -> None:
    """Conversions from Gemini structured outputs to state records maintain schema fidelity."""
    extraction = EvidenceBundleExtraction(
        event_id="evt-555",
        logs_available=True,
        log_summary="Cluster sync retry",
        trace_summary="Slow barrier span 320ms",
        anomaly=None,
    )
    ev_refs = EvidenceRefs.from_extraction(extraction, node_id="render-07")
    assert ev_refs.event_id == "evt-555"
    assert ev_refs.node_id == "render-07"
    assert ev_refs.logs_available is True

    diagnosis = RootCauseDiagnosis(
        event_id="evt-555",
        category="network_jitter",
        confidence=0.95,
        rationale="Handshake timeout verified in logs",
    )
    diag_record = DiagnosisRecord.from_diagnosis(diagnosis, node_id="render-07")
    assert diag_record.category == "network_jitter"
    assert diag_record.confidence == 0.95

    card_pkg = HITLCardPackage(
        event_id="evt-555",
        escalation_reason="threshold_exceeded",
        proposed_action="execute_threshold_exceeding_failover",
        cost_delta_estimate="$5,000 failover cost",
        visual_impact_score="Low",
        root_cause_summary="Primary render node failure",
    )
    hitl_card = HITLCard.from_package(card_pkg, node_id="render-07")
    assert hitl_card.escalation_reason == "threshold_exceeded"
    assert hitl_card.node_id == "render-07"


@pytest.mark.asyncio
async def test_sequential_batch_state_reductions() -> None:
    """Batch reductions sequentially apply a series of deltas."""
    initial = GenlockSentinelState(session_id="batch-session-01")

    deltas = [
        {"session_status": SessionStatus.TRIAGING},
        {
            "active_drift_events": {
                "render-01": DriftEvent(
                    event_id="evt-100",
                    node_id="render-01",
                    frame_id="f-01",
                    breach_ts="2026-09-08T12:00:00Z",
                    sync_offset_us=180.0,
                )
            }
        },
        {
            "active_drift_events": {
                "render-02": DriftEvent(
                    event_id="evt-200",
                    node_id="render-02",
                    frame_id="f-02",
                    breach_ts="2026-09-08T12:00:01Z",
                    sync_offset_us=195.0,
                )
            }
        },
        {"session_status": SessionStatus.CORRELATING},
    ]

    final_state = reduce_state_batch(initial, deltas)
    assert final_state.session_status == SessionStatus.CORRELATING
    assert len(final_state.active_drift_events) == 2
    assert "render-01" in final_state.active_drift_events
    assert "render-02" in final_state.active_drift_events
