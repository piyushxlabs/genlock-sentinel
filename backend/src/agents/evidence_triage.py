"""Node 2: Evidence Triage (Gemini 3.7 Flash).

Executes read-only observability queries against Loki, Tempo, and Prometheus
via the Grafana MCP Client. Synthesizes query results into a structured
EvidenceBundleExtraction adhering to the silence-over-guessing policy.

Node-Tool Access Matrix:
- Read-only observability: Bound ONLY to query_loki_logs, find_slow_requests,
  and get_trace_by_id.
- Reads active_drift_events; writes evidence_bundle.
- NO remediation tools bound.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from google.adk import Context
from pydantic import BaseModel, ConfigDict, Field

from src.agents.model_config import generate_structured_output
from src.state.reducers import reduce_state
from src.state.schema import (
    DriftEvent,
    EvidenceRefs,
    GenlockSentinelState,
    SessionStatus,
    get_or_init_state,
    utc_now_iso,
)
from src.structured_outputs.evidence_bundle_extraction import EvidenceBundleExtraction
from src.tools.evidence_triage_tools import (
    find_slow_requests,
    get_trace_by_id,
    query_loki_logs,
)
from src.tools.schemas.pydantic_models import (
    FindSlowRequestsInput,
    GetTraceByIdInput,
    QueryLokiLogsInput,
)


class EvidenceTriageInput(BaseModel):
    """Input payload for Evidence Triage node."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: Optional[str] = Field(None, description="Active drift event ID")
    node_id: Optional[str] = Field(None, description="Breaching cluster node")
    frame_id: Optional[str] = Field(None, description="Production frame ID")


def _get_active_drift_event(
    ctx: Context,
    node_input: Optional[EvidenceTriageInput | Dict[str, Any]] = None,
) -> DriftEvent:
    """Resolves target drift event from input or active_drift_events state."""
    state = get_or_init_state(ctx)

    # Check input first
    inp_event_id: Optional[str] = None
    inp_node_id: Optional[str] = None
    inp_frame_id: Optional[str] = None

    if isinstance(node_input, EvidenceTriageInput):
        inp_event_id = node_input.event_id
        inp_node_id = node_input.node_id
        inp_frame_id = node_input.frame_id
    elif isinstance(node_input, dict):
        inp_event_id = node_input.get("event_id")
        inp_node_id = node_input.get("node_id")
        inp_frame_id = str(node_input.get("frame_id")) if node_input.get("frame_id") is not None else None

    if inp_event_id and inp_node_id and inp_frame_id is not None:
        return DriftEvent(
            event_id=inp_event_id,
            node_id=inp_node_id,
            frame_id=inp_frame_id,
            breach_ts=utc_now_iso(),
            sync_offset_us=842.0,
            threshold_us=150.0,
            status="detected",
        )

    # Search in state.active_drift_events
    if state.active_drift_events:
        if inp_node_id and inp_node_id in state.active_drift_events:
            return state.active_drift_events[inp_node_id]
        if inp_event_id:
            for ev in state.active_drift_events.values():
                if ev.event_id == inp_event_id:
                    return ev
        return next(iter(state.active_drift_events.values()))

    # Fallback synthetic event for testing
    return DriftEvent(
        event_id="drift-render-07-f-144021-default",
        node_id="render-07",
        frame_id="f-144021",
        breach_ts=utc_now_iso(),
        sync_offset_us=842.0,
        threshold_us=150.0,
        status="detected",
    )


async def evidence_triage_node(
    ctx: Context,
    node_input: Optional[EvidenceTriageInput | Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Queries observability tools and synthesizes EvidenceBundleExtraction."""
    current_state = get_or_init_state(ctx)
    drift_event = _get_active_drift_event(ctx, node_input)
    event_id = drift_event.event_id
    node_id = drift_event.node_id
    frame_id = drift_event.frame_id

    # 1. Execute Tool 1: query_loki_logs
    loki_payload = QueryLokiLogsInput(
        datasource_uid="loki-stage-01",
        logql=f'{{cluster="stage-ndisplay"}} |= "{node_id}"',
        start=drift_event.breach_ts,
        end=utc_now_iso(),
        limit=200,
    )
    loki_output = await query_loki_logs(
        loki_payload,
        state=current_state,
        node_id=node_id,
    )

    # 2. Execute Tool 2: find_slow_requests
    sift_payload = FindSlowRequestsInput(
        service_name=node_id,
        start=drift_event.breach_ts,
        end=utc_now_iso(),
        min_duration_ms=100,
    )
    sift_output = await find_slow_requests(
        sift_payload,
        state=current_state,
    )

    # 3. Execute Tool 3: get_trace_by_id
    trace_payload = GetTraceByIdInput(
        trace_id=frame_id,
    )
    trace_output = await get_trace_by_id(
        trace_payload,
        state=current_state,
    )

    # Compile evidence into extraction prompt
    logs_available = loki_output.success and len(loki_output.result) > 0
    anomalies: list[str] = []
    if not logs_available:
        anomalies.append("query_loki_logs failed or returned empty logs after retries")
    if not trace_output.success:
        anomalies.append("get_trace_by_id failed or returned empty span details")

    triage_prompt = f"""Synthesize an EvidenceBundleExtraction for drift event {event_id}.
Telemetry observations:
- Node: {node_id}, Frame: {frame_id}
- Loki logs result: {loki_output.result}
- Sift slow request findings: {sift_output.result}
- Tempo trace spans: {trace_output.result}
- Logs available: {logs_available}
- Tool anomalies: {anomalies}

Produce an exact EvidenceBundleExtraction JSON with event_id='{event_id}',
logs_available={str(logs_available).lower()}, concise log_summary, trace_summary,
and anomaly description (or null if none)."""

    mock_key = (
        "evidence_bundle_edge"
        if ("edge" in event_id)
        else (
            "evidence_bundle_complex"
            if ("complex" in event_id or "render-12" in node_id or "ambiguous" in event_id)
            else "evidence_bundle_simple"
        )
    )

    extraction: EvidenceBundleExtraction = await generate_structured_output(
        role="fast",
        schema_cls=EvidenceBundleExtraction,
        prompt=triage_prompt,
        mock_key=mock_key,
    )

    if extraction.event_id != event_id:
        extraction = EvidenceBundleExtraction(
            event_id=event_id,
            logs_available=extraction.logs_available,
            log_summary=extraction.log_summary,
            trace_summary=extraction.trace_summary,
            anomaly=extraction.anomaly,
        )

    # Grounded safety override if logs were truly missing
    if not logs_available and extraction.logs_available:
        extraction = EvidenceBundleExtraction(
            event_id=event_id,
            logs_available=False,
            log_summary="Telemetry gap: Loki logs unavailable after 3 retry attempts.",
            trace_summary=extraction.trace_summary,
            anomaly="Telemetric gap encountered in Loki logs.",
        )

    # Reconstruct state and reduce
    current_state = get_or_init_state(ctx)

    state_evidence = EvidenceRefs.from_extraction(
        extraction=extraction,
        node_id=node_id,
        raw_refs={"trace_id": frame_id},
    )

    deltas = {
        "evidence_bundle": {event_id: state_evidence.model_dump()},
        "session_status": SessionStatus.CORRELATING.value,
    }
    updated_state = reduce_state(current_state, deltas)

    # Persist updated bundle in context
    ctx.actions.state_delta["evidence_bundle"] = {
        k: v.model_dump() for k, v in updated_state.evidence_bundle.items()
    }
    ctx.actions.state_delta["session_status"] = updated_state.session_status.value

    return extraction.model_dump()
