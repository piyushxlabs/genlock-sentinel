"""Genlock Sentinel — Pydantic V2 Schemas for All 9 Agent Tools.

Strict Pydantic V2 models with extra="forbid" per
AGENT_MASTER_PLAN.md Section 5 and AGENT_LOGIC_SPEC.md Section 3.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------------------
# Tool 1: query_loki_logs
# ------------------------------------------------------------------------------

class QueryLokiLogsInput(BaseModel):
    """Input payload for query_loki_logs tool."""

    model_config = ConfigDict(strict=True, extra="forbid")

    datasource_uid: str = Field(default="loki-stage-01", description="Loki datasource UID in Grafana")
    logql: str = Field(..., description="LogQL query string (sanitized)")
    start: str = Field(..., description="ISO 8601 UTC start time")
    end: str = Field(..., description="ISO 8601 UTC end time")
    limit: int = Field(default=200, ge=1, le=1000, description="Max log lines to retrieve")


class QueryLokiLogsOutput(BaseModel):
    """Output payload from query_loki_logs tool."""

    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool = Field(..., description="Whether the log query completed successfully")
    result: List[str] = Field(default_factory=list, description="Raw matching log lines")
    error: Optional[str] = Field(default=None, description="Error message if query failed")


# ------------------------------------------------------------------------------
# Tool 2: find_slow_requests
# ------------------------------------------------------------------------------

class FindSlowRequestsInput(BaseModel):
    """Input payload for find_slow_requests tool (Grafana Sift)."""

    model_config = ConfigDict(strict=True, extra="forbid")

    service_name: str = Field(..., description="Service or node identifier (e.g. render-07)")
    start: str = Field(..., description="ISO 8601 UTC start time")
    end: str = Field(..., description="ISO 8601 UTC end time")
    min_duration_ms: int = Field(default=100, ge=1, description="Minimum duration threshold in ms")


class FindSlowRequestsOutput(BaseModel):
    """Output payload from find_slow_requests tool."""

    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool = Field(..., description="Whether the investigation succeeded")
    result: Dict[str, Any] = Field(default_factory=dict, description="Sift investigation findings and slow spans")
    error: Optional[str] = Field(default=None, description="Error message if query failed")


# ------------------------------------------------------------------------------
# Tool 3: get_trace_by_id
# ------------------------------------------------------------------------------

class GetTraceByIdInput(BaseModel):
    """Input payload for get_trace_by_id tool (Tempo MCP)."""

    model_config = ConfigDict(strict=True, extra="forbid")

    trace_id: str = Field(..., description="Distributed trace ID matching the active camera frame ID")


class GetTraceByIdOutput(BaseModel):
    """Output payload from get_trace_by_id tool."""

    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool = Field(..., description="Whether the trace was retrieved successfully")
    result: Dict[str, Any] = Field(default_factory=dict, description="Trace payload containing span tree")
    error: Optional[str] = Field(default=None, description="Error message if retrieval failed")


# ------------------------------------------------------------------------------
# Tools 4-6: Reversible Remediation (Autonomous Dispatch)
# ------------------------------------------------------------------------------

class ReversibleRemediationInput(BaseModel):
    """Input schema for reversible remediation tools (Tools 4, 5, 6)."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(..., description="Associated drift event identifier")
    node_id: str = Field(..., description="Target cluster render node")
    target_category: Literal["network_jitter", "asset_streaming_stall", "thermal_throttle"] = Field(
        ..., description="Diagnosed category authorizing this action"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence of the diagnosis")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operational parameters for remediation")


class ReversibleRemediationOutput(BaseModel):
    """Output schema for reversible remediation tools."""

    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool = Field(..., description="Whether the remediation command executed successfully")
    action_taken: str = Field(..., description="Name of the action executed")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of execution")
    details: Dict[str, Any] = Field(default_factory=dict, description="Action execution details")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


# ------------------------------------------------------------------------------
# Tools 7-9: HITL-Gated Actions (Post-Approval Handling)
# ------------------------------------------------------------------------------

class HitlGatedActionInput(BaseModel):
    """Input schema for HITL-gated actions (Tools 7, 8, 9)."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(..., description="Associated drift event identifier")
    hitl_card_id: str = Field(..., description="ID of the approved HITL card")
    approval_state: Literal["approved"] = Field(..., description="Must equal 'approved' at type level")
    node_id: Optional[str] = Field(default=None, description="Target cluster render node")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")


class HitlGatedActionOutput(BaseModel):
    """Output schema for HITL-gated actions."""

    model_config = ConfigDict(strict=True, extra="forbid")

    success: bool = Field(..., description="Whether the stage control action succeeded")
    action_taken: str = Field(..., description="Name of the high-stakes action executed")
    timestamp: str = Field(..., description="ISO 8601 UTC execution timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Execution confirmation details")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
