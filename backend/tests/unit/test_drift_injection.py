"""Unit tests for live drift injection endpoint and simulator dispatch.

Verifies:
1. POST /sessions/{session_id}/inject-drift strict Pydantic V2 schema validation and 202 response.
2. State mutation for active_drift_events in checkpoint storage.
3. Real-time AGUIEventBridge event broadcasts (SYNC_OFFSET_SAMPLE, STEP_STARTED, TOOL_CALL_*, REASONING_*, STATE_DELTA, RUN_PAUSED).
4. Execution of 7-node workflow runner (run_reasoning_loop) on complex scenario resulting in HITL pause.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.state.checkpointing import load_checkpoint, save_checkpoint
from src.state.schema import GenlockSentinelState, SessionStatus
from src.ui.agui_bridge import get_event_bridge
from src.agents.reasoning_loop import reset_reasoning_loop_trackers


@pytest.fixture(autouse=True)
def reset_trackers(monkeypatch):
    """Ensure cycle cap trackers are clean and force mock for deterministic unit tests."""
    monkeypatch.setenv("GENLOCK_SENTINEL_FORCE_MOCK", "true")
    reset_reasoning_loop_trackers()
    yield
    reset_reasoning_loop_trackers()


@pytest.mark.asyncio
async def test_inject_drift_endpoint_validation_and_202():
    """Verifies that POST /sessions/{session_id}/inject-drift accepts valid payload and returns 202."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "event_id": "test-drift-inject-001",
            "node_id": "render-07",
            "frame_id": "f-10001",
            "breach_ts": "2026-09-09T08:00:00Z",
            "sync_offset_us": 195.5,
            "threshold_us": 150.0,
            "category_hint": "network_jitter",
            "mock_loki_lines": ["sync handshake retry node=render-07"],
            "mock_tempo_spans": [{"service": "render-07", "duration_ms": 320}],
        }

        resp = await client.post(
            "/sessions/test-session-inject-01/inject-drift",
            json=payload,
        )

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["session_id"] == "test-session-inject-01"
        assert data["event_id"] == "test-drift-inject-001"

        # Verify state was checkpointed with the drift event
        saved_state = await load_checkpoint("test-session-inject-01")
        assert saved_state is not None
        assert "render-07" in saved_state.active_drift_events
        evt = saved_state.active_drift_events["render-07"]
        assert evt.node_id == "render-07"
        assert evt.sync_offset_us == 195.5


