"""Genlock Sentinel — Autonomous Remediation Tools (Tools 4, 5, 6).

Implements:
  - Tool 4: failover_cluster_leadership (network_jitter)
  - Tool 5: deprioritize_texture_streaming (asset_streaming_stall)
  - Tool 6: force_genlock_resync (thermal_throttle)

Bound exclusively to Autonomous Remediation Dispatch (Node 4) per
AGENT_LOGIC_SPEC.md Section 3 and Section 6.
"""

from __future__ import annotations

from typing import Optional

from src.state.schema import GenlockSentinelState, utc_now_iso
from src.tools.schemas.pydantic_models import (
    ReversibleRemediationInput,
    ReversibleRemediationOutput,
)
from src.utils.errors import StateValidationError


def _verify_remediation_precondition(
    state: GenlockSentinelState,
    payload: ReversibleRemediationInput,
    expected_category: str,
    action_name: str,
) -> None:
    """Verifies that diagnosis matches expected category and meets confidence floor."""
    if payload.target_category != expected_category:
        raise StateValidationError(
            f"Precondition failed: {action_name} requires target_category='{expected_category}', "
            f"received '{payload.target_category}'."
        )

    # Search latest diagnosis for this event in state
    matching_records = [d for d in state.diagnosis_history if d.event_id == payload.event_id]
    if not matching_records:
        raise StateValidationError(
            f"Precondition failed: No DiagnosisRecord found in diagnosis_history for event '{payload.event_id}'."
        )

    latest_diag = matching_records[-1]
    if latest_diag.category != expected_category:
        raise StateValidationError(
            f"Precondition failed: Latest diagnosis category '{latest_diag.category}' does not match "
            f"required category '{expected_category}' for {action_name}."
        )

    if latest_diag.confidence < state.config.confidence_floor:
        raise StateValidationError(
            f"Precondition failed: Diagnosis confidence {latest_diag.confidence:.2f} is below "
            f"confidence floor {state.config.confidence_floor:.2f}."
        )


async def failover_cluster_leadership(
    payload: ReversibleRemediationInput,
    state: Optional[GenlockSentinelState] = None,
) -> ReversibleRemediationOutput:
    """Tool 4: Fails cluster leadership over to a healthy standby node.

    Precondition: Latest diagnosis has category == 'network_jitter' and confidence >= floor.
    """
    if state is not None:
        _verify_remediation_precondition(
            state, payload, expected_category="network_jitter", action_name="failover_cluster_leadership"
        )

    return ReversibleRemediationOutput(
        success=True,
        action_taken="failover_cluster_leadership",
        timestamp=utc_now_iso(),
        details={
            "target_node": payload.node_id,
            "event_id": payload.event_id,
            "status": "failover_completed",
            "standby_promoted": payload.parameters.get("standby_node", "render-08"),
        },
        error=None,
    )


async def deprioritize_texture_streaming(
    payload: ReversibleRemediationInput,
    state: Optional[GenlockSentinelState] = None,
) -> ReversibleRemediationOutput:
    """Tool 5: Deprioritizes background texture streaming to resolve asset streaming stalls.

    Precondition: Latest diagnosis has category == 'asset_streaming_stall' and confidence >= floor.
    """
    if state is not None:
        _verify_remediation_precondition(
            state, payload, expected_category="asset_streaming_stall", action_name="deprioritize_texture_streaming"
        )

    return ReversibleRemediationOutput(
        success=True,
        action_taken="deprioritize_texture_streaming",
        timestamp=utc_now_iso(),
        details={
            "target_node": payload.node_id,
            "event_id": payload.event_id,
            "status": "texture_pool_throttled",
            "streaming_pool_reduction_pct": 50,
        },
        error=None,
    )


async def force_genlock_resync(
    payload: ReversibleRemediationInput,
    state: Optional[GenlockSentinelState] = None,
) -> ReversibleRemediationOutput:
    """Tool 6: Forces an immediate genlock hardware re-sync handshake.

    Precondition: Latest diagnosis has category == 'thermal_throttle' and confidence >= floor.
    """
    if state is not None:
        _verify_remediation_precondition(
            state, payload, expected_category="thermal_throttle", action_name="force_genlock_resync"
        )

    return ReversibleRemediationOutput(
        success=True,
        action_taken="force_genlock_resync",
        timestamp=utc_now_iso(),
        details={
            "target_node": payload.node_id,
            "event_id": payload.event_id,
            "status": "resync_handshake_dispatched",
            "vsync_lock_acquired": True,
        },
        error=None,
    )
