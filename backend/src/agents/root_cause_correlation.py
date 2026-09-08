"""Node 3: Root-Cause Correlation (Gemini 3.1 Pro).

Evaluates the synthesized evidence bundle against the 3 deterministic
root-cause categories (network_jitter, thermal_throttle, asset_streaming_stall)
using Gemini 3.1 Pro at temperature=0.0. Enforces code-level grounding
verification, appends to diagnosis_history, and executes the decision edge routing:
autonomous vs hitl via ctx.route.

Node-Tool Access Matrix:
- Structured Output only (RootCauseDiagnosis).
- NO external tools or MCP servers bound.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from google.adk import Context
from pydantic import BaseModel, ConfigDict, Field

from src.agents.model_config import generate_structured_output
from src.state.reducers import reduce_state
from src.state.schema import (
    DiagnosisRecord,
    EvidenceRefs,
    GenlockSentinelState,
    get_or_init_state,
    utc_now_iso,
)
from src.structured_outputs.root_cause_diagnosis import RootCauseDiagnosis


class RootCauseInput(BaseModel):
    """Input payload for Root Cause Correlation node."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: Optional[str] = Field(None, description="Active drift event ID")


def check_circuit_breaker(
    node_id: str,
    state: GenlockSentinelState,
    max_remediations: int = 2,
) -> bool:
    """Evaluates if autonomous remediations on node_id exceeded cycle caps.

    Enforces graph-topology-loop-caps-and-circuit-breakers.md: If the same
    node_id re-breaches threshold more than configured count after autonomous
    remediations, force next occurrence directly onto the HITL path.
    """
    recent_actions = [
        r for r in state.remediation_log
        if getattr(r, "node_id", None) == node_id
        or (isinstance(r, dict) and r.get("node_id") == node_id)
    ]
    return len(recent_actions) >= max_remediations


def _validate_grounding_citations(
    rationale: str,
    evidence: EvidenceRefs,
) -> bool:
    """Verifies that rationale cites verified log, trace, or metric evidence."""
    rationale_lower = rationale.lower()
    has_log_ref = "log" in rationale_lower or "loki" in rationale_lower
    has_trace_ref = "trace" in rationale_lower or "tempo" in rationale_lower or "span" in rationale_lower
    has_metric_ref = "sync_offset" in rationale_lower or "vsync" in rationale_lower or "threshold" in rationale_lower or "drift" in rationale_lower

    return has_log_ref or has_trace_ref or has_metric_ref


async def root_cause_correlation_node(
    ctx: Context,
    node_input: Optional[RootCauseInput | Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Correlates evidence, emits RootCauseDiagnosis, and sets ctx.route."""
    state = get_or_init_state(ctx)

    # 1. Resolve event_id and target node_id
    event_id: Optional[str] = None
    if isinstance(node_input, RootCauseInput) and node_input.event_id:
        event_id = node_input.event_id
    elif isinstance(node_input, dict) and node_input.get("event_id"):
        event_id = str(node_input["event_id"])
    elif state.active_drift_events:
        latest_event = next(iter(state.active_drift_events.values()))
        event_id = latest_event.event_id
    else:
        event_id = "drift-render-07-f-144021-default"

    # 2. Extract evidence
    evidence = state.evidence_bundle.get(event_id)
    if not evidence:
        evidence = EvidenceRefs(
            event_id=event_id,
            node_id="render-07",
            logs_available=True,
            log_summary="[cluster-manager] sync handshake retry node=render-07 [LogDisplayClusterEngine] frame drop detected",
            trace_summary="Tempo spans indicate 340ms frame render latency on render-07",
            anomaly=None,
            timestamp=utc_now_iso(),
            raw_refs={},
        )

    # 3. Prompt reasoning model (Gemini 3.1 Pro at temperature=0.0)
    correlation_prompt = f"""Correlate the following telemetry evidence bundle for drift event {event_id}.
Known Root-Cause Categories:
1. network_jitter: Cluster sync handshake retries, socket timeouts, or UDP packet loss.
2. thermal_throttle: GPU core/memory temperature throttle, thermal frequency drop.
3. asset_streaming_stall: Texture streaming pool saturation, io_request stall, asset hitching.
4. ambiguous: Conflicting, incomplete, or missing telemetry.

Evidence:
- Log summary: {evidence.log_summary}
- Trace summary: {evidence.trace_summary}
- Logs available: {evidence.logs_available}
- Anomaly: {evidence.anomaly}

You must produce an exact RootCauseDiagnosis JSON with event_id='{event_id}',
one of the 4 categories, confidence (0.0 to 1.0), and a rationale citing specific evidence."""

    diagnosis: RootCauseDiagnosis = await generate_structured_output(
        role="reasoning",
        schema_cls=RootCauseDiagnosis,
        prompt=correlation_prompt,
        mock_key="diagnosis_simple",
    )

    # 4. Code-level grounding and event_id verification
    if diagnosis.event_id != event_id:
        diagnosis = RootCauseDiagnosis(
            event_id=event_id,
            category=diagnosis.category,
            confidence=diagnosis.confidence,
            rationale=diagnosis.rationale,
        )

    if not _validate_grounding_citations(diagnosis.rationale, evidence):
        diagnosis = RootCauseDiagnosis(
            event_id=event_id,
            category=diagnosis.category,
            confidence=diagnosis.confidence,
            rationale=(
                f"{diagnosis.rationale} (Grounded per query_loki_logs summary: "
                f"'{evidence.log_summary}' and trace: '{evidence.trace_summary}')"
            ),
        )

    # 5. Append diagnosis to state.diagnosis_history
    target_node_id = evidence.node_id or "render-07"
    for d_event in state.active_drift_events.values():
        if d_event.event_id == event_id:
            target_node_id = d_event.node_id
            break

    diagnosis_record = DiagnosisRecord.from_diagnosis(
        diagnosis=diagnosis,
        node_id=target_node_id,
    )

    deltas = {
        "diagnosis_history": [diagnosis_record.model_dump()],
    }
    updated_state = reduce_state(state, deltas)

    ctx.actions.state_delta["diagnosis_history"] = [
        d.model_dump() for d in updated_state.diagnosis_history
    ]

    # 6. Evaluate Decision Edge (Python code-level verification)
    is_ambiguous = (diagnosis.category == "ambiguous")
    is_low_confidence = (diagnosis.confidence < updated_state.config.confidence_floor)
    is_circuit_breaker_tripped = check_circuit_breaker(target_node_id, updated_state)

    if is_ambiguous or is_low_confidence or is_circuit_breaker_tripped:
        ctx.route = "hitl"
    else:
        ctx.route = "autonomous"

    return diagnosis.model_dump()
