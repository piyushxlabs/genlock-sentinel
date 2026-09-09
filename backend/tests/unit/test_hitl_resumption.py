"""Unit and Integration Tests for HITL Graph-Resumption Coordinator.

Verifies Section 7, Section 9.3, and Section 10 Step 16 requirements:
  - Valid Approve flow resuming from HITL Pause and executing the approved tool
    (halt_live_take, fallback_to_greenscreen, execute_threshold_exceeding_failover).
  - Valid Deny flow with audit logging in error_logs and remediation_log,
    asserting zero actuator tools fire and session_status returns to monitoring.
  - Stale and mismatched checkpoint_id rejection (HTTP 400).
  - Event ID mismatch rejection (HTTP 400).
  - Modified input refusal (HTTP 400).
  - Nonexistent session rejection (HTTP 404).
  - No pending HITL card rejection (HTTP 400).
  - RUN_PAUSED event emission and state delta broadcasts.
  - ADK LongRunningFunctionTool configuration.
  - End-to-end FastAPI endpoint integration via ASGITransport.
"""

import asyncio
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.state.checkpointing import load_checkpoint, save_checkpoint
from src.state.schema import (
    ApprovalStatus,
    DriftEvent,
    GenlockSentinelState,
    HITLCard,
    SessionStatus,
)
from src.ui.agui_bridge import get_event_bridge
from src.ui.hitl_resumption import (
    DecisionRequest,
    DecisionResponse,
    HITLResumptionCoordinator,
    get_hitl_coordinator,
    hitl_supervisor_approval_tool,
)


