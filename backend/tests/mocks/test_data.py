"""Genlock Sentinel — Test Data Mocks and Fixtures.

Provides standard mock drift events, tool outputs, and structured extraction
payloads exactly per Section 9.1 and Section 9.3 of AGENT_MASTER_PLAN.md.
"""

from __future__ import annotations

from typing import Any, Dict

from src.state.schema import (
    ApprovalStatus,
    DiagnosisRecord,
    DriftEvent,
    EvidenceRefs,
    GenlockSentinelState,
    HITLCard,
    RemediationAction,
    RuntimeConfig,
    SessionStatus,
    utc_now_iso,
)
from src.structured_outputs import (
    EvidenceBundleExtraction,
    HITLCardPackage,
    RootCauseDiagnosis,
)

# ------------------------------------------------------------------------------
# Section 9.1: Mock Drift Events
# ------------------------------------------------------------------------------

# 1. Simple Case: Clean network-jitter breach on render-07 (unambiguous)
SIMPLE_CASE_DRIFT_EVENT = DriftEvent(
    event_id="evt-simple-001",
    node_id="render-07",
    frame_id="f-104250",
    sync_offset_us=185.4,
    threshold_us=100.0,
    breach_ts=utc_now_iso(),
    status="detected",
)

# 2. Complex Case: Conflicting evidence (Loki: thermal, Tempo: jitter) on render-12
COMPLEX_CASE_DRIFT_EVENT = DriftEvent(
    event_id="evt-complex-002",
    node_id="render-12",
    frame_id="f-104251",
    sync_offset_us=245.8,
    threshold_us=100.0,
    breach_ts=utc_now_iso(),
    status="detected",
)

# 3. Edge Case: query_loki_logs times out after 3 retries on render-03
EDGE_CASE_DRIFT_EVENT = DriftEvent(
    event_id="evt-edge-003",
    node_id="render-03",
    frame_id="f-104252",
    sync_offset_us=165.2,
    threshold_us=100.0,
    breach_ts=utc_now_iso(),
    status="detected",
)

# 4. Asset Streaming Stall Case on render-04
ASSET_STALL_DRIFT_EVENT = DriftEvent(
    event_id="evt-stall-004",
    node_id="render-04",
    frame_id="f-104253",
    sync_offset_us=310.0,
    threshold_us=100.0,
    breach_ts=utc_now_iso(),
    status="detected",
)

# 5. Thermal Throttle Case on render-09
THERMAL_THROTTLE_DRIFT_EVENT = DriftEvent(
    event_id="evt-thermal-005",
    node_id="render-09",
    frame_id="f-104254",
    sync_offset_us=290.0,
    threshold_us=100.0,
    breach_ts=utc_now_iso(),
    status="detected",
)

# ------------------------------------------------------------------------------
# Section 9.1: Mock Tool Outputs (Raw MCP / Actuator responses)
# ------------------------------------------------------------------------------

MOCK_LOKI_NETWORK_JITTER = {
    "success": True,
    "result": [
        "14:02:10 [cluster-manager] sync handshake retry node=render-07",
        "14:02:11 [LogDisplayClusterEngine] frame drop detected sync_offset_us=185.4 > 100.0",
    ],
    "error": None,
}

MOCK_LOKI_THERMAL_THROTTLE = {
    "success": True,
    "result": [
        "14:02:10 [HardwareMonitor] GPU 0 thermal throttle engaged temp=94C node=render-12",
        "14:02:11 [LogDisplayClusterEngine] clock frequency stepdown detected",
    ],
    "error": None,
}

MOCK_LOKI_ASSET_STALL = {
    "success": True,
    "result": [
        "14:02:10 [TextureStreaming] High-res nanite mipmap paging queue blocked node=render-04",
        "14:02:11 [LogDisplayClusterEngine] render stall texture pool exhaustion",
    ],
    "error": None,
}

MOCK_LOKI_TIMEOUT = {
    "success": False,
    "result": None,
    "error": "Loki query timed out after 3 retries (504 Gateway Timeout)",
}

MOCK_SIFT_FINDINGS = {
    "success": True,
    "result": {
        "investigation_id": "sift-mock-001",
        "findings": [
            {"span": "frame_render", "duration_ms": 340, "service": "render-07"},
        ],
    },
    "error": None,
}

MOCK_TEMPO_TRACE = {
    "success": True,
    "result": {
        "spans": [
            {"service": "render-07", "duration_ms": 340, "status": "ok", "span_id": "span-07-render"},
        ],
    },
    "error": None,
}

MOCK_TEMPO_NETWORK_SPAN = {
    "success": True,
    "result": {
        "spans": [
            {"service": "render-12", "duration_ms": 280, "status": "slow_network_ack", "span_id": "span-12-net"},
        ],
    },
    "error": None,
}

MOCK_FAILOVER_SUCCESS = {
    "success": True,
    "action_taken": "failover_cluster_leadership",
    "timestamp": utc_now_iso(),
    "details": {"node_id": "render-07"},
    "error": None,
}

