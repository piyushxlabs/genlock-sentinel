"""Node 5: HITL Card Generation (Gemini 3.7 Flash).

Packages an escalated or ambiguous diagnosis into a structured HITLCardPackage
specifying the escalation reason, proposed action, cost delta estimate,
visual impact score, and grounded summary.

Node-Tool Access Matrix:
- Structured Output only (HITLCardPackage).
- Reads diagnosis_history, evidence_bundle.
- Writes pending_hitl_card and session_status = awaiting_approval.
- NO external tools bound.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from google.adk import Context
from pydantic import BaseModel, ConfigDict, Field

from src.agents.model_config import generate_structured_output
from src.state.reducers import reduce_state
from src.state.schema import GenlockSentinelState, HITLCard, SessionStatus, get_or_init_state
from src.structured_outputs.hitl_card_package import HITLCardPackage


class HITLCardGenerationInput(BaseModel):
    """Input payload for HITL Card Generation node."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: Optional[str] = Field(None, description="Active drift event ID")
    escalation_reason: Optional[str] = Field(None, description="Reason for HITL escalation")


async def hitl_card_generation_node(
    ctx: Context,
    node_input: Optional[HITLCardGenerationInput | Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates HITLCardPackage and updates pending_hitl_card state."""
    state = get_or_init_state(ctx)

    # 1. Resolve event_id and latest diagnosis
    event_id: str
    target_node_id: str = "render-07"
    if state.diagnosis_history:
        latest_diag = state.diagnosis_history[-1]
        event_id = latest_diag.event_id
        target_node_id = latest_diag.node_id or "render-07"
        category = latest_diag.category
        confidence = latest_diag.confidence
        rationale = latest_diag.rationale
    else:
        event_id = "drift-render-07-f-144021-default"
        category = "ambiguous"
        confidence = 0.50
        rationale = "Ambiguous diagnosis: conflicting Loki logs and Tempo traces."

    evidence = state.evidence_bundle.get(event_id)
    log_summary = evidence.log_summary if evidence else "Logs show frame drop warning."
    trace_summary = evidence.trace_summary if evidence else "Traces show render span jitter."

    # 2. Build prompt for Gemini 3.7 Flash
    card_prompt = f"""Generate a HITLCardPackage for on-set virtual production supervisor approval.
Event: {event_id}
Diagnosed Category: {category} (confidence: {confidence})
Rationale: {rationale}
Log evidence: {log_summary}
Trace evidence: {trace_summary}

Requirements:
- escalation_reason: Exactly one of ('ambiguous_diagnosis', 'take_halt_required', 'capture_fallback_required', 'threshold_exceeded')
- proposed_action: One of ('halt_live_take', 'fallback_to_greenscreen', 'execute_threshold_exceeding_failover')
- cost_delta_estimate: Cost estimate string (e.g. '$1,250 USD' or '1250.0')
- visual_impact_score: Impact score string (e.g. '8.5 / 10')
- root_cause_summary: Grounded, concise operational summary for the stage supervisor.

Produce an exact HITLCardPackage JSON."""

    package: HITLCardPackage = await generate_structured_output(
        role="fast",
        schema_cls=HITLCardPackage,
        prompt=card_prompt,
        mock_key="hitl_card_complex",
    )

    if package.event_id != latest_diag.event_id:
        package = HITLCardPackage(
            event_id=latest_diag.event_id,
            escalation_reason=package.escalation_reason,
            proposed_action=package.proposed_action,
            cost_delta_estimate=package.cost_delta_estimate,
            visual_impact_score=package.visual_impact_score,
            root_cause_summary=package.root_cause_summary,
        )

    # Convert to state HITLCard model via from_package helper
    card_model = HITLCard.from_package(
        package=package,
        node_id=target_node_id,
    )

    # Apply state reducers
    deltas = {
        "pending_hitl_card": card_model.model_dump(),
        "session_status": SessionStatus.AWAITING_APPROVAL.value,
    }
    updated_state = reduce_state(state, deltas)

    ctx.actions.state_delta["pending_hitl_card"] = updated_state.pending_hitl_card.model_dump()
    ctx.actions.state_delta["session_status"] = updated_state.session_status.value

    return package.model_dump()
