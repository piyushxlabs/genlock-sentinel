"""Node 7: Post-Approval Handling (Deterministic).

Dispatches HITL-gated actuator tools strictly after human supervisor approval.
Enforces programmatic approval_state verification and card matching.

Node-Tool Access Matrix:
- Deterministic dispatch: Bound ONLY to Tools 7–9:
  halt_live_take, fallback_to_greenscreen, execute_threshold_exceeding_failover.
- Callable ONLY after supervisor approval.
- NO LLM calls.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from google.adk import Context
from pydantic import BaseModel, ConfigDict, Field

from src.state.reducers import reduce_state
from src.state.schema import (
    ApprovalStatus,
    GenlockSentinelState,
    RemediationAction,
    SessionStatus,
    get_or_init_state,
    utc_now_iso,
)
from src.tools.post_approval_tools import (
    execute_threshold_exceeding_failover,
    fallback_to_greenscreen,
    halt_live_take,
)
from src.tools.schemas.pydantic_models import (
    HitlGatedActionInput,
    HitlGatedActionOutput,
)
from src.utils.errors import PostApprovalExecutionError, ToolExecutionError


class PostApprovalOutput(BaseModel):
    """Output payload from Post-Approval Handling node."""

    model_config = ConfigDict(strict=True, extra="forbid")

    action_taken: str = Field(..., description="Action executed or denial logged")
    success: bool = Field(..., description="Whether action succeeded")
    approval_state: str = Field(..., description="The approval state verified")
    event_id: str = Field(..., description="Event identifier")
    details: Dict[str, Any] = Field(default_factory=dict, description="Action details")


async def post_approval_handling_node(
    ctx: Context,
    node_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Executes the supervisor-approved tool or handles operational denial."""
    state = get_or_init_state(ctx)

    if not state.pending_hitl_card:
        raise ToolExecutionError("Post-approval handling called with no pending_hitl_card in state")

    card = state.pending_hitl_card
    event_id = card.event_id
    proposed_action = card.proposed_action
    approval_state = state.approval_state

    # Resolve target node id
    target_node_id = card.node_id or "render-07"
    for d_event in state.active_drift_events.values():
        if d_event.event_id == event_id:
            target_node_id = d_event.node_id
            break

    # If supervisor denied the proposed action
    if approval_state == ApprovalStatus.DENIED:
        denial_record = RemediationAction(
            action_id=f"act-{uuid4().hex[:8]}",
            event_id=event_id,
            node_id=target_node_id,
            action_taken=f"denied_{proposed_action}",
            timestamp=utc_now_iso(),
            success=False,
            details={"supervisor_decision": "denied", "proposed_action": proposed_action},
        )
        deltas = {
            "remediation_log": [denial_record.model_dump()],
            "session_status": SessionStatus.MONITORING.value,
        }
        updated_state = reduce_state(state, deltas)

        ctx.actions.state_delta["remediation_log"] = [
            r.model_dump() for r in updated_state.remediation_log
        ]
        ctx.actions.state_delta["session_status"] = updated_state.session_status.value

        output = PostApprovalOutput(
            action_taken=f"denied_{proposed_action}",
            success=True,
            approval_state=approval_state.value,
            event_id=event_id,
            details={"status": "denied_by_supervisor"},
        )
        return output.model_dump()

    # If supervisor approved the proposed action
    if approval_state == ApprovalStatus.APPROVED:
        action_name: str
        tool_res: HitlGatedActionOutput

        payload = HitlGatedActionInput(
            event_id=event_id,
            hitl_card_id=card.card_id,
            approval_state="approved",
            node_id=target_node_id,
            parameters={"proposed_action": proposed_action},
        )

        norm_action = (proposed_action or "").strip().lower()

        if norm_action == "halt_live_take":
            action_name = "halt_live_take"
            tool_res = await halt_live_take(payload, state=state)
            details = tool_res.model_dump()

        elif norm_action == "fallback_to_greenscreen":
            action_name = "fallback_to_greenscreen"
            tool_res = await fallback_to_greenscreen(payload, state=state)
            details = tool_res.model_dump()

        elif norm_action == "execute_threshold_exceeding_failover":
            action_name = "execute_threshold_exceeding_failover"
            tool_res = await execute_threshold_exceeding_failover(payload, state=state)
            details = tool_res.model_dump()

        elif norm_action == "none" or "none" in norm_action or norm_action in ("no_action", "acknowledge", "acknowledgement", ""):
            action_name = "supervisor_acknowledged"
            details = {
                "status": "approved_acknowledgment",
                "proposed_action": proposed_action,
                "note": "Supervisor acknowledged diagnostic finding without actuator execution",
            }

        else:
            raise PostApprovalExecutionError(
                f"Unknown HITL-gated action: '{proposed_action}'"
            )

        # Record action in state
        action_record = RemediationAction(
            action_id=f"act-{uuid4().hex[:8]}",
            event_id=event_id,
            node_id=target_node_id,
            action_taken=action_name,
            timestamp=utc_now_iso(),
            success=details.get("success", True),
            details=details,
        )

        deltas = {
            "remediation_log": [action_record.model_dump()],
            "session_status": SessionStatus.MONITORING.value,
        }
        updated_state = reduce_state(state, deltas)

        ctx.actions.state_delta["remediation_log"] = [
            r.model_dump() for r in updated_state.remediation_log
        ]
        ctx.actions.state_delta["session_status"] = updated_state.session_status.value

        output = PostApprovalOutput(
            action_taken=action_name,
            success=details.get("success", True),
            approval_state=approval_state.value,
            event_id=event_id,
            details=details,
        )
        return output.model_dump()

    raise ToolExecutionError(
        f"Post-approval handling invoked with invalid approval_state: '{approval_state}'"
    )
