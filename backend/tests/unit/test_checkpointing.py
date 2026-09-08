"""Unit Tests for Genlock Sentinel Checkpointing Backend.

Verifies durable checkpoint save/load/resume round-trip per
AGENT_MASTER_PLAN.md Section 4, Step 4, Section 9.2, and Section 10, Step 8:
  - Database initialization (prepare_tables)
  - Full 10-field GenlockSentinelState serialization & reconstruction round-trip
  - Checkpoint state updates across graph execution steps
  - Deletion and listing of checkpoints
  - Graceful handling of nonexistent sessions
"""

import os
import tempfile
from pathlib import Path
import pytest
from google.adk.sessions import DatabaseSessionService

from src.state.checkpointing import (
    create_session_service,
    delete_checkpoint,
    get_database_url,
    init_checkpoint_db,
    list_checkpoints,
    load_checkpoint,
    save_checkpoint,
)
from src.state.reducers import reduce_state
from src.state.schema import (
    ApprovalStatus,
    DiagnosisRecord,
    DriftEvent,
    ErrorRecord,
    EvidenceRefs,
    GenlockSentinelState,
    HITLCard,
    RemediationAction,
    RuntimeConfig,
    SessionStatus,
)


@pytest.fixture
def temp_db_service() -> DatabaseSessionService:
    """Provides an isolated temporary SQLite database session service for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = Path(tf.name).resolve().as_posix()

    db_url = f"sqlite+aiosqlite:///{temp_path}"
    svc = create_session_service(db_url=db_url)

    yield svc

    # Cleanup temporary database file
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception:
        pass


def test_database_url_resolution() -> None:
    """Verifies that database URL resolves to an async driver (aiosqlite or asyncpg)."""
    url = get_database_url()
    assert (
        url.startswith("sqlite+aiosqlite:///")
        or url.startswith("postgresql+asyncpg://")
    ), f"Expected async database driver, got: {url}"


@pytest.mark.asyncio
async def test_init_checkpoint_db(temp_db_service: DatabaseSessionService) -> None:
    """Verifies that prepare_tables initializes checkpoint tables without error."""
    initialized_svc = await init_checkpoint_db(session_service=temp_db_service)
    assert initialized_svc is not None
    await initialized_svc.close()


@pytest.mark.asyncio
async def test_checkpoint_save_and_load_roundtrip(temp_db_service: DatabaseSessionService) -> None:
    """Verifies complete 100% round-trip fidelity of all 10 state fields."""
    session_id = "shoot-ckpt-roundtrip-01"

    original_state = GenlockSentinelState(
        session_id=session_id,
        session_status=SessionStatus.TRIAGING,
        active_drift_events={
            "render-07": DriftEvent(
                event_id="evt-roundtrip-01",
                node_id="render-07",
                frame_id="f-9988",
                breach_ts="2026-09-08T15:30:00Z",
                sync_offset_us=195.4,
                threshold_us=150.0,
                status="triaged",
            )
        },
        evidence_bundle={
            "evt-roundtrip-01": EvidenceRefs(
                event_id="evt-roundtrip-01",
                node_id="render-07",
                logs_available=True,
                log_summary="Sync handshake retry confirmed on node render-07",
                trace_summary="Tempo barrier duration 340ms status warning",
                anomaly=None,
            )
        },
        diagnosis_history=[
            DiagnosisRecord(
                event_id="evt-roundtrip-01",
                node_id="render-07",
                category="network_jitter",
                confidence=0.94,
                rationale="Loki logs and Tempo traces align on cluster sync latency",
            )
        ],
        remediation_log=[
            RemediationAction(
                event_id="evt-roundtrip-01",
                node_id="render-07",
                action_taken="failover_cluster_leadership",
                success=True,
                details={"standby_node": "render-08"},
            )
        ],
        pending_hitl_card=HITLCard(
            event_id="evt-roundtrip-01",
            node_id="render-07",
            escalation_reason="ambiguous_diagnosis",
            proposed_action="halt_live_take",
            cost_delta_estimate="$1,500/min take hold",
            visual_impact_score="High",
            root_cause_summary="Sync offset exceeded visual tolerance threshold",
        ),
        approval_state=ApprovalStatus.PENDING,
        error_logs=[
            ErrorRecord(
                event_id="evt-roundtrip-01",
                node_id="render-07",
                error_type="TransientMCPTimeout",
                message="Initial Loki query timed out; retry succeeded",
            )
        ],
        config=RuntimeConfig(
            confidence_floor=0.80,
            financial_threshold_usd=1000.0,
            query_window_max_seconds=90,
            max_tool_retries=3,
            sync_offset_threshold_us=120.0,
        ),
    )

    # 1. Save checkpoint
    saved_session = await save_checkpoint(
        session_id=session_id,
        state=original_state,
        user_id="supervisor-01",
        session_service=temp_db_service,
    )
    assert saved_session.id == session_id

    # 2. Load checkpoint and verify exact field values
    loaded_state = await load_checkpoint(
        session_id=session_id,
        user_id="supervisor-01",
        session_service=temp_db_service,
    )

    assert loaded_state is not None
    assert loaded_state.session_id == original_state.session_id
    assert loaded_state.session_status == SessionStatus.TRIAGING
    assert "render-07" in loaded_state.active_drift_events
    assert loaded_state.active_drift_events["render-07"].sync_offset_us == 195.4
    assert "evt-roundtrip-01" in loaded_state.evidence_bundle
    assert loaded_state.evidence_bundle["evt-roundtrip-01"].logs_available is True
    assert len(loaded_state.diagnosis_history) == 1
    assert loaded_state.diagnosis_history[0].category == "network_jitter"
    assert len(loaded_state.remediation_log) == 1
    assert loaded_state.remediation_log[0].action_taken == "failover_cluster_leadership"
    assert loaded_state.pending_hitl_card is not None
    assert loaded_state.pending_hitl_card.proposed_action == "halt_live_take"
    assert loaded_state.approval_state == ApprovalStatus.PENDING
    assert len(loaded_state.error_logs) == 1
    assert loaded_state.config.financial_threshold_usd == 1000.0

    await temp_db_service.close()


@pytest.mark.asyncio
async def test_checkpoint_update_across_steps(temp_db_service: DatabaseSessionService) -> None:
    """Verifies that checkpoints update cleanly as state evolves across execution steps."""
    session_id = "shoot-step-evolution-02"

    initial_state = GenlockSentinelState(session_id=session_id)
    await save_checkpoint(
        session_id=session_id,
        state=initial_state,
        session_service=temp_db_service,
    )

    # Step 1: Detect breach
    drift_event = DriftEvent(
        event_id="evt-evo-01",
        node_id="render-12",
        frame_id="f-500",
        breach_ts="2026-09-08T16:00:00Z",
        sync_offset_us=215.0,
    )
    s1 = reduce_state(
        initial_state,
        {
            "session_status": SessionStatus.TRIAGING,
            "active_drift_events": {"render-12": drift_event},
        },
    )
    await save_checkpoint(session_id=session_id, state=s1, session_service=temp_db_service)

    # Step 2: Correlate diagnosis and enter HITL pause
    card = HITLCard(
        event_id="evt-evo-01",
        node_id="render-12",
        escalation_reason="take_halt_required",
        proposed_action="halt_live_take",
        cost_delta_estimate="$2,000/min burn",
        visual_impact_score="Critical",
        root_cause_summary="Irrecoverable thermal throttling on node render-12",
    )
    s2 = reduce_state(
        s1,
        {
            "session_status": SessionStatus.AWAITING_APPROVAL,
            "pending_hitl_card": card,
            "approval_state": ApprovalStatus.PENDING,
        },
    )
    await save_checkpoint(session_id=session_id, state=s2, session_service=temp_db_service)

    # Verify reload reflects the final step
    restored = await load_checkpoint(session_id=session_id, session_service=temp_db_service)
    assert restored is not None
    assert restored.session_status == SessionStatus.AWAITING_APPROVAL
    assert restored.pending_hitl_card is not None
    assert restored.pending_hitl_card.escalation_reason == "take_halt_required"
    assert "render-12" in restored.active_drift_events

    await temp_db_service.close()


@pytest.mark.asyncio
async def test_checkpoint_nonexistent_returns_none(temp_db_service: DatabaseSessionService) -> None:
    """Verifies that requesting a nonexistent checkpoint gracefully returns None."""
    loaded = await load_checkpoint(
        session_id="ghost-session-9999",
        session_service=temp_db_service,
    )
    assert loaded is None
    await temp_db_service.close()


@pytest.mark.asyncio
async def test_checkpoint_deletion_and_listing(temp_db_service: DatabaseSessionService) -> None:
    """Verifies listing and deleting session checkpoints."""
    s1_id = "session-to-list-01"
    s2_id = "session-to-list-02"

    state1 = GenlockSentinelState(session_id=s1_id)
    state2 = GenlockSentinelState(session_id=s2_id)

    await save_checkpoint(session_id=s1_id, state=state1, session_service=temp_db_service)
    await save_checkpoint(session_id=s2_id, state=state2, session_service=temp_db_service)

    sessions = await list_checkpoints(session_service=temp_db_service)
    assert s1_id in sessions
    assert s2_id in sessions

    # Delete s1
    deleted = await delete_checkpoint(session_id=s1_id, session_service=temp_db_service)
    assert deleted is True

    # Confirm s1 is gone
    after_deletion = await list_checkpoints(session_service=temp_db_service)
    assert s1_id not in after_deletion
    assert s2_id in after_deletion
    assert await load_checkpoint(session_id=s1_id, session_service=temp_db_service) is None

    await temp_db_service.close()
