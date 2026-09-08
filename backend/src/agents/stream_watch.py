"""Node 1: Stream Watch (Non-LLM).

Continuously ingests and evaluates live genlock sync-offset telemetry
against operational vsync-variance thresholds. Upon threshold breach,
instantiates an active DriftEvent, updates active_drift_events, and
transitions session_status to ACTIVE / TRIAGING.

Node-Tool Access Matrix:
- Polling/subscription only: Bound to Prometheus sync-offset ingestion.
- Writes active_drift_events.
- NO external write tools bound.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import uuid4

from google.adk import Context
from pydantic import BaseModel, ConfigDict, Field

from src.state.reducers import reduce_state
from src.state.schema import (
    DriftEvent,
    GenlockSentinelState,
    SessionStatus,
    get_or_init_state,
    utc_now_iso,
)


class StreamWatchInput(BaseModel):
    """Input payload for Stream Watch node."""

    model_config = ConfigDict(strict=True, extra="forbid")

    node_id: str = Field(default="render-07", description="Target render cluster node")
    sync_offset_us: float = Field(default=842.0, description="Measured vsync offset in microseconds")
    frame_id: str = Field(default="f-144021", description="Live production frame identifier")
    timestamp: float = Field(default_factory=time.time, description="Telemetry capture epoch timestamp")
    metric_name: str = Field(default="genlock_sync_offset_us", description="Telemetry metric key")


class StreamWatchOutput(BaseModel):
    """Output payload from Stream Watch node."""

    model_config = ConfigDict(strict=True, extra="forbid")

    threshold_breached: bool = Field(..., description="Whether vsync variance threshold was breached")
    drift_event: Optional[DriftEvent] = Field(None, description="Instantiated drift event if breached")
    message: str = Field(..., description="Evaluation summary message")


async def stream_watch_node(
    ctx: Context,
    node_input: Optional[StreamWatchInput | Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluates telemetry sample and emits drift event on threshold breach."""
    current_state = get_or_init_state(ctx)
    threshold = current_state.config.sync_offset_threshold_us

    # Ensure session_id is persisted in context state delta
    if "session_id" not in ctx.state:
        ctx.actions.state_delta["session_id"] = current_state.session_id

    # Parse input
    if node_input is None:
        telemetry = StreamWatchInput()
    elif isinstance(node_input, StreamWatchInput):
        telemetry = node_input
    elif isinstance(node_input, dict):
        telemetry = StreamWatchInput.model_validate(node_input)
    else:
        telemetry = StreamWatchInput()

    is_breach = telemetry.sync_offset_us > threshold

    if is_breach:
        event_id = f"drift-{telemetry.node_id}-{telemetry.frame_id}-{int(telemetry.timestamp)}"
        drift_event = DriftEvent(
            event_id=event_id,
            node_id=telemetry.node_id,
            frame_id=telemetry.frame_id,
            breach_ts=utc_now_iso(),
            sync_offset_us=telemetry.sync_offset_us,
            threshold_us=threshold,
            status="detected",
        )

        deltas = {
            "active_drift_events": {telemetry.node_id: drift_event.model_dump()},
            "session_status": SessionStatus.TRIAGING.value,
        }

        # Apply state reducers
        updated_state = reduce_state(current_state, deltas)

        # Commit deltas to ADK context
        ctx.actions.state_delta["active_drift_events"] = {
            k: v.model_dump() for k, v in updated_state.active_drift_events.items()
        }
        ctx.actions.state_delta["session_status"] = updated_state.session_status.value

        output = StreamWatchOutput(
            threshold_breached=True,
            drift_event=drift_event,
            message=(
                f"Drift breach detected on {telemetry.node_id}: "
                f"{telemetry.sync_offset_us}us > {threshold}us threshold."
            ),
        )
    else:
        output = StreamWatchOutput(
            threshold_breached=False,
            drift_event=None,
            message=(
                f"Sync offset nominal on {telemetry.node_id}: "
                f"{telemetry.sync_offset_us}us <= {threshold}us threshold."
            ),
        )

    return output.model_dump()
