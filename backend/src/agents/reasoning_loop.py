"""Genlock Sentinel — Multi-Step Reasoning Loop Coordinator.

Coordinates Evidence Triage and Root-Cause Correlation with strict:
1. Cycle cap enforcement (exactly 1 diagnostic and remediation pass per event_id).
2. Code-level grounding and citation verification.
3. Silence-over-guessing telemetry gap handling.
4. Untrusted telemetry prompt injection sanitization (OWASP LLM01).
5. Circuit breaker escalation to HITL.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Literal, Optional, Set

from google.adk.agents.context import Context
from pydantic import BaseModel, ConfigDict, Field

from src.agents.autonomous_dispatch import autonomous_dispatch_node
from src.agents.evidence_triage import evidence_triage_node
from src.agents.hitl_card_generation import hitl_card_generation_node
from src.agents.root_cause_correlation import (
    check_circuit_breaker,
    root_cause_correlation_node,
)
from src.state.checkpointing import save_checkpoint
from src.state.reducers import reduce_state
from src.state.schema import (
    ApprovalStatus,
    DiagnosisRecord,
    DriftEvent,
    EvidenceRefs,
    GenlockSentinelState,
    HITLCard,
    RemediationAction,
    SessionStatus,
    get_or_init_state,
    utc_now_iso,
)
from src.telemetry.tracing import (
    annotate_circuit_breaker,
    event_span,
    mark_span_error,
    mark_span_ok,
    node_span,
)
from src.ui.agui_bridge import get_event_bridge
from src.ui.hitl_resumption import get_hitl_coordinator
from src.utils.errors import AgentError, StateValidationError, ToolExecutionError

# In-flight and processed event trackers to enforce the strict 1-pass cycle cap
_PROCESSED_EVENT_IDS: Set[str] = set()
_IN_FLIGHT_EVENT_IDS: Set[str] = set()

# Prompt-injection pattern screening for untrusted telemetry
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+|previous\s+|prior\s+)*instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*override", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"admin\s+override", re.IGNORECASE),
    re.compile(r"approve\s+all\s+actions", re.IGNORECASE),
]


class ReasoningLoopResult(BaseModel):
    """Execution summary for a single-event reasoning loop pass."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str
    node_id: str
    status: Literal["remediated", "awaiting_approval", "ambiguous_escalated", "failed"]
    triage_bundle: Optional[Dict[str, Any]] = None
    diagnosis: Optional[Dict[str, Any]] = None
    remediation: Optional[Dict[str, Any]] = None
    hitl_card: Optional[Dict[str, Any]] = None
    iterations: int = 1
    error: Optional[str] = None


