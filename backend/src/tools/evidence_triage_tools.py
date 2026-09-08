"""Genlock Sentinel — Evidence Triage Tools (Tools 1, 2, 3).

Implements:
  - Tool 1: query_loki_logs
  - Tool 2: find_slow_requests
  - Tool 3: get_trace_by_id

Bound exclusively to Evidence Triage (Node 2) per
AGENT_LOGIC_SPEC.md Section 3 and Section 6.
"""

from __future__ import annotations

from typing import Optional

from src.state.schema import GenlockSentinelState
from src.tools.mcp_clients.grafana_mcp_client import GrafanaMCPClient, sanitize_logql
from src.tools.schemas.pydantic_models import (
    FindSlowRequestsInput,
    FindSlowRequestsOutput,
    GetTraceByIdInput,
    GetTraceByIdOutput,
    QueryLokiLogsInput,
    QueryLokiLogsOutput,
)
from src.utils.errors import StateValidationError


# Default client instance
_default_client: Optional[GrafanaMCPClient] = None


def get_mcp_client() -> GrafanaMCPClient:
    """Returns or lazily instantiates the GrafanaMCPClient."""
    global _default_client
    if _default_client is None:
        _default_client = GrafanaMCPClient()
    return _default_client


async def query_loki_logs(
    payload: QueryLokiLogsInput,
    state: Optional[GenlockSentinelState] = None,
    node_id: Optional[str] = None,
    client: Optional[GrafanaMCPClient] = None,
    simulate_timeout: bool = False,
) -> QueryLokiLogsOutput:
    """Tool 1: Queries Grafana Loki for nDisplay cluster manager & engine logs.

    Precondition: An active DriftEvent must exist for the target node_id if state is provided.
    """
    if state is not None and node_id is not None:
        if node_id not in state.active_drift_events:
            raise StateValidationError(
                f"Precondition failed: No active DriftEvent found for node '{node_id}' in active_drift_events."
            )

    active_client = client or get_mcp_client()
    return await active_client.query_loki_logs(payload, simulate_timeout=simulate_timeout)


async def find_slow_requests(
    payload: FindSlowRequestsInput,
    state: Optional[GenlockSentinelState] = None,
    client: Optional[GrafanaMCPClient] = None,
    simulate_timeout: bool = False,
) -> FindSlowRequestsOutput:
    """Tool 2: Investigates slow render spans via Grafana Sift on Tempo.

    Precondition: An active DriftEvent must exist for the target service/node if state is provided.
    """
    if state is not None:
        node_id = payload.service_name
        if node_id not in state.active_drift_events:
            raise StateValidationError(
                f"Precondition failed: No active DriftEvent found for node '{node_id}' in active_drift_events."
            )

    active_client = client or get_mcp_client()
    return await active_client.find_slow_requests(payload, simulate_timeout=simulate_timeout)


async def get_trace_by_id(
    payload: GetTraceByIdInput,
    state: Optional[GenlockSentinelState] = None,
    client: Optional[GrafanaMCPClient] = None,
    simulate_timeout: bool = False,
) -> GetTraceByIdOutput:
    """Tool 3: Retrieves complete distributed trace by frame_id from Tempo MCP.

    Precondition: A matching frame_id must exist on an active DriftEvent if state is provided.
    """
    if state is not None:
        matching_frames = [
            e.frame_id for e in state.active_drift_events.values() if e.frame_id == payload.trace_id
        ]
        if not matching_frames:
            raise StateValidationError(
                f"Precondition failed: trace_id '{payload.trace_id}' does not match any active DriftEvent frame_id."
            )

    active_client = client or get_mcp_client()
    return await active_client.get_trace_by_id(payload, simulate_timeout=simulate_timeout)
