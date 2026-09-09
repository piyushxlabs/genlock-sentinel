"""Genlock Sentinel — Unit Test Suite for Typed AG-UI SSE Streaming Layer.

Verifies complete implementation per AGENT_MASTER_PLAN.md Section 7, Section 10 Step 15,
and INTERFACE_OBSERVABILITY_SYSTEM.md Section 2 & 2a:
  - Strict Pydantic V2 schemas for all nine Section 7 event types.
  - RFC 6902 JSON Patch state delta generation across all three reducer types.
  - ADK 2.x Event projection to AG-UI typed events.
  - SSE wire formatting (`data: <json>\\n\\n`).
  - Pub/sub broadcasting across concurrent subscribers.
  - FastAPI SSE streaming endpoint `GET /sessions/{session_id}/stream`.
"""

import asyncio
import json
from typing import Any, Dict, List
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from src.main import app
from src.state.checkpointing import save_checkpoint
from src.state.schema import (
    ApprovalStatus,
    DriftEvent,
    ErrorRecord,
    EvidenceBundleExtraction,
    GenlockSentinelState,
    RemediationAction,
    RootCauseDiagnosis,
    SessionStatus,
    utc_now_iso,
)
from src.ui.agui_bridge import AGUIEventBridge, get_event_bridge
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
    StepStartedEvent,
    StreamingEvent,
    SyncOffsetSampleEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)


# ------------------------------------------------------------------------------
# 1. Verification of Nine Event Types (Schemas, Validation, Serialization)
# ------------------------------------------------------------------------------

