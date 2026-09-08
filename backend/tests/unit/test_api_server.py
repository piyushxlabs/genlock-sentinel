"""Unit Tests for Genlock Sentinel FastAPI Backend API & Endpoints.

Verifies FastAPI endpoints per AGENT_MASTER_PLAN.md Section 7, Section 8, and Section 10 Step 14:
  - GET /health and GET /healthz readiness endpoints
  - GET / metadata endpoint
  - POST /sessions/{session_id}/events/{event_id}/decision (Approve, Deny, malformed payloads, mismatched checkpoints)
  - POST /sessions/{session_id}/stop emergency stop endpoint
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.state.checkpointing import load_checkpoint, save_checkpoint
from src.state.schema import (
    ApprovalStatus,
    GenlockSentinelState,
    HITLCard,
    SessionStatus,
)


@pytest.fixture
def test_client() -> AsyncClient:
    """Creates an async test client for the FastAPI application."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ------------------------------------------------------------------------------
# Health & Metadata Endpoints
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_healthz_and_health_endpoints(test_client: AsyncClient) -> None:
    """Verifies both /health and /healthz endpoints respond with healthy status."""
    async with test_client as client:
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        data_health = res_health.json()
        assert data_health["status"] == "healthy"
        assert data_health["app_name"] == "genlock_sentinel"
        assert data_health["streaming_mode"] == "SSE"

        res_healthz = await client.get("/healthz")
        assert res_healthz.status_code == 200
        data_healthz = res_healthz.json()
        assert data_healthz["status"] == "healthy"
        assert data_healthz["app_name"] == "genlock_sentinel"


@pytest.mark.asyncio
async def test_root_metadata_endpoint(test_client: AsyncClient) -> None:
    """Verifies GET / returns service metadata."""
    async with test_client as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Genlock Sentinel"
        assert data["status"] == "online"


# ------------------------------------------------------------------------------
# Decision Endpoint: Malformed & Invalid Payloads
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_decision_endpoint_rejects_malformed_payload(test_client: AsyncClient) -> None:
    """Rejects payload with invalid action or extra fields with HTTP 422."""
    async with test_client as client:
        # Invalid action literal
        res_invalid_action = await client.post(
            "/sessions/s-01/events/e-01/decision",
            json={"action": "maybe", "checkpoint_id": "hitl_pause::e-01"},
        )
        assert res_invalid_action.status_code == 422

        # Extra forbidden field (extra="forbid")
        res_extra_field = await client.post(
            "/sessions/s-01/events/e-01/decision",
            json={
                "action": "approve",
                "checkpoint_id": "hitl_pause::e-01",
                "unauthorized_field": "hack",
            },
        )
        assert res_extra_field.status_code == 422


@pytest.mark.asyncio
async def test_decision_endpoint_rejects_modified_inputs(test_client: AsyncClient) -> None:
    """Rejects decision with non-null modified_inputs (no editable fields per spec)."""
    async with test_client as client:
        res = await client.post(
            "/sessions/s-01/events/e-01/decision",
            json={
                "action": "approve",
                "checkpoint_id": "hitl_pause::e-01",
                "modified_inputs": {"cost_delta_estimate": "$0"},
            },
        )
        assert res.status_code == 400
        assert "Modifying inputs is not permitted" in res.json()["detail"]


