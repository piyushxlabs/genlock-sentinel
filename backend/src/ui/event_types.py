"""Genlock Sentinel — Typed AG-UI SSE Streaming Event Schemas.

Strict Pydantic V2 models defining the complete 9-event-type vocabulary per
AGENT_MASTER_PLAN.md Section 7, Section 10 Step 15, and
INTERFACE_OBSERVABILITY_SYSTEM.md Section 2a:
  1. RUN_STARTED
  2. STEP_STARTED / STEP_FINISHED
  3. TOOL_CALL_START / TOOL_CALL_ARGS / TOOL_CALL_END / TOOL_CALL_RESULT
  4. REASONING_START / REASONING_MESSAGE_START / REASONING_MESSAGE_CONTENT / REASONING_MESSAGE_END / REASONING_END
  5. STATE_DELTA (RFC 6902 JSON patch operations)
  6. RUN_PAUSED
  7. RUN_ERROR
  8. RUN_FINISHED
  9. Supplementary: SYNC_OFFSET_SAMPLE, STATE_SNAPSHOT
"""

from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------------------
# 1. Run Lifecycle Events
# ------------------------------------------------------------------------------

class RunStartedEvent(BaseModel):
    """Emitted on session/run initialization."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["RUN_STARTED"] = "RUN_STARTED"
    runId: str = Field(..., description="Unique run identifier")
    threadId: str = Field(..., description="Session identifier")


class RunPausedEvent(BaseModel):
    """Emitted when the graph enters HITL Pause awaiting human approval."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["RUN_PAUSED"] = "RUN_PAUSED"
    runId: str = Field(..., description="Unique run identifier")
    reason: str = Field(default="hitl_approval_required", description="Pause justification reason")


class RunFinishedEvent(BaseModel):
    """Emitted when shoot session terminates."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["RUN_FINISHED"] = "RUN_FINISHED"
    runId: str = Field(..., description="Unique run identifier")


class RunErrorEvent(BaseModel):
    """Emitted on permanent system or diagnostic failure."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["RUN_ERROR"] = "RUN_ERROR"
    message: str = Field(..., description="Human-readable failure message")
    code: str = Field(..., description="Machine-readable error classification code")


# ------------------------------------------------------------------------------
# 2. Step Progress Events
# ------------------------------------------------------------------------------

StepName = Literal[
    "stream_watch",
    "evidence_triage",
    "root_cause_correlation",
    "autonomous_dispatch",
    "hitl_card_generation",
    "hitl_pause",
    "post_approval_handling",
]


class StepStartedEvent(BaseModel):
    """Emitted on entry of any of the seven ADK graph nodes."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["STEP_STARTED"] = "STEP_STARTED"
    step_name: StepName = Field(..., description="Active graph node step name")
    event_id: str = Field(..., description="Target drift event identifier")


class StepFinishedEvent(BaseModel):
    """Emitted on exit of any of the seven ADK graph nodes."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["STEP_FINISHED"] = "STEP_FINISHED"
    step_name: StepName = Field(..., description="Completed graph node step name")
    event_id: str = Field(..., description="Target drift event identifier")


# ------------------------------------------------------------------------------
# 3. Tool Execution Lifecycle Events
# ------------------------------------------------------------------------------

class ToolCallStartEvent(BaseModel):
    """Emitted immediately before invoking any of the 9 agent tools."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["TOOL_CALL_START"] = "TOOL_CALL_START"
    toolCallId: str = Field(..., description="Unique invocation identifier")
    toolCallName: str = Field(..., description="Tool name (e.g. query_loki_logs)")


class ToolCallArgsEvent(BaseModel):
    """Emitted to stream tool invocation arguments for debug tracing."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["TOOL_CALL_ARGS"] = "TOOL_CALL_ARGS"
    toolCallId: str = Field(..., description="Unique invocation identifier")
    delta: str = Field(..., description="JSON fragment of tool arguments")


class ToolCallEndEvent(BaseModel):
    """Emitted when tool arguments streaming ends."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["TOOL_CALL_END"] = "TOOL_CALL_END"
    toolCallId: str = Field(..., description="Unique invocation identifier")


class ToolCallResultEvent(BaseModel):
    """Emitted when tool execution resolves with output or error."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["TOOL_CALL_RESULT"] = "TOOL_CALL_RESULT"
    toolCallId: str = Field(..., description="Unique invocation identifier")
    content: str = Field(..., description="Serialized JSON result matching tool Output schema")


# ------------------------------------------------------------------------------
# 4. Native Model Reasoning Stream Events
# ------------------------------------------------------------------------------

