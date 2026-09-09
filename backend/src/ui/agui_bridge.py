"""Genlock Sentinel — Typed AG-UI SSE Streaming Event Bridge.

Bridges the Google ADK 2.x Workflow Runtime and GenlockSentinelState mutations
to the AG-UI SSE protocol per AGENT_MASTER_PLAN.md Section 7, Section 10 Step 15,
and INTERFACE_OBSERVABILITY_SYSTEM.md Section 2 & 2a.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from google.adk import Event
from pydantic import BaseModel

from src.state.checkpointing import load_checkpoint
from src.state.schema import utc_now_iso
from src.ui.event_types import (
    ReasoningEndEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    ReasoningMessageStartEvent,
    ReasoningStartEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunPausedEvent,
    RunStartedEvent,
    StateDeltaEvent,
    StateDeltaOp,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepName,
    StepStartedEvent,
    StreamingEvent,
    SyncOffsetSampleEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)

logger = logging.getLogger("genlock_sentinel.ui.agui_bridge")


class AGUIEventBridge:
    """Central event bridge managing typed AG-UI SSE streaming for Genlock Sentinel.

    Provides:
      - Subscription management for multiple concurrent SSE clients per session.
      - Conversion and formatting of typed events to standard SSE wire format (`data: <json>\\n\\n`).
      - RFC 6902 JSON Patch state delta generation matching declared reducer semantics.
      - Full-state snapshot delivery on client reconnect.
      - Projection of ADK 2.x Workflow events into typed AG-UI streaming events.
      - High-frequency telemetry broadcasting (Prometheus sync-offset stream).
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, Set[asyncio.Queue[str]]] = {}
        self._lock = asyncio.Lock()

    # --------------------------------------------------------------------------
    # 1. Wire Formatting
    # --------------------------------------------------------------------------

    @staticmethod
    def format_sse_event(event: Any) -> str:
        """Serializes any typed event, Pydantic model, or dictionary into an SSE wire block.

        Format: `data: <json_string>\\n\\n`
        """
        if isinstance(event, BaseModel):
            payload_json = event.model_dump_json()
        elif isinstance(event, dict):
            payload_json = json.dumps(event)
        elif isinstance(event, str):
            payload_json = event
        else:
            raise ValueError(f"Unsupported event payload type: {type(event)}")

        # Ensure single-line data frame per SSE specification standard
        cleaned_json = payload_json.replace("\r\n", "").replace("\n", "")
        return f"data: {cleaned_json}\n\n"

    # --------------------------------------------------------------------------
    # 2. State Delta RFC 6902 Projection
    # --------------------------------------------------------------------------

    @staticmethod
    def build_state_delta(
        field_name: str,
        reducer_type: str,
        value: Any,
        key: Optional[str] = None,
    ) -> StateDeltaEvent:
        """Translates state mutations into RFC 6902 JSON Patch operations matching declared reducers.

        Reducers:
          - append-only (diagnosis_history, remediation_log, error_logs) -> `add` at `/{field}/-`
          - merge-by-key (active_drift_events, evidence_bundle) -> `add` at `/{field}/{key}`
          - last-write-wins (approval_state, session_status, pending_hitl_card) -> `replace` at `/{field}`
        """
        serialized_value: Any
        if isinstance(value, BaseModel):
            serialized_value = value.model_dump(mode="json")
        elif hasattr(value, "value"):  # Enum support
            serialized_value = value.value
        elif isinstance(value, dict):
            serialized_value = value
        else:
            serialized_value = value

        ops: List[StateDeltaOp] = []

        if reducer_type == "append-only":
            ops.append(
                StateDeltaOp(
                    op="add",
                    path=f"/{field_name}/-",
                    value=serialized_value,
                )
            )
        elif reducer_type == "merge-by-key":
            if not key:
                if isinstance(value, BaseModel):
                    key = getattr(value, "event_id", None) or getattr(value, "node_id", None)
                elif isinstance(value, dict):
                    key = value.get("event_id") or value.get("node_id")
            if not key:
                raise ValueError("merge-by-key reducer requires a non-empty key parameter.")
            ops.append(
                StateDeltaOp(
                    op="add",
                    path=f"/{field_name}/{key}",
                    value=serialized_value,
                )
            )
        elif reducer_type == "last-write-wins":
            ops.append(
                StateDeltaOp(
                    op="replace",
                    path=f"/{field_name}",
                    value=serialized_value,
                )
            )
        else:
            raise ValueError(f"Unknown reducer type '{reducer_type}' for field '{field_name}'.")

        return StateDeltaEvent(delta=ops)

    # --------------------------------------------------------------------------
    # 3. ADK Workflow Event Projection
    # --------------------------------------------------------------------------

    @staticmethod
    def project_adk_event(
        event: Event,
        session_id: str,
        target_event_id: str = "default_event",
    ) -> List[StreamingEvent]:
        """Projects native Google ADK 2.x Event objects into typed AG-UI streaming events.

        Translates:
          - Node lifecycle -> StepStartedEvent / StepFinishedEvent
          - Tool invocation -> ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent
          - Tool completion -> ToolCallResultEvent
        """
        projected: List[StreamingEvent] = []
        node_name = getattr(event, "node_name", None)

        # 1. Project node / step transitions
        valid_step_names = {
            "stream_watch",
            "evidence_triage",
            "root_cause_correlation",
            "autonomous_dispatch",
            "hitl_card_generation",
            "hitl_pause",
            "post_approval_handling",
        }
        if node_name and node_name in valid_step_names:
            step_typed: StepName = node_name  # type: ignore[assignment]
            projected.append(StepStartedEvent(step_name=step_typed, event_id=target_event_id))

        # 2. Project function / tool calls
        if hasattr(event, "get_function_calls"):
            fn_calls = event.get_function_calls()
            for fn in fn_calls:
                call_id = getattr(fn, "id", f"call_{getattr(fn, 'name', 'tool')}")
                call_name = getattr(fn, "name", "unknown_tool")
                raw_args = getattr(fn, "args", {})
                args_json = json.dumps(raw_args) if not isinstance(raw_args, str) else raw_args

                projected.append(ToolCallStartEvent(toolCallId=call_id, toolCallName=call_name))
                projected.append(ToolCallArgsEvent(toolCallId=call_id, delta=args_json))
                projected.append(ToolCallEndEvent(toolCallId=call_id))

        # 3. Project function / tool responses
        if hasattr(event, "get_function_responses"):
            fn_responses = event.get_function_responses()
            for resp in fn_responses:
                call_id = getattr(resp, "id", f"resp_{getattr(resp, 'name', 'tool')}")
                raw_response = getattr(resp, "response", {})
                resp_json = json.dumps(raw_response) if not isinstance(raw_response, str) else raw_response

                projected.append(ToolCallResultEvent(toolCallId=call_id, content=resp_json))

        return projected

    # --------------------------------------------------------------------------
    # 4. Subscription & Streaming Management
    # --------------------------------------------------------------------------

    async def register_subscriber(self, session_id: str) -> asyncio.Queue[str]:
        """Registers a new SSE listener queue for a given session."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            if session_id not in self._subscribers:
                self._subscribers[session_id] = set()
            self._subscribers[session_id].add(queue)
        return queue

    async def unregister_subscriber(self, session_id: str, queue: asyncio.Queue[str]) -> None:
        """Removes an active SSE listener queue."""
        async with self._lock:
            if session_id in self._subscribers:
                self._subscribers[session_id].discard(queue)
                if not self._subscribers[session_id]:
                    del self._subscribers[session_id]

    async def broadcast_event(self, session_id: str, event: Any) -> None:
        """Publishes an event to all active SSE subscribers for a session."""
        wire_line = self.format_sse_event(event)
        async with self._lock:
            subscribers = list(self._subscribers.get(session_id, []))

        for queue in subscribers:
            await queue.put(wire_line)

    async def stream_session_events(
        self,
        session_id: str,
        emit_initial_snapshot: bool = True,
        keepalive_interval: float = 15.0,
        max_events: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Asynchronous generator streaming SSE lines for an active session.

        Features:
          - Immediate StateSnapshotEvent resync on connection/reconnect.
          - Periodic `: ping\\n\\n` keepalive frames to defeat proxy and gateway timeouts.
          - Guaranteed cleanup on client disconnect.
          - Optional max_events bound for test determinism and finite consumption.
        """
        queue = await self.register_subscriber(session_id)
        yielded_count = 0
        try:
            # Send initial ping so Starlette/FastAPI flushes SSE response headers immediately
            yield ": ping\n\n"
            yielded_count += 1
            if max_events is not None and yielded_count >= max_events:
                return

            # 1. Zero-loss reconnect: stream current state snapshot if available
            if emit_initial_snapshot:
                state = await load_checkpoint(session_id=session_id)
                if state is not None:
                    snapshot_event = StateSnapshotEvent(
                        session_id=session_id,
                        state=state.model_dump(mode="json"),
                    )
                    yield self.format_sse_event(snapshot_event)
                    yielded_count += 1
                    if max_events is not None and yielded_count >= max_events:
                        return

            # 2. Stream live events and keepalive frames
            while True:
                if max_events is not None and yielded_count >= max_events:
                    break
                try:
                    line = await asyncio.wait_for(queue.get(), timeout=keepalive_interval)
                    yield line
                    yielded_count += 1
                    if max_events is not None and yielded_count >= max_events:
                        break
                except asyncio.TimeoutError:
                    # Send standard SSE keepalive comment line
                    yield ": ping\n\n"
                    yielded_count += 1
                    if max_events is not None and yielded_count >= max_events:
                        break
        finally:
            await self.unregister_subscriber(session_id, queue)

    # --------------------------------------------------------------------------
    # 5. Direct Event Emission Helpers
    # --------------------------------------------------------------------------

    async def emit_run_started(self, session_id: str, run_id: str) -> RunStartedEvent:
        """Emits RUN_STARTED event."""
        evt = RunStartedEvent(runId=run_id, threadId=session_id)
        await self.broadcast_event(session_id, evt)
        return evt

    async def emit_run_paused(
        self, session_id: str, run_id: str, reason: str = "hitl_approval_required"
    ) -> RunPausedEvent:
        """Emits RUN_PAUSED event."""
        evt = RunPausedEvent(runId=run_id, reason=reason)
        await self.broadcast_event(session_id, evt)
        return evt

    async def emit_run_finished(self, session_id: str, run_id: str) -> RunFinishedEvent:
        """Emits RUN_FINISHED event."""
        evt = RunFinishedEvent(runId=run_id)
        await self.broadcast_event(session_id, evt)
        return evt

    async def emit_run_error(self, session_id: str, message: str, code: str) -> RunErrorEvent:
        """Emits RUN_ERROR event."""
        evt = RunErrorEvent(message=message, code=code)
        await self.broadcast_event(session_id, evt)
        return evt

    async def emit_step_started(self, session_id: str, step_name: StepName, event_id: str) -> StepStartedEvent:
        """Emits STEP_STARTED event."""
        evt = StepStartedEvent(step_name=step_name, event_id=event_id)
        await self.broadcast_event(session_id, evt)
        return evt

    async def emit_step_finished(self, session_id: str, step_name: StepName, event_id: str) -> StepFinishedEvent:
        """Emits STEP_FINISHED event."""
        evt = StepFinishedEvent(step_name=step_name, event_id=event_id)
        await self.broadcast_event(session_id, evt)
        return evt

    async def emit_sync_offset_sample(
        self,
        session_id: str,
        node_id: str,
        sync_offset_us: float,
        threshold_us: float = 150.0,
        timestamp: Optional[str] = None,
    ) -> SyncOffsetSampleEvent:
        """Emits SYNC_OFFSET_SAMPLE event for real-time live chart display."""
        evt = SyncOffsetSampleEvent(
            node_id=node_id,
            sync_offset_us=sync_offset_us,
            threshold_us=threshold_us,
            timestamp=timestamp or utc_now_iso(),
        )
        await self.broadcast_event(session_id, evt)
        return evt

    async def emit_tool_call_lifecycle(
        self,
        session_id: str,
        tool_call_id: str,
        tool_name: str,
        args: Dict[str, Any],
        result: Dict[str, Any],
    ) -> List[StreamingEvent]:
        """Emits full TOOL_CALL lifecycle sequence (START -> ARGS -> END -> RESULT)."""
        events: List[StreamingEvent] = [
            ToolCallStartEvent(toolCallId=tool_call_id, toolCallName=tool_name),
            ToolCallArgsEvent(toolCallId=tool_call_id, delta=json.dumps(args)),
            ToolCallEndEvent(toolCallId=tool_call_id),
            ToolCallResultEvent(toolCallId=tool_call_id, content=json.dumps(result)),
        ]
        for evt in events:
            await self.broadcast_event(session_id, evt)
        return events

    async def emit_reasoning_stream(
        self,
        session_id: str,
        message_id: str,
        deltas: List[str],
    ) -> List[StreamingEvent]:
        """Emits native reasoning thinking sequence (START -> CONTENT* -> END)."""
        events: List[StreamingEvent] = [
            ReasoningStartEvent(messageId=message_id),
            ReasoningMessageStartEvent(messageId=message_id),
        ]
        for delta in deltas:
            events.append(ReasoningMessageContentEvent(messageId=message_id, delta=delta))
        events.append(ReasoningMessageEndEvent(messageId=message_id))
        events.append(ReasoningEndEvent())

        for evt in events:
            await self.broadcast_event(session_id, evt)
        return events


# Singleton instance for system-wide use
_GLOBAL_BRIDGE = AGUIEventBridge()


def get_event_bridge() -> AGUIEventBridge:
    """Returns the shared AGUIEventBridge singleton."""
    return _GLOBAL_BRIDGE