@pytest.mark.asyncio
async def test_decision_endpoint_session_not_found(test_client: AsyncClient) -> None:
    """Returns 404 when session_id does not exist in checkpoint store."""
    async with test_client as client:
        res = await client.post(
            "/sessions/nonexistent-session/events/e-01/decision",
            json={"action": "approve", "checkpoint_id": "hitl_pause::e-01"},
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_decision_endpoint_no_pending_card(test_client: AsyncClient) -> None:
    """Returns 400 when session exists but has no pending HITL card."""
    session_id = "sess-no-card"
    clean_state = GenlockSentinelState(session_id=session_id, pending_hitl_card=None)
    await save_checkpoint(session_id=session_id, state=clean_state)

    async with test_client as client:
        res = await client.post(
            f"/sessions/{session_id}/events/e-01/decision",
            json={"action": "approve", "checkpoint_id": "hitl_pause::e-01"},
        )
        assert res.status_code == 400
        assert "No pending HITL card" in res.json()["detail"]


@pytest.mark.asyncio
async def test_decision_endpoint_event_and_checkpoint_mismatch(test_client: AsyncClient) -> None:
    """Returns 400 when event_id or checkpoint_id does not match pending card."""
    session_id = "sess-mismatch"
    card = HITLCard(
        card_id="card-100",
        event_id="evt-expected",
        node_id="render-07",
        escalation_reason="take_halt_required",
        proposed_action="halt_live_take",
        cost_delta_estimate="$25,000",
        visual_impact_score="critical",
        root_cause_summary="Frame sync loss",
    )
    state = GenlockSentinelState(
        session_id=session_id,
        approval_state=ApprovalStatus.PENDING,
        pending_hitl_card=card,
    )
    await save_checkpoint(session_id=session_id, state=state)

    async with test_client as client:
        # Event ID mismatch
        res_wrong_event = await client.post(
            f"/sessions/{session_id}/events/evt-wrong/decision",
            json={"action": "approve", "checkpoint_id": "hitl_pause::evt-expected"},
        )
        assert res_wrong_event.status_code == 400
        assert "Event ID mismatch" in res_wrong_event.json()["detail"]

        # Checkpoint ID mismatch
        res_wrong_checkpoint = await client.post(
            f"/sessions/{session_id}/events/evt-expected/decision",
            json={"action": "approve", "checkpoint_id": "hitl_pause::wrong-checkpoint"},
        )
        assert res_wrong_checkpoint.status_code == 400
        assert "Checkpoint ID mismatch" in res_wrong_checkpoint.json()["detail"]


# ------------------------------------------------------------------------------
# Decision Endpoint: Valid Approve & Deny Cycles
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_decision_endpoint_approve_cycle(test_client: AsyncClient) -> None:
    """Approve payload updates approval_state, resumes session, and persists checkpoint."""
    session_id = "sess-approve-flow"
    event_id = "evt-sync-200"
    card = HITLCard(
        card_id="card-200",
        event_id=event_id,
        node_id="render-07",
        escalation_reason="take_halt_required",
        proposed_action="halt_live_take",
        cost_delta_estimate="$25,000",
        visual_impact_score="critical",
        root_cause_summary="Persisted frame tear",
    )
    state = GenlockSentinelState(
        session_id=session_id,
        session_status=SessionStatus.AWAITING_APPROVAL,
        approval_state=ApprovalStatus.PENDING,
        pending_hitl_card=card,
    )
    await save_checkpoint(session_id=session_id, state=state)

    async with test_client as client:
        res = await client.post(
            f"/sessions/{session_id}/events/{event_id}/decision",
            json={"action": "approve", "checkpoint_id": f"hitl_pause::{event_id}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["action"] == "approve"
        assert data["approval_state"] == "approved"
        assert data["session_id"] == session_id
        assert data["event_id"] == event_id

    # Verify state in checkpoint storage
    updated_state = await load_checkpoint(session_id=session_id)
    assert updated_state is not None
    assert updated_state.approval_state == ApprovalStatus.APPROVED
    assert updated_state.session_status == SessionStatus.RESUMED
    assert any("supervisor_approved::halt_live_take" in a.action_taken for a in updated_state.remediation_log)


@pytest.mark.asyncio
async def test_decision_endpoint_deny_cycle(test_client: AsyncClient) -> None:
    """Deny payload updates approval_state, returns to monitoring, and logs reason."""
    session_id = "sess-deny-flow"
    event_id = "evt-sync-300"
    card = HITLCard(
        card_id="card-300",
        event_id=event_id,
        node_id="render-12",
        escalation_reason="threshold_exceeded",
        proposed_action="execute_threshold_exceeding_failover",
        cost_delta_estimate="$10,000",
        visual_impact_score="medium",
        root_cause_summary="Secondary node drift",
    )
    state = GenlockSentinelState(
        session_id=session_id,
        session_status=SessionStatus.AWAITING_APPROVAL,
        approval_state=ApprovalStatus.PENDING,
        pending_hitl_card=card,
    )
    await save_checkpoint(session_id=session_id, state=state)

    async with test_client as client:
        res = await client.post(
            f"/sessions/{session_id}/events/{event_id}/decision",
            json={
                "action": "deny",
                "checkpoint_id": f"hitl_pause::{event_id}",
                "reason": "Director called cut manually.",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["action"] == "deny"
        assert data["approval_state"] == "denied"

    # Verify state in checkpoint storage
    updated_state = await load_checkpoint(session_id=session_id)
    assert updated_state is not None
    assert updated_state.approval_state == ApprovalStatus.DENIED
    assert updated_state.session_status == SessionStatus.MONITORING
    assert any("Director called cut manually" in log.message for log in updated_state.error_logs)
    assert any("supervisor_denied" in a.action_taken for a in updated_state.remediation_log)


# ------------------------------------------------------------------------------
# Emergency Stop Endpoint
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stop_session_endpoint_halts_active_session(test_client: AsyncClient) -> None:
    """Emergency stop transitions status to stopped, halts approvals, and checkpoints state."""
    session_id = "sess-emergency-stop"
    active_state = GenlockSentinelState(
        session_id=session_id,
        session_status=SessionStatus.MONITORING,
        approval_state=ApprovalStatus.PENDING,
    )
    await save_checkpoint(session_id=session_id, state=active_state)

    async with test_client as client:
        res = await client.post(
            f"/sessions/{session_id}/stop",
            json={
                "reason": "Stage safety incident",
                "supervisor_id": "dp_supervisor",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "stopped"
        assert data["session_id"] == session_id
        assert "halted immediately" in data["message"]

    # Verify checkpoint persistence
    halted_state = await load_checkpoint(session_id=session_id)
    assert halted_state is not None
    assert halted_state.session_status == SessionStatus.STOPPED
    assert halted_state.approval_state == ApprovalStatus.HALTED
    assert any("Stage safety incident" in log.message for log in halted_state.error_logs)


@pytest.mark.asyncio
async def test_stop_session_endpoint_rejects_malformed_payload(test_client: AsyncClient) -> None:
    """Rejects stop payload with extra forbidden fields."""
    async with test_client as client:
        res = await client.post(
            "/sessions/any-session/stop",
            json={"unknown_field": "disallowed"},
        )
        assert res.status_code == 422