class ReasoningStartEvent(BaseModel):
    """Emitted at start of Gemini 3.1 Pro thinking trace."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["REASONING_START"] = "REASONING_START"
    messageId: str = Field(..., description="Thinking message identifier")


class ReasoningMessageStartEvent(BaseModel):
    """Emitted at start of thinking content container."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["REASONING_MESSAGE_START"] = "REASONING_MESSAGE_START"
    messageId: str = Field(..., description="Thinking message identifier")


class ReasoningMessageContentEvent(BaseModel):
    """Emitted for each thinking token delta."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["REASONING_MESSAGE_CONTENT"] = "REASONING_MESSAGE_CONTENT"
    messageId: str = Field(..., description="Thinking message identifier")
    delta: str = Field(..., description="Incremental reasoning token fragment")


class ReasoningMessageEndEvent(BaseModel):
    """Emitted at conclusion of thinking content container."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["REASONING_MESSAGE_END"] = "REASONING_MESSAGE_END"
    messageId: str = Field(..., description="Thinking message identifier")


class ReasoningEndEvent(BaseModel):
    """Emitted at conclusion of Gemini 3.1 Pro thinking trace."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["REASONING_END"] = "REASONING_END"


# ------------------------------------------------------------------------------
# 5. Shared State Mutation Events (RFC 6902 JSON Patch)
# ------------------------------------------------------------------------------

class StateDeltaOp(BaseModel):
    """Single RFC 6902 JSON Patch operation matching declared state reducers."""

    model_config = ConfigDict(strict=True, extra="forbid")

    op: Literal["add", "replace", "remove"] = Field(..., description="JSON Patch operation")
    path: str = Field(..., description="Target JSON Pointer path in GenlockSentinelState")
    value: Optional[Any] = Field(default=None, description="Value payload for add/replace")


class StateDeltaEvent(BaseModel):
    """Emitted on every state mutation to keep frontend console perfectly synchronized."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["STATE_DELTA"] = "STATE_DELTA"
    delta: List[StateDeltaOp] = Field(..., description="Array of JSON Patch operations")


# ------------------------------------------------------------------------------
# 6. Supplementary Telemetry & Snapshot Events
# ------------------------------------------------------------------------------

class SyncOffsetSampleEvent(BaseModel):
    """Emitted from Stream Watch Prometheus polling for live line chart visualization."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["SYNC_OFFSET_SAMPLE"] = "SYNC_OFFSET_SAMPLE"
    node_id: str = Field(..., description="Cluster render node identifier")
    sync_offset_us: float = Field(..., description="Measured sync offset in microseconds")
    threshold_us: float = Field(default=150.0, description="Breach threshold reference line")
    timestamp: str = Field(..., description="ISO 8601 UTC sample timestamp")


class StateSnapshotEvent(BaseModel):
    """Emitted on mid-stream client reconnect to perform zero-loss full-state resync."""

    model_config = ConfigDict(strict=True, extra="forbid")

    type: Literal["STATE_SNAPSHOT"] = "STATE_SNAPSHOT"
    session_id: str = Field(..., description="Active session ID")
    state: Dict[str, Any] = Field(..., description="Full 10-field GenlockSentinelState snapshot")


# ------------------------------------------------------------------------------
# Union of All Streaming Events
# ------------------------------------------------------------------------------

StreamingEvent = Annotated[
    Union[
        RunStartedEvent,
        RunPausedEvent,
        RunFinishedEvent,
        RunErrorEvent,
        StepStartedEvent,
        StepFinishedEvent,
        ToolCallStartEvent,
        ToolCallArgsEvent,
        ToolCallEndEvent,
        ToolCallResultEvent,
        ReasoningStartEvent,
        ReasoningMessageStartEvent,
        ReasoningMessageContentEvent,
        ReasoningMessageEndEvent,
        ReasoningEndEvent,
        StateDeltaEvent,
        SyncOffsetSampleEvent,
        StateSnapshotEvent,
    ],
    Field(discriminator="type"),
]


# Explicitly rebuild all models for runtime type safety
RunStartedEvent.model_rebuild()
RunPausedEvent.model_rebuild()
RunFinishedEvent.model_rebuild()
RunErrorEvent.model_rebuild()
StepStartedEvent.model_rebuild()
StepFinishedEvent.model_rebuild()
ToolCallStartEvent.model_rebuild()
ToolCallArgsEvent.model_rebuild()
ToolCallEndEvent.model_rebuild()
ToolCallResultEvent.model_rebuild()
ReasoningStartEvent.model_rebuild()
ReasoningMessageStartEvent.model_rebuild()
ReasoningMessageContentEvent.model_rebuild()
ReasoningMessageEndEvent.model_rebuild()
ReasoningEndEvent.model_rebuild()
StateDeltaOp.model_rebuild()
StateDeltaEvent.model_rebuild()
SyncOffsetSampleEvent.model_rebuild()
StateSnapshotEvent.model_rebuild()