def sanitize_telemetry_input(text: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Screens untrusted telemetry data for instruction-injection attempts (OWASP LLM01).

    Returns (sanitized_text, anomaly_warning).
    """
    if not text:
        return None, None

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            warning = f"Prompt-injection attempt detected and neutralized: matched pattern '{pattern.pattern}'"
            sanitized = pattern.sub("[SUSPICIOUS_INSTRUCTION_REDACTED]", text)
            return sanitized, warning

    return text, None


def reset_reasoning_loop_trackers() -> None:
    """Resets global cycle cap tracking sets for testing environments."""
    _PROCESSED_EVENT_IDS.clear()
    _IN_FLIGHT_EVENT_IDS.clear()


async def run_reasoning_loop(
    ctx: Context,
    event_id: str,
    max_iterations: int = 1,
) -> ReasoningLoopResult:
    """Executes the complete reasoning loop for a drift event adhering to Step 12 specifications.

    Enforces:
    1. Cycle cap: exactly ONE diagnostic and remediation pass per event_id.
    2. Zero ungrounded claims (silence-over-guessing).
    3. Pure Python decision edge routing.
    """
    # --------------------------------------------------------------------------
    # 1. Cycle Cap & Re-entry Validation
    # --------------------------------------------------------------------------
    if event_id in _IN_FLIGHT_EVENT_IDS:
        raise StateValidationError(
            f"Event {event_id} is already in flight. Concurrent diagnostic loops forbidden."
        )
    if event_id in _PROCESSED_EVENT_IDS:
        raise StateValidationError(
            f"Event {event_id} has already completed a reasoning pass. Max iterations = 1 exceeded."
        )

    _IN_FLIGHT_EVENT_IDS.add(event_id)

    try:
        current_state = get_or_init_state(ctx)
        session_id: str = current_state.session_id or "session-unknown"

        # Locate the active drift event
        target_drift: Optional[DriftEvent] = None
        for d in current_state.active_drift_events.values():
            if d.event_id == event_id:
                target_drift = d
                break

        if target_drift is None:
            raise StateValidationError(
                f"No active drift event found in state for event_id='{event_id}'."
            )

        node_id = target_drift.node_id
        bridge = get_event_bridge()

        with event_span(session_id=session_id, event_id=event_id, node_id=node_id) as evt_span:
            # ------------------------------------------------------------------
            # 2. Node 2: Evidence Triage Pass
            # ------------------------------------------------------------------
            await bridge.emit_step_started(
                session_id=session_id,
                step_name="evidence_triage",
                event_id=event_id,
            )
            with node_span(
                node_name="evidence_triage",
                model="gemini-3.7-flash",
                session_id=session_id,
                event_id=event_id,
            ):
                triage_output = await evidence_triage_node(ctx, {"event_id": event_id, "node_id": node_id})

            # Screen extracted telemetry for instruction-injection attempts
            log_summary, log_anomaly = sanitize_telemetry_input(triage_output.get("log_summary"))
            trace_summary, trace_anomaly = sanitize_telemetry_input(triage_output.get("trace_summary"))

            anomalies = []
            if triage_output.get("anomaly"):
                anomalies.append(str(triage_output["anomaly"]))
            if log_anomaly:
                anomalies.append(log_anomaly)
            if trace_anomaly:
                anomalies.append(trace_anomaly)

            triage_bundle = {
                "event_id": event_id,
                "logs_available": triage_output.get("logs_available", False),
                "log_summary": log_summary,
                "trace_summary": trace_summary,
                "anomaly": "; ".join(anomalies) if anomalies else None,
            }

            # Emit tool call lifecycle events for query_loki_logs & find_slow_requests
            await bridge.emit_tool_call_lifecycle(
                session_id=session_id,
                tool_call_id=f"call-loki-{event_id}",
                tool_name="query_loki_logs",
                args={"node_id": node_id, "cluster": "stage-ndisplay"},
                result={"logs_available": triage_bundle["logs_available"], "log_summary": log_summary or ""},
            )
            await bridge.emit_tool_call_lifecycle(
                session_id=session_id,
                tool_call_id=f"call-tempo-{event_id}",
                tool_name="find_slow_requests",
                args={"service_name": node_id, "min_duration_ms": 100},
                result={"trace_summary": trace_summary or ""},
            )
            await bridge.emit_step_finished(
                session_id=session_id,
                step_name="evidence_triage",
                event_id=event_id,
            )
            await bridge.broadcast_event(
                session_id,
                bridge.build_state_delta(
                    field_name="evidence_bundle",
                    reducer_type="merge-by-key",
                    value=triage_bundle,
                    key=event_id,
                ),
            )

            # ------------------------------------------------------------------
            # 3. Node 3: Root-Cause Correlation Pass
            # ------------------------------------------------------------------
            await bridge.emit_step_started(
                session_id=session_id,
                step_name="root_cause_correlation",
                event_id=event_id,
            )
            with node_span(
                node_name="root_cause_correlation",
                model="gemini-3.1-pro",
                session_id=session_id,
                event_id=event_id,
            ):
                diagnosis_output = await root_cause_correlation_node(ctx, {"event_id": event_id})

            # Stream Gemini 3.1 Pro reasoning tokens to live console
            rationale_str = diagnosis_output.get("rationale", "")
            if rationale_str:
                tokens = [w + " " for w in rationale_str.split(" ") if w]
                await bridge.emit_reasoning_stream(
                    session_id=session_id,
                    message_id=f"reasoning-{event_id}",
                    deltas=tokens,
                )

            await bridge.emit_step_finished(
                session_id=session_id,
                step_name="root_cause_correlation",
                event_id=event_id,
            )
            curr_state_diag = get_or_init_state(ctx)
            latest_diag = curr_state_diag.diagnosis_history[-1] if curr_state_diag.diagnosis_history else diagnosis_output
            await bridge.broadcast_event(
                session_id,
                bridge.build_state_delta(
                    field_name="diagnosis_history",
                    reducer_type="append-only",
                    value=latest_diag,
                ),
            )

            # Evaluate decision routing set by Node 3 (ctx.route)
            route = getattr(ctx, "route", None)
            if not route:
                # Recompute decision edge deterministically if route was unset
                is_ambiguous = diagnosis_output.get("category") == "ambiguous"
                is_low_conf = float(diagnosis_output.get("confidence", 0.0)) < current_state.config.confidence_floor
                is_breaker = check_circuit_breaker(node_id, get_or_init_state(ctx))
                if is_breaker:
                    annotate_circuit_breaker(evt_span, node_id)
                route = "hitl" if (is_ambiguous or is_low_conf or is_breaker) else "autonomous"

            # ------------------------------------------------------------------
            # 4. Routing: Autonomous Remediation vs HITL Escalation
            # ------------------------------------------------------------------
            if route == "autonomous":
                # Step 5a: Autonomous Dispatch
                await bridge.emit_step_started(
                    session_id=session_id,
                    step_name="autonomous_dispatch",
                    event_id=event_id,
                )
                with node_span(
                    node_name="autonomous_dispatch",
                    session_id=session_id,
                    event_id=event_id,
                ):
                    dispatch_output = await autonomous_dispatch_node(ctx)

                action_name = dispatch_output.get("action_taken", "remediation_actuator")
                await bridge.emit_tool_call_lifecycle(
                    session_id=session_id,
                    tool_call_id=f"call-actuator-{event_id}",
                    tool_name=action_name,
                    args={"node_id": node_id, "event_id": event_id},
                    result=dispatch_output,
                )
                await bridge.emit_step_finished(
                    session_id=session_id,
                    step_name="autonomous_dispatch",
                    event_id=event_id,
                )

                st_now = get_or_init_state(ctx)
                if st_now.remediation_log:
                    await bridge.broadcast_event(
                        session_id,
                        bridge.build_state_delta(
                            field_name="remediation_log",
                            reducer_type="append-only",
                            value=st_now.remediation_log[-1],
                        ),
                    )
                await bridge.emit_run_finished(session_id=session_id, run_id=f"run-{event_id}")
                await save_checkpoint(session_id=session_id, state=st_now)

                _PROCESSED_EVENT_IDS.add(event_id)
                mark_span_ok(evt_span, "remediated")
                return ReasoningLoopResult(
                    event_id=event_id,
                    node_id=node_id,
                    status="remediated",
                    triage_bundle=triage_bundle,
                    diagnosis=diagnosis_output,
                    remediation=dispatch_output,
                    hitl_card=None,
                    iterations=1,
                )
            else:
                # Step 5b: HITL Card Generation & Pause
                await bridge.emit_step_started(
                    session_id=session_id,
                    step_name="hitl_card_generation",
                    event_id=event_id,
                )
                with node_span(
                    node_name="hitl_card_generation",
                    model="gemini-3.7-flash",
                    session_id=session_id,
                    event_id=event_id,
                ):
                    card_output = await hitl_card_generation_node(ctx)

                await bridge.emit_step_finished(
                    session_id=session_id,
                    step_name="hitl_card_generation",
                    event_id=event_id,
                )

                await bridge.emit_step_started(
                    session_id=session_id,
                    step_name="hitl_pause",
                    event_id=event_id,
                )

                st_now = get_or_init_state(ctx)
                coordinator = get_hitl_coordinator()
                await coordinator.notify_paused(
                    session_id=session_id,
                    run_id=f"run-{event_id}",
                    card=st_now.pending_hitl_card,
                    reason="hitl_approval_required",
                )
                await save_checkpoint(session_id=session_id, state=st_now)

                _PROCESSED_EVENT_IDS.add(event_id)
                status_desc: Literal["awaiting_approval", "ambiguous_escalated"] = (
                    "ambiguous_escalated"
                    if diagnosis_output.get("category") == "ambiguous"
                    else "awaiting_approval"
                )
                mark_span_ok(evt_span, status_desc)
                return ReasoningLoopResult(
                    event_id=event_id,
                    node_id=node_id,
                    status=status_desc,
                    triage_bundle=triage_bundle,
                    diagnosis=diagnosis_output,
                    remediation=None,
                    hitl_card=card_output,
                    iterations=1,
                )

    except Exception as exc:
        _PROCESSED_EVENT_IDS.add(event_id)
        current_state = get_or_init_state(ctx)
        session_id = current_state.session_id or "session-unknown"
        bridge = get_event_bridge()
        await bridge.emit_run_error(
            session_id=session_id,
            message=str(exc),
            code="REASONING_LOOP_ERROR",
        )
        return ReasoningLoopResult(
            event_id=event_id,
            node_id=locals().get("node_id", "unknown"),
            status="failed",
            iterations=1,
            error=str(exc),
        )
    finally:
        _IN_FLIGHT_EVENT_IDS.discard(event_id)