MOCK_DEPRIORITIZE_SUCCESS = {
    "success": True,
    "action_taken": "deprioritize_texture_streaming",
    "timestamp": utc_now_iso(),
    "details": {"node_id": "render-04"},
    "error": None,
}

MOCK_FORCE_RESYNC_SUCCESS = {
    "success": True,
    "action_taken": "force_genlock_resync",
    "timestamp": utc_now_iso(),
    "details": {"node_id": "render-09"},
    "error": None,
}

MOCK_HALT_TAKE_SUCCESS = {
    "success": True,
    "action_taken": "halt_live_take",
    "timestamp": utc_now_iso(),
    "details": {"card_id": "card-halt-001"},
    "error": None,
}

MOCK_FALLBACK_GREENSCREEN_SUCCESS = {
    "success": True,
    "action_taken": "fallback_to_greenscreen",
    "timestamp": utc_now_iso(),
    "details": {"card_id": "card-green-001"},
    "error": None,
}

MOCK_FAILOVER_THRESHOLD_SUCCESS = {
    "success": True,
    "action_taken": "execute_threshold_exceeding_failover",
    "timestamp": utc_now_iso(),
    "details": {"card_id": "card-failover-001"},
    "error": None,
}

# ------------------------------------------------------------------------------
# Mock Structured Outputs (Pydantic Models)
# ------------------------------------------------------------------------------

MOCK_TRIAGE_SIMPLE = EvidenceBundleExtraction(
    event_id="evt-simple-001",
    logs_available=True,
    log_summary="Sync handshake retry and frame drop detected on render-07 (offset 185.4us > 100.0us)",
    trace_summary="Slow frame_render span duration 340ms on render-07",
    anomaly=None,
)

MOCK_TRIAGE_COMPLEX_CONFLICTING = EvidenceBundleExtraction(
    event_id="evt-complex-002",
    logs_available=True,
    log_summary="Loki indicates GPU thermal throttle (94C) on render-12",
    trace_summary="Tempo indicates network packet drop slow_network_ack (280ms) on render-12",
    anomaly="Conflicting telemetry: Loki logs indicate GPU thermal throttle while Tempo trace indicates slow network transport jitter",
)

MOCK_TRIAGE_EDGE_TIMEOUT = EvidenceBundleExtraction(
    event_id="evt-edge-003",
    logs_available=False,
    log_summary=None,
    trace_summary="Slow frame_render span 340ms on render-03",
    anomaly="Loki query failed after 3 retries: logs_available=false; telemetry gap flag set",
)

MOCK_DIAGNOSIS_SIMPLE = RootCauseDiagnosis(
    event_id="evt-simple-001",
    category="network_jitter",
    confidence=0.94,
    rationale="Verified per query_loki_logs entry 'sync handshake retry node=render-07' and get_trace_by_id span duration 340ms.",
)

MOCK_DIAGNOSIS_COMPLEX_AMBIGUOUS = RootCauseDiagnosis(
    event_id="evt-complex-002",
    category="ambiguous",
    confidence=0.45,
    rationale="Conflicting telemetry: query_loki_logs shows GPU thermal throttle at 94C but get_trace_by_id shows slow_network_ack on transport layer.",
)

MOCK_DIAGNOSIS_ASSET_STALL = RootCauseDiagnosis(
    event_id="evt-stall-004",
    category="asset_streaming_stall",
    confidence=0.92,
    rationale="Verified per query_loki_logs entry 'High-res nanite mipmap paging queue blocked' and render stall on render-04.",
)

MOCK_DIAGNOSIS_THERMAL = RootCauseDiagnosis(
    event_id="evt-thermal-005",
    category="thermal_throttle",
    confidence=0.91,
    rationale="Verified per query_loki_logs entry 'GPU 0 thermal throttle engaged temp=94C node=render-09'.",
)

MOCK_HITL_PACKAGE_HALT = HITLCardPackage(
    event_id="evt-complex-002",
    escalation_reason="ambiguous_diagnosis",
    proposed_action="halt_live_take",
    cost_delta_estimate="$1,850.00 stage burn risk",
    visual_impact_score="Severe sync tear across volume",
    root_cause_summary="Conflicting telemetry: Loki logs show GPU thermal throttle while Tempo traces show network transport stall. Ambiguous diagnosis requires human supervisor arbitration.",
)


def create_initial_test_state(
    session_id: str = "session-eval-001",
    drift_event: DriftEvent = SIMPLE_CASE_DRIFT_EVENT,
) -> GenlockSentinelState:
    """Creates a pristine test state with one active drift event."""
    return GenlockSentinelState(
        session_id=session_id,
        session_status=SessionStatus.MONITORING,
        config=RuntimeConfig(
            sync_offset_threshold_us=100.0,
            financial_threshold_usd=1000.0,
            confidence_floor=0.85,
        ),
        active_drift_events={drift_event.node_id: drift_event},
        evidence_bundle={},
        diagnosis_history=[],
        pending_hitl_card=None,
        approval_state=None,
        remediation_log=[],
        error_logs=[],
    )