class TestTypedEventSchemas:
    """Validates schemas, strict extra="forbid", and serialization for all event types."""

    def test_run_lifecycle_events(self) -> None:
        # RUN_STARTED
        evt1 = RunStartedEvent(runId="run_001", threadId="sess_001")
        assert evt1.type == "RUN_STARTED"
        assert evt1.runId == "run_001"
        assert evt1.threadId == "sess_001"
        data1 = json.loads(evt1.model_dump_json())
        assert data1["type"] == "RUN_STARTED"

        # RUN_PAUSED
        evt2 = RunPausedEvent(runId="run_001", reason="hitl_approval_required")
        assert evt2.type == "RUN_PAUSED"
        assert evt2.reason == "hitl_approval_required"

        # RUN_FINISHED
        evt3 = RunFinishedEvent(runId="run_001")
        assert evt3.type == "RUN_FINISHED"

        # RUN_ERROR
        evt4 = RunErrorEvent(message="Loki connection timeout after 3 retries", code="TELEMETRY_SOURCE_EXHAUSTED")
        assert evt4.type == "RUN_ERROR"
        assert evt4.code == "TELEMETRY_SOURCE_EXHAUSTED"

    def test_step_progress_events(self) -> None:
        # STEP_STARTED
        evt1 = StepStartedEvent(step_name="evidence_triage", event_id="f-88213")
        assert evt1.type == "STEP_STARTED"
        assert evt1.step_name == "evidence_triage"
        assert evt1.event_id == "f-88213"

        # STEP_FINISHED
        evt2 = StepFinishedEvent(step_name="root_cause_correlation", event_id="f-88213")
        assert evt2.type == "STEP_FINISHED"
        assert evt2.step_name == "root_cause_correlation"

        # Rejects invalid step_name
        with pytest.raises(ValidationError):
            StepStartedEvent(step_name="unregistered_node", event_id="f-88213")  # type: ignore[arg-type]

    def test_tool_call_lifecycle_events(self) -> None:
        # TOOL_CALL_START
        evt1 = ToolCallStartEvent(toolCallId="call_001", toolCallName="query_loki_logs")
        assert evt1.type == "TOOL_CALL_START"
        assert evt1.toolCallName == "query_loki_logs"

        # TOOL_CALL_ARGS
        args_payload = json.dumps({"datasource_uid": "loki-prod", "logql": "{node=\"render-07\"}"})
        evt2 = ToolCallArgsEvent(toolCallId="call_001", delta=args_payload)
        assert evt2.type == "TOOL_CALL_ARGS"
        assert "render-07" in evt2.delta

        # TOOL_CALL_END
        evt3 = ToolCallEndEvent(toolCallId="call_001")
        assert evt3.type == "TOOL_CALL_END"

        # TOOL_CALL_RESULT
        result_payload = json.dumps({"success": True, "result": ["log line 1"], "error": None})
        evt4 = ToolCallResultEvent(toolCallId="call_001", content=result_payload)
        assert evt4.type == "TOOL_CALL_RESULT"
        assert "log line 1" in evt4.content

    def test_reasoning_stream_events(self) -> None:
        evt1 = ReasoningStartEvent(messageId="msg_001")
        assert evt1.type == "REASONING_START"

        evt2 = ReasoningMessageStartEvent(messageId="msg_001")
        assert evt2.type == "REASONING_MESSAGE_START"

        evt3 = ReasoningMessageContentEvent(messageId="msg_001", delta="Weighing network RTT against thermal...")
        assert evt3.type == "REASONING_MESSAGE_CONTENT"
        assert "RTT" in evt3.delta

        evt4 = ReasoningMessageEndEvent(messageId="msg_001")
        assert evt4.type == "REASONING_MESSAGE_END"

        evt5 = ReasoningEndEvent()
        assert evt5.type == "REASONING_END"

    def test_state_delta_and_snapshot_events(self) -> None:
        # STATE_DELTA
        op = StateDeltaOp(op="add", path="/diagnosis_history/-", value={"category": "network_jitter"})
        evt1 = StateDeltaEvent(delta=[op])
        assert evt1.type == "STATE_DELTA"
        assert len(evt1.delta) == 1
        assert evt1.delta[0].path == "/diagnosis_history/-"

        # STATE_SNAPSHOT
        evt2 = StateSnapshotEvent(session_id="sess_001", state={"session_status": "monitoring"})
        assert evt2.type == "STATE_SNAPSHOT"
        assert evt2.session_id == "sess_001"

    def test_sync_offset_sample_event(self) -> None:
        evt = SyncOffsetSampleEvent(
            node_id="render-07",
            sync_offset_us=182.4,
            threshold_us=150.0,
            timestamp=utc_now_iso(),
        )
        assert evt.type == "SYNC_OFFSET_SAMPLE"
        assert evt.sync_offset_us == 182.4

    def test_strict_schema_rejection_of_unrecognized_fields(self) -> None:
        with pytest.raises(ValidationError):
            RunStartedEvent(runId="r1", threadId="t1", unauthorized_field="bad")  # type: ignore[call-arg]


# ------------------------------------------------------------------------------
# 2. State Delta RFC 6902 Reducer Projection Tests
# ------------------------------------------------------------------------------