@pytest.fixture
def test_client() -> AsyncClient:
    """Creates an async test client for the FastAPI application."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _create_sample_card(
    event_id: str = "evt-complex-01",
    node_id: str = "render-07",
    proposed_action: str = "halt_live_take",
) -> HITLCard:
    """Helper to instantiate a valid HITLCard for testing."""
    return HITLCard(
        card_id=f"card-{event_id}",
        event_id=event_id,
        node_id=node_id,
        escalation_reason="take_halt_required",
        proposed_action=proposed_action,
        cost_delta_estimate="$2,450 for the estimated 1-minute halt",
        visual_impact_score="high — defect would otherwise be captured on camera",
        root_cause_summary="Persistent sync-offset breach exceeding hardware threshold on render-07.",
    )


# ------------------------------------------------------------------------------
# 1. Valid Approve Flow Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hitl_coordinator_approve_halt_live_take() -> None:
    """Approve payload resumes graph, executes halt_live_take, logs action, and updates state."""
    coordinator = get_hitl_coordinator()
    session_id = "sess-approve-halt"
    event_id = "evt-halt-01"

    card = _create_sample_card(event_id=event_id, proposed_action="halt_live_take")
    drift = DriftEvent(
        event_id=event_id,
        node_id="render-07",
        frame_id="f-100",
        breach_ts="2026-09-09T12:00:00Z",
        sync_offset_us=210.0,
        threshold_us=150.0,
        status="detected",
    )
    state = GenlockSentinelState(
        session_id=session_id,
        session_status=SessionStatus.AWAITING_APPROVAL,
        approval_state=ApprovalStatus.PENDING,
        pending_hitl_card=card,
        active_drift_events={"render-07": drift},
    )
    await save_checkpoint(session_id=session_id, state=state)

    req = DecisionRequest(
        action="approve",
        checkpoint_id=f"hitl_pause::{event_id}",
    )

    response = await coordinator.handle_decision(
        session_id=session_id,
        event_id=event_id,
        payload=req,
    )

    assert response.status == "accepted"
    assert response.action == "approve"
    assert response.approval_state == "approved"
    assert response.event_id == event_id
    assert response.checkpoint_id == f"hitl_pause::{event_id}"
    assert response.post_approval_result is not None
    assert response.post_approval_result["action_taken"] == "halt_live_take"
    assert response.post_approval_result["success"] is True

    # Verify state saved in checkpoint store
    saved_state = await load_checkpoint(session_id=session_id)
    assert saved_state is not None
    assert saved_state.approval_state == ApprovalStatus.APPROVED
    assert saved_state.session_status == SessionStatus.MONITORING
    assert saved_state.pending_hitl_card is None
    assert "render-07" not in saved_state.active_drift_events

    # Verify remediation_log has approval audit and executed tool
    actions = [a.action_taken for a in saved_state.remediation_log]
    assert any("supervisor_approved::halt_live_take" in a for a in actions)
    assert any("halt_live_take" in a for a in actions)


@pytest.mark.asyncio
async def test_hitl_coordinator_approve_fallback_to_greenscreen() -> None:
    """Approve payload resumes graph and executes fallback_to_greenscreen."""
    coordinator = get_hitl_coordinator()
    session_id = "sess-approve-greenscreen"
    event_id = "evt-gs-01"

    card = _create_sample_card(event_id=event_id, proposed_action="fallback_to_greenscreen")
    state = GenlockSentinelState(
        session_id=session_id,
        session_status=SessionStatus.AWAITING_APPROVAL,
        approval_state=ApprovalStatus.PENDING,
        pending_hitl_card=card,
    )
    await save_checkpoint(session_id=session_id, state=state)

    req = DecisionRequest(
        action="approve",
        checkpoint_id=card.card_id,  # using card_id format
    )

    response = await coordinator.handle_decision(
        session_id=session_id,
        event_id=event_id,
        payload=req,
    )

    assert response.status == "accepted"
    assert response.approval_state == "approved"
    assert response.post_approval_result is not None
    assert response.post_approval_result["action_taken"] == "fallback_to_greenscreen"
    assert response.post_approval_result["success"] is True

    saved_state = await load_checkpoint(session_id=session_id)
    assert saved_state is not None
    assert any("fallback_to_greenscreen" in a.action_taken for a in saved_state.remediation_log)


@pytest.mark.asyncio
async def test_hitl_coordinator_approve_threshold_exceeding_failover() -> None:
    """Approve payload resumes graph and executes execute_threshold_exceeding_failover."""
    coordinator = get_hitl_coordinator()
    session_id = "sess-approve-failover"
    event_id = "evt-failover-01"

    card = _create_sample_card(
        event_id=event_id,
        proposed_action="execute_threshold_exceeding_failover",
    )
    state = GenlockSentinelState(
        session_id=session_id,
        session_status=SessionStatus.AWAITING_APPROVAL,
        approval_state=ApprovalStatus.PENDING,
        pending_hitl_card=card,
    )
    await save_checkpoint(session_id=session_id, state=state)

    req = DecisionRequest(
        action="approve",
        checkpoint_id=event_id,  # using event_id format
    )

    response = await coordinator.handle_decision(
        session_id=session_id,
        event_id=event_id,
        payload=req,
    )

    assert response.status == "accepted"
    assert response.approval_state == "approved"
    assert response.post_approval_result is not None
    assert response.post_approval_result["action_taken"] == "execute_threshold_exceeding_failover"
    assert response.post_approval_result["success"] is True

    saved_state = await load_checkpoint(session_id=session_id)
    assert saved_state is not None
    assert any(
        "execute_threshold_exceeding_failover" in a.action_taken
        for a in saved_state.remediation_log
    )


# ------------------------------------------------------------------------------
# 2. Valid Deny Flow Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hitl_coordinator_deny_flow_audit_logging() -> None:
    """Deny payload logs denial to error_logs and remediation_log, fires no tools, returns to monitoring."""
    coordinator = get_hitl_coordinator()
    session_id = "sess-deny-audit"
    event_id = "evt-deny-01"

    card = _create_sample_card(event_id=event_id, proposed_action="halt_live_take")
    drift = DriftEvent(
        event_id=event_id,
        node_id="render-07",
        frame_id="f-100",
        breach_ts="2026-09-09T12:00:00Z",
        sync_offset_us=210.0,
        threshold_us=150.0,
        status="detected",
    )
    state = GenlockSentinelState(
        session_id=session_id,
        session_status=SessionStatus.AWAITING_APPROVAL,
        approval_state=ApprovalStatus.PENDING,
        pending_hitl_card=card,
        active_drift_events={"render-07": drift},
    )
    await save_checkpoint(session_id=session_id, state=state)

    deny_reason = "Director signaled live take is wrapping; manual reset preferred."
    req = DecisionRequest(
        action="deny",
        checkpoint_id=f"hitl_pause::{event_id}",
        reason=deny_reason,
    )

    response = await coordinator.handle_decision(
        session_id=session_id,
        event_id=event_id,
        payload=req,
    )

    assert response.status == "accepted"
    assert response.action == "deny"
    assert response.approval_state == "denied"
    assert response.post_approval_result is not None
    assert response.post_approval_result["action_taken"] == "denied_halt_live_take"
    assert response.post_approval_result["success"] is False

    # Verify state saved in checkpoint store
    saved_state = await load_checkpoint(session_id=session_id)
    assert saved_state is not None
    assert saved_state.approval_state == ApprovalStatus.DENIED
    assert saved_state.session_status == SessionStatus.MONITORING
    assert saved_state.pending_hitl_card is None
    assert "render-07" not in saved_state.active_drift_events

    # Assert zero action tools fired (no halt_live_take success record)
    assert not any(
        a.action_taken == "halt_live_take" and a.success is True
        for a in saved_state.remediation_log
    )

    # Assert error_logs contains SupervisorDenial
    assert len(saved_state.error_logs) == 1
    error_entry = saved_state.error_logs[0]
    assert error_entry.error_type == "SupervisorDenial"
    assert error_entry.event_id == event_id
    assert deny_reason in error_entry.message

    # Assert remediation_log contains denial record
    denial_actions = [
        a for a in saved_state.remediation_log
        if a.action_taken == "supervisor_denied::halt_live_take"
    ]
    assert len(denial_actions) == 1
    assert denial_actions[0].success is False
    assert denial_actions[0].details["reason"] == deny_reason


# ------------------------------------------------------------------------------
# 3. Defensive Validation & Error Handling Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hitl_coordinator_rejects_modified_inputs() -> None:
    """Rejects decision payload with non-null modified_inputs (400 Bad Request)."""
    coordinator = get_hitl_coordinator()
    session_id = "sess-mod-input"
    event_id = "evt-mod-01"

    card = _create_sample_card(event_id=event_id)
    state = GenlockSentinelState(
        session_id=session_id,
        pending_hitl_card=card,
    )
    await save_checkpoint(session_id=session_id, state=state)

    req = DecisionRequest(
        action="approve",
        checkpoint_id=f"hitl_pause::{event_id}",
        modified_inputs={"cost_delta_estimate": "$0"},
    )

    with pytest.raises(HTTPException) as exc_info:
        await coordinator.handle_decision(
            session_id=session_id,
            event_id=event_id,
            payload=req,
        )

    assert exc_info.value.status_code == 400
    assert "Modifying inputs is not permitted" in exc_info.value.detail


@pytest.mark.asyncio
async def test_hitl_coordinator_rejects_missing_session() -> None:
    """Returns 404 when session_id does not exist in checkpoint store."""
    coordinator = get_hitl_coordinator()
    req = DecisionRequest(
        action="approve",
        checkpoint_id="hitl_pause::e-nonexistent",
    )

    with pytest.raises(HTTPException) as exc_info:
        await coordinator.handle_decision(
            session_id="nonexistent-session-id",
            event_id="e-nonexistent",
            payload=req,
        )

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_hitl_coordinator_rejects_no_pending_card() -> None:
    """Returns 400 when session has no pending HITL card."""
    coordinator = get_hitl_coordinator()
    session_id = "sess-no-card"
    event_id = "evt-no-card"

    clean_state = GenlockSentinelState(session_id=session_id, pending_hitl_card=None)
    await save_checkpoint(session_id=session_id, state=clean_state)

    req = DecisionRequest(
        action="approve",
        checkpoint_id=f"hitl_pause::{event_id}",
    )

    with pytest.raises(HTTPException) as exc_info:
        await coordinator.handle_decision(
            session_id=session_id,
            event_id=event_id,
            payload=req,
        )

    assert exc_info.value.status_code == 400
    assert "No pending HITL card" in exc_info.value.detail


@pytest.mark.asyncio
async def test_hitl_coordinator_rejects_event_id_mismatch() -> None:
    """Returns 400 when URL event_id does not match pending card event_id."""
    coordinator = get_hitl_coordinator()
    session_id = "sess-evt-mismatch"
    actual_event = "evt-actual-99"

    card = _create_sample_card(event_id=actual_event)
    state = GenlockSentinelState(session_id=session_id, pending_hitl_card=card)
    await save_checkpoint(session_id=session_id, state=state)

    req = DecisionRequest(
        action="approve",
        checkpoint_id=f"hitl_pause::{actual_event}",
    )

    with pytest.raises(HTTPException) as exc_info:
        await coordinator.handle_decision(
            session_id=session_id,
            event_id="evt-wrong-param",
            payload=req,
        )

    assert exc_info.value.status_code == 400
    assert "Event ID mismatch" in exc_info.value.detail


@pytest.mark.asyncio
async def test_hitl_coordinator_rejects_stale_checkpoint_id() -> None:
    """Returns 400 when checkpoint_id does not match the pending card."""
    coordinator = get_hitl_coordinator()
    session_id = "sess-stale-ckpt"
    event_id = "evt-current-12"

    card = _create_sample_card(event_id=event_id)
    state = GenlockSentinelState(session_id=session_id, pending_hitl_card=card)
    await save_checkpoint(session_id=session_id, state=state)

    req = DecisionRequest(
        action="approve",
        checkpoint_id="hitl_pause::stale-prior-event",
    )

    with pytest.raises(HTTPException) as exc_info:
        await coordinator.handle_decision(
            session_id=session_id,
            event_id=event_id,
            payload=req,
        )

    assert exc_info.value.status_code == 400
    assert "Checkpoint ID mismatch" in exc_info.value.detail


# ------------------------------------------------------------------------------
# 4. RUN_PAUSED Emission & LongRunningFunctionTool Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notify_paused_emits_run_paused_and_state_deltas() -> None:
    """notify_paused emits RUN_PAUSED event and broadcasts pending card deltas."""
    bridge = get_event_bridge()
    coordinator = HITLResumptionCoordinator(bridge=bridge)

    session_id = "sess-pause-notif"
    run_id = "run-test-pause-01"
    event_id = "evt-pause-01"
    card = _create_sample_card(event_id=event_id)

    # Subscribe to bridge queue
    q = await bridge.register_subscriber(session_id)

    event = await coordinator.notify_paused(
        session_id=session_id,
        run_id=run_id,
        card=card,
        reason="hitl_approval_required",
    )

    assert event.type == "RUN_PAUSED"
    assert event.runId == run_id
    assert event.reason == "hitl_approval_required"

    # Read events from subscriber queue
    received_frames = []
    while not q.empty():
        received_frames.append(q.get_nowait())

    await bridge.unregister_subscriber(session_id, q)

    assert len(received_frames) >= 3
    all_raw = " ".join(received_frames)
    assert "STATE_DELTA" in all_raw
    assert "pending_hitl_card" in all_raw
    assert "RUN_PAUSED" in all_raw


def test_long_running_function_tool_properties() -> None:
    """Verifies that hitl_supervisor_approval_tool is configured as a LongRunningFunctionTool."""
    assert hitl_supervisor_approval_tool.is_long_running is True
    declaration = hitl_supervisor_approval_tool._get_declaration()
    assert declaration is not None
    assert "NOTE: This is a long-running operation" in declaration.description


# ------------------------------------------------------------------------------
# 5. FastAPI End-to-End Endpoint Integration
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_decision_endpoint_e2e_approve(test_client: AsyncClient) -> None:
    """E2E test: POST /sessions/{session_id}/events/{event_id}/decision approve flow."""
    session_id = "sess-e2e-approve"
    event_id = "evt-e2e-01"
    card = _create_sample_card(event_id=event_id, proposed_action="halt_live_take")

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
        assert data["post_approval_result"]["action_taken"] == "halt_live_take"
        assert data["post_approval_result"]["success"] is True

    # Checkpoint verification
    saved_state = await load_checkpoint(session_id=session_id)
    assert saved_state is not None
    assert saved_state.approval_state == ApprovalStatus.APPROVED
    assert saved_state.session_status == SessionStatus.MONITORING


@pytest.mark.asyncio
async def test_api_decision_endpoint_e2e_deny(test_client: AsyncClient) -> None:
    """E2E test: POST /sessions/{session_id}/events/{event_id}/decision deny flow."""
    session_id = "sess-e2e-deny"
    event_id = "evt-e2e-02"
    card = _create_sample_card(event_id=event_id, proposed_action="fallback_to_greenscreen")

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
                "checkpoint_id": card.card_id,
                "reason": "Director opted to keep shooting in current mode.",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["action"] == "deny"
        assert data["approval_state"] == "denied"
        assert data["post_approval_result"]["action_taken"] == "denied_fallback_to_greenscreen"
        assert data["post_approval_result"]["success"] is False

    # Checkpoint verification
    saved_state = await load_checkpoint(session_id=session_id)
    assert saved_state is not None
    assert saved_state.approval_state == ApprovalStatus.DENIED
    assert saved_state.session_status == SessionStatus.MONITORING
    assert len(saved_state.error_logs) == 1
    assert "Director opted" in saved_state.error_logs[0].message


@pytest.mark.asyncio
async def test_hitl_coordinator_approve_proposed_action_none(test_client: AsyncClient) -> None:
    """Verifies that approving a card where proposed_action is 'none' completes as an acknowledgement

    without raising PostApprovalExecutionError, logs to remediation_log, and returns session to monitoring.
    """
    session_id = "sess-approve-none"
    event_id = "evt-none-01"
    card = _create_sample_card(event_id=event_id, proposed_action="none")

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
                "action": "approve",
                "checkpoint_id": card.card_id,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["action"] == "approve"
        assert data["approval_state"] == "approved"
        assert data["post_approval_result"]["action_taken"] == "supervisor_acknowledged"
        assert data["post_approval_result"]["success"] is True

    # Checkpoint verification
    saved_state = await load_checkpoint(session_id=session_id)
    assert saved_state is not None
    assert saved_state.approval_state == ApprovalStatus.APPROVED
    assert saved_state.session_status == SessionStatus.MONITORING
    assert len(saved_state.remediation_log) >= 1
    actions = [r.action_taken for r in saved_state.remediation_log]
    assert "supervisor_acknowledged" in actions


@pytest.mark.asyncio
async def test_hitl_coordinator_approve_proposed_action_contains_none(test_client: AsyncClient) -> None:
    """Verifies that approving a card where proposed_action contains 'none' (e.g. 'none (diagnostic pause)')

    completes cleanly as supervisor_acknowledged without raising PostApprovalExecutionError.
    """
    session_id = "sess-approve-contains-none"
    event_id = "evt-contains-none-02"
    card = _create_sample_card(event_id=event_id, proposed_action="none (diagnostic pause)")

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
                "action": "approve",
                "checkpoint_id": card.card_id,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["post_approval_result"]["action_taken"] == "supervisor_acknowledged"

    saved_state = await load_checkpoint(session_id=session_id)
    assert saved_state is not None
    assert saved_state.session_status == SessionStatus.MONITORING

