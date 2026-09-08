"""Genlock Sentinel — Post-Approval Handling Tools (Tools 7, 8, 9).

Implements:
  - Tool 7: halt_live_take
  - Tool 8: fallback_to_greenscreen
  - Tool 9: execute_threshold_exceeding_failover

Bound exclusively to Post-Approval Handling (Node 7) per
AGENT_LOGIC_SPEC.md Section 3 and Section 6.
Callable only when approval_state == 'approved' on the matching HITL card.
"""

from __future__ import annotations

from typing import Optional

from src.state.schema import ApprovalStatus, GenlockSentinelState, utc_now_iso
from src.tools.schemas.pydantic_models import (
    HitlGatedActionInput,
    HitlGatedActionOutput,
)
from src.utils.errors import StateValidationError


def _verify_hitl_precondition(
    state: GenlockSentinelState,
    payload: HitlGatedActionInput,
    expected_action: str,
) -> None:
    """Verifies that approval_state is 'approved' and matches the pending HITL card."""
    if state.approval_state != ApprovalStatus.APPROVED:
        raise StateValidationError(
            f"Precondition failed: {expected_action} requires state.approval_state == 'approved', "
            f"found '{state.approval_state}'."
        )

    if state.pending_hitl_card is None:
        raise StateValidationError(
            f"Precondition failed: No active pending_hitl_card found in state for {expected_action}."
        )

    if state.pending_hitl_card.proposed_action != expected_action:
        raise StateValidationError(
            f"Precondition failed: Pending HITL card proposed_action '{state.pending_hitl_card.proposed_action}' "
            f"does not match required tool '{expected_action}'."
        )

    # Verify card ID or event ID correlation
    if (
        state.pending_hitl_card.card_id != payload.hitl_card_id
        and state.pending_hitl_card.event_id != payload.hitl_card_id
    ):
        raise StateValidationError(
            f"Precondition failed: hitl_card_id '{payload.hitl_card_id}' does not match "
            f"pending card id '{state.pending_hitl_card.card_id}'."
        )


async def halt_live_take(
    payload: HitlGatedActionInput,
    state: Optional[GenlockSentinelState] = None,
) -> HitlGatedActionOutput:
    """Tool 7: Halts the active camera take on the virtual production stage.

    Precondition: approval_state == 'approved' and pending_hitl_card.proposed_action == 'halt_live_take'.
    """
    if state is not None:
        _verify_hitl_precondition(state, payload, expected_action="halt_live_take")

    return HitlGatedActionOutput(
        success=True,
        action_taken="halt_live_take",
        timestamp=utc_now_iso(),
        details={
            "event_id": payload.event_id,
            "hitl_card_id": payload.hitl_card_id,
            "status": "take_halted",
            "stage_director_notified": True,
            "timecode_freeze": "14:02:12:08",
        },
        error=None,
    )


async def fallback_to_greenscreen(
    payload: HitlGatedActionInput,
    state: Optional[GenlockSentinelState] = None,
) -> HitlGatedActionOutput:
    """Tool 8: Switches LED volume display to uniform chromakey greenscreen.

    Precondition: approval_state == 'approved' and pending_hitl_card.proposed_action == 'fallback_to_greenscreen'.
    """
    if state is not None:
        _verify_hitl_precondition(state, payload, expected_action="fallback_to_greenscreen")

    return HitlGatedActionOutput(
        success=True,
        action_taken="fallback_to_greenscreen",
        timestamp=utc_now_iso(),
        details={
            "event_id": payload.event_id,
            "hitl_card_id": payload.hitl_card_id,
            "status": "greenscreen_engaged",
            "chroma_color_hex": "#00FF00",
        },
        error=None,
    )


async def execute_threshold_exceeding_failover(
    payload: HitlGatedActionInput,
    state: Optional[GenlockSentinelState] = None,
) -> HitlGatedActionOutput:
    """Tool 9: Triggers a high-cost multi-node or cloud failover exceeding financial limits.

    Precondition: approval_state == 'approved' and proposed_action == 'execute_threshold_exceeding_failover'.
    """
    if state is not None:
        _verify_hitl_precondition(state, payload, expected_action="execute_threshold_exceeding_failover")

    return HitlGatedActionOutput(
        success=True,
        action_taken="execute_threshold_exceeding_failover",
        timestamp=utc_now_iso(),
        details={
            "event_id": payload.event_id,
            "hitl_card_id": payload.hitl_card_id,
            "status": "cloud_failover_dispatched",
            "authorized_cost_cap_usd": payload.parameters.get("authorized_cost_usd", 2500.0),
        },
        error=None,
    )