class TestStateDeltaProjection:
    """Verifies that AGUIEventBridge generates RFC 6902 ops matching declared reducers."""

    def test_append_only_reducer_projection(self) -> None:
        bridge = AGUIEventBridge()
        diag = RootCauseDiagnosis(
            event_id="f-88213",
            category="network_jitter",
            confidence=0.92,
            rationale="RTT spike detected in Loki logs at 14:02:11Z",
        )
        delta_event = bridge.build_state_delta(
            field_name="diagnosis_history",
            reducer_type="append-only",
            value=diag,
        )
        assert len(delta_event.delta) == 1
        op = delta_event.delta[0]
        assert op.op == "add"
        assert op.path == "/diagnosis_history/-"
        assert op.value["category"] == "network_jitter"
        assert op.value["confidence"] == 0.92

    def test_merge_by_key_reducer_projection(self) -> None:
        bridge = AGUIEventBridge()
        drift = DriftEvent(
            event_id="f-88213",
            node_id="render-07",
            frame_id="f-88213",
            breach_ts=utc_now_iso(),
            sync_offset_us=185.0,
            threshold_us=150.0,
        )
        delta_event = bridge.build_state_delta(
            field_name="active_drift_events",
            reducer_type="merge-by-key",
            value=drift,
            key="f-88213",
        )
        assert len(delta_event.delta) == 1
        op = delta_event.delta[0]
        assert op.op == "add"
        assert op.path == "/active_drift_events/f-88213"
        assert op.value["node_id"] == "render-07"
        assert op.value["sync_offset_us"] == 185.0

    def test_last_write_wins_reducer_projection(self) -> None:
        bridge = AGUIEventBridge()
        delta_event = bridge.build_state_delta(
            field_name="approval_state",
            reducer_type="last-write-wins",
            value=ApprovalStatus.APPROVED,
        )
        assert len(delta_event.delta) == 1
        op = delta_event.delta[0]
        assert op.op == "replace"
        assert op.path == "/approval_state"
        assert op.value == "approved"

    def test_missing_key_for_merge_by_key_raises_error(self) -> None:
        bridge = AGUIEventBridge()
        with pytest.raises(ValueError, match="requires a non-empty key"):
            bridge.build_state_delta(
                field_name="evidence_bundle",
                reducer_type="merge-by-key",
                value={"summary": "test"},
                key=None,
            )


# ------------------------------------------------------------------------------
# 3. Wire Formatting and Pub/Sub Tests
# ------------------------------------------------------------------------------

class TestBridgeWireAndPubSub:
    """Verifies SSE line serialization and in-memory broadcaster subscription."""

    def test_format_sse_event_from_pydantic_model(self) -> None:
        evt = RunStartedEvent(runId="r-100", threadId="s-100")
        wire_str = AGUIEventBridge.format_sse_event(evt)
        assert wire_str.startswith("data: ")
        assert wire_str.endswith("\n\n")
        assert '"type":"RUN_STARTED"' in wire_str.replace(" ", "")

    def test_format_sse_event_from_dict(self) -> None:
        raw_dict = {"type": "CUSTOM", "payload": 123}
        wire_str = AGUIEventBridge.format_sse_event(raw_dict)
        assert wire_str.startswith("data: ")
        assert wire_str.endswith("\n\n")
        assert '"type": "CUSTOM"' in wire_str

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_subscribers(self) -> None:
        bridge = AGUIEventBridge()
        session_id = "test_broadcast_sess"

        q1 = await bridge.register_subscriber(session_id)
        q2 = await bridge.register_subscriber(session_id)

        evt = StepStartedEvent(step_name="stream_watch", event_id="f-1")
        await bridge.broadcast_event(session_id, evt)

        line1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        line2 = await asyncio.wait_for(q2.get(), timeout=1.0)

        assert "STEP_STARTED" in line1
        assert "STEP_STARTED" in line2

        await bridge.unregister_subscriber(session_id, q1)
        await bridge.unregister_subscriber(session_id, q2)


# ------------------------------------------------------------------------------
# 4. ADK Workflow Event Projection Tests
# ------------------------------------------------------------------------------