@pytest.mark.asyncio
async def test_inject_drift_extra_fields_forbidden():
    """Verifies strict extra='forbid' rejection on unknown fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "event_id": "test-drift-invalid-001",
            "node_id": "render-07",
            "frame_id": "f-10001",
            "breach_ts": "2026-09-09T08:00:00Z",
            "sync_offset_us": 195.5,
            "threshold_us": 150.0,
            "category_hint": "network_jitter",
            "unknown_field": "disallowed",
        }

        resp = await client.post(
            "/sessions/test-session-invalid/inject-drift",
            json=payload,
        )
        assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_inject_drift_complex_scenario_emits_all_ui_events_and_pauses():
    """Verifies that injecting a complex drift event triggers run_reasoning_loop,

    emitting SYNC_OFFSET_SAMPLE, STEP_STARTED, TOOL_CALL_*, REASONING_*, STATE_DELTA,
    and pauses at HITL Approval Modal (RUN_PAUSED).
    """
    session_id = "test-session-complex-stream"
    bridge = get_event_bridge()
    subscriber_queue = await bridge.register_subscriber(session_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "event_id": "drift-complex-e2e-001",
            "node_id": "render-12",
            "frame_id": "f-91004",
            "breach_ts": "2026-09-09T08:15:00Z",
            "sync_offset_us": 210.0,
            "threshold_us": 150.0,
            "category_hint": "ambiguous",
            "mock_loki_lines": ["GPU throttling detected; junction temp 94C"],
            "mock_tempo_spans": [{"service": "render-12", "status": "error"}],
        }

        # Use wait=true to synchronously await the reasoning loop execution
        resp = await client.post(
            f"/sessions/{session_id}/inject-drift?wait=true",
            json=payload,
        )
        assert resp.status_code == 202

    # Collect all emitted SSE events
    emitted_raw: List[str] = []
    while not subscriber_queue.empty():
        emitted_raw.append(subscriber_queue.get_nowait())

    await bridge.unregister_subscriber(session_id, subscriber_queue)

    joined_stream = "\n".join(emitted_raw)

    # 1. Verify SYNC_OFFSET_SAMPLE
    assert "SYNC_OFFSET_SAMPLE" in joined_stream
    assert "210.0" in joined_stream or "210" in joined_stream
    assert "render-12" in joined_stream

    # 2. Verify STEP_STARTED
    assert "STEP_STARTED" in joined_stream
    assert "evidence_triage" in joined_stream
    assert "root_cause_correlation" in joined_stream
    assert "hitl_card_generation" in joined_stream
    assert "hitl_pause" in joined_stream

    # 3. Verify TOOL_CALL_*
    assert "TOOL_CALL_START" in joined_stream
    assert "query_loki_logs" in joined_stream

    # 4. Verify REASONING_* (Gemini thinking stream)
    assert "REASONING_MESSAGE_CONTENT" in joined_stream

    # 5. Verify STATE_DELTA
    assert "STATE_DELTA" in joined_stream
    assert "active_drift_events" in joined_stream
    assert "pending_hitl_card" in joined_stream

    # 6. Verify RUN_PAUSED (blocking HITL modal trigger)
    assert "RUN_PAUSED" in joined_stream

    # Verify state in storage shows awaiting_approval with pending card
    state = await load_checkpoint(session_id)
    assert state is not None
    assert state.session_status == SessionStatus.AWAITING_APPROVAL
    assert state.pending_hitl_card is not None
    assert state.pending_hitl_card.event_id == "drift-complex-e2e-001"


@pytest.mark.asyncio
async def test_inject_drift_simple_scenario_autonomous_remediation():
    """Verifies that injecting a simple drift event executes autonomous remediation."""
    session_id = "test-session-simple-stream"
    bridge = get_event_bridge()
    subscriber_queue = await bridge.register_subscriber(session_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "event_id": "drift-simple-e2e-001",
            "node_id": "render-07",
            "frame_id": "f-88213",
            "breach_ts": "2026-09-09T08:20:00Z",
            "sync_offset_us": 185.4,
            "threshold_us": 150.0,
            "category_hint": "network_jitter",
            "mock_loki_lines": ["sync handshake retry node=render-07"],
            "mock_tempo_spans": [{"service": "render-07", "duration_ms": 340}],
        }

        resp = await client.post(
            f"/sessions/{session_id}/inject-drift?wait=true",
            json=payload,
        )
        assert resp.status_code == 202

    emitted_raw: List[str] = []
    while not subscriber_queue.empty():
        emitted_raw.append(subscriber_queue.get_nowait())

    await bridge.unregister_subscriber(session_id, subscriber_queue)
    joined_stream = "\n".join(emitted_raw)

    assert "autonomous_dispatch" in joined_stream
    assert "remediation_log" in joined_stream
    assert "RUN_FINISHED" in joined_stream

    state = await load_checkpoint(session_id)
    assert state is not None
    assert len(state.remediation_log) > 0
    assert state.remediation_log[-1].node_id == "render-07"


@pytest.mark.asyncio
async def test_simulate_drift_script_dispatch(monkeypatch):
    """Verifies that scripts/simulate_drift.py emit_drift_event forwards to HTTP endpoint."""
    from scripts.simulate_drift import SCENARIOS, emit_drift_event

    posted_payloads: List[Dict[str, Any]] = []

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, timeout=None):
            posted_payloads.append({"url": url, "json": json})
            from httpx import Response
            return Response(status_code=202, text='{"status":"accepted"}')

    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)

    payload = SCENARIOS["complex"]
    target_url = "http://localhost:8000/sessions/test-stage-01/inject-drift"
    await emit_drift_event(payload, destination_url=target_url)

    assert len(posted_payloads) == 1
    assert posted_payloads[0]["url"] == target_url
    assert posted_payloads[0]["json"]["event_id"] == "drift-evt-complex-002"
    assert posted_payloads[0]["json"]["node_id"] == "render-12"