class TestADKEventProjection:
    """Verifies projection of ADK 2.x Event objects into typed AG-UI events."""

    def test_project_adk_node_entry(self) -> None:
        class MockADKEvent:
            node_name = "evidence_triage"

        bridge = AGUIEventBridge()
        events = bridge.project_adk_event(MockADKEvent(), session_id="s1", target_event_id="e1")  # type: ignore[arg-type]
        assert len(events) == 1
        assert isinstance(events[0], StepStartedEvent)
        assert events[0].step_name == "evidence_triage"
        assert events[0].event_id == "e1"

    def test_project_adk_function_calls(self) -> None:
        class MockFunctionCall:
            id = "call_123"
            name = "query_loki_logs"
            args = {"logql": "{node=\"render-07\"}"}

        class MockADKEvent:
            node_name = None

            def get_function_calls(self) -> List[Any]:
                return [MockFunctionCall()]

        bridge = AGUIEventBridge()
        events = bridge.project_adk_event(MockADKEvent(), session_id="s1", target_event_id="e1")  # type: ignore[arg-type]
        assert len(events) == 3
        assert isinstance(events[0], ToolCallStartEvent)
        assert events[0].toolCallName == "query_loki_logs"
        assert isinstance(events[1], ToolCallArgsEvent)
        assert "render-07" in events[1].delta
        assert isinstance(events[2], ToolCallEndEvent)

    def test_project_adk_function_responses(self) -> None:
        class MockFunctionResponse:
            id = "call_123"
            name = "query_loki_logs"
            response = {"success": True, "result": ["ok"]}

        class MockADKEvent:
            node_name = None

            def get_function_responses(self) -> List[Any]:
                return [MockFunctionResponse()]

        bridge = AGUIEventBridge()
        events = bridge.project_adk_event(MockADKEvent(), session_id="s1", target_event_id="e1")  # type: ignore[arg-type]
        assert len(events) == 1
        assert isinstance(events[0], ToolCallResultEvent)
        assert events[0].toolCallId == "call_123"
        assert "ok" in events[0].content


# ------------------------------------------------------------------------------
# 5. FastAPI SSE Streaming Endpoint Tests
# ------------------------------------------------------------------------------

class TestFastAPISSEEndpoint:
    """Verifies live streaming via GET /sessions/{session_id}/stream."""

    @pytest.mark.asyncio
    async def test_sse_stream_receives_broadcast_events(self) -> None:
        session_id = "sess_sse_test_001"
        bridge = get_event_bridge()

        sample_evt = SyncOffsetSampleEvent(
            node_id="render-07",
            sync_offset_us=165.2,
            threshold_us=150.0,
            timestamp=utc_now_iso(),
        )

        async def _run_stream_test() -> List[str]:
            # Broadcast sample_evt in a background task as soon as subscription appears
            async def _delayed_bcast():
                for _ in range(50):
                    await asyncio.sleep(0.01)
                    async with bridge._lock:
                        if session_id in bridge._subscribers and len(bridge._subscribers[session_id]) > 0:
                            break
                await bridge.broadcast_event(session_id, sample_evt)

            bcast_task = asyncio.create_task(_delayed_bcast())
            transport = ASGITransport(app=app)
            received_lines: List[str] = []
            try:
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    async with client.stream("GET", f"/sessions/{session_id}/stream?max_events=2") as response:
                        assert response.status_code == 200
                        assert "text/event-stream" in response.headers["content-type"]
                        assert response.headers["cache-control"] == "no-cache"

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                received_lines.append(line)
                                break
            finally:
                if not bcast_task.done():
                    bcast_task.cancel()
            return received_lines

        lines = await asyncio.wait_for(_run_stream_test(), timeout=3.0)
        assert len(lines) >= 1
        assert "SYNC_OFFSET_SAMPLE" in lines[0]
        assert "render-07" in lines[0]

    @pytest.mark.asyncio
    async def test_sse_stream_emits_initial_state_snapshot_on_reconnect(self) -> None:
        session_id = "sess_reconnect_test_002"
        # Seed an existing checkpoint for this session
        existing_state = GenlockSentinelState(
            session_id=session_id,
            session_status=SessionStatus.MONITORING,
            approval_state=ApprovalStatus.PENDING,
        )
        await save_checkpoint(session_id=session_id, state=existing_state)

        async def _run_reconnect_test() -> List[str]:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                async with client.stream("GET", f"/sessions/{session_id}/stream?max_events=2") as response:
                    assert response.status_code == 200
                    received_lines: List[str] = []
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            received_lines.append(line)
                            break
                    return received_lines

        lines = await asyncio.wait_for(_run_reconnect_test(), timeout=3.0)
        assert len(lines) >= 1
        assert "STATE_SNAPSHOT" in lines[0]
        assert session_id in lines[0]
