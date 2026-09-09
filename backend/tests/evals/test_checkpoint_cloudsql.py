"""Genlock Sentinel — Checkpoint & Cloud SQL Durability Evaluation Suite.

Verifies checkpointing requirements per AGENT_MASTER_PLAN.md Section 9.2 & Step 19:
1. DatabaseSessionService lifecycle with Cloud SQL PostgreSQL and SQLite URLs.
2. Checkpoint write/read/resume round-trip with full 10-field GenlockSentinelState.
3. Crash-and-resume simulation verifying state recovery across session boundaries.
4. Reducer preservation and serialization fidelity.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4
import pytest

from src.state.checkpointing import (
    create_session_service,
    get_database_url,
    init_checkpoint_db,
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
    utc_now_iso,
)
from tests.mocks.test_data import (
    COMPLEX_CASE_DRIFT_EVENT,
    SIMPLE_CASE_DRIFT_EVENT,
    create_initial_test_state,
)


@pytest.fixture
def temp_db_url(tmp_path: Path) -> str:
    """Provides an isolated async SQLite database URL for checkpoint durability testing."""
    db_file = tmp_path / "sentinel_eval_checkpoints.db"
    return f"sqlite+aiosqlite:///{db_file.as_posix()}"


class TestCheckpointDurabilityEvals:
    """Evaluates checkpoint persistence, crash recovery, and database connection handling."""

    def test_database_url_resolution(self, monkeypatch):
        """Verifies resolution of Cloud SQL and SQLite URLs from environment variables."""
        # Cloud SQL PostgreSQL URL
        cloud_sql_url = "postgresql+asyncpg://sentinel_app:secret@10.20.30.40:5432/genlock_prod"
        monkeypatch.setenv("ADK_SESSION_DB_URL", "")
        monkeypatch.setenv("CLOUD_SQL_POSTGRES_URL", cloud_sql_url)
        assert get_database_url() == cloud_sql_url

        # ADK Session DB URL override
        sqlite_override = "sqlite+aiosqlite:///C:/data/custom_sessions.db"
        monkeypatch.setenv("ADK_SESSION_DB_URL", sqlite_override)
        assert get_database_url() == sqlite_override

    @pytest.mark.asyncio
    async def test_checkpoint_roundtrip_all_ten_state_fields(self, temp_db_url: str):
        """Verifies that all 10 GenlockSentinelState fields serialize and deserialize

        without data loss or schema drift across a durable database checkpoint.
        """
        svc = create_session_service(db_url=temp_db_url)
        await init_checkpoint_db(session_service=svc)

        session_id = "session-eval-durability-001"
        now = utc_now_iso()

        full_state = GenlockSentinelState(
            session_id=session_id,
            session_status=SessionStatus.MONITORING,
            config=RuntimeConfig(
                sync_offset_threshold_us=100.0,
                financial_threshold_usd=1000.0,
                confidence_floor=0.85,
            ),
            active_drift_events={
                "render-07": SIMPLE_CASE_DRIFT_EVENT,
                "render-12": COMPLEX_CASE_DRIFT_EVENT,
            },
            evidence_bundle={
                "evt-simple-001": EvidenceRefs(
                    event_id="evt-simple-001",
                    node_id="render-07",
                    logs_available=True,
                    log_summary="Sync handshake retry",
                    trace_summary="340ms frame_render",
                )
            },
            diagnosis_history=[
                DiagnosisRecord(
                    event_id="evt-simple-001",
                    node_id="render-07",
                    category="network_jitter",
                    confidence=0.94,
                    rationale="Verified per query_loki_logs",
                    timestamp=now,
                )
            ],
            pending_hitl_card=HITLCard(
                card_id="card-eval-001",
                event_id="evt-complex-002",
                node_id="render-12",
                escalation_reason="ambiguous_diagnosis",
                proposed_action="halt_live_take",
                cost_delta_estimate="$1,850.00",
                visual_impact_score="High",
                root_cause_summary="Ambiguous telemetry",
                created_at=now,
            ),
            approval_state=ApprovalStatus.APPROVED,
            remediation_log=[
                RemediationAction(
                    action_id="act-eval-001",
                    event_id="evt-simple-001",
                    node_id="render-07",
                    action_taken="failover_cluster_leadership",
                    timestamp=now,
                    success=True,
                    details={"node_id": "render-07"},
                )
            ],
            error_logs=[
                ErrorRecord(
                    error_id="err-eval-001",
                    event_id="evt-edge-003",
                    error_type="TimeoutError",
                    message="Loki query timed out after 3 retries",
                    timestamp=now,
                )
            ],
        )

        # Save checkpoint to database
        saved_session = await save_checkpoint(
            session_id=session_id,
            state=full_state,
            session_service=svc,
        )
        assert saved_session is not None

        # Load checkpoint back from database
        recovered_state = await load_checkpoint(
            session_id=session_id,
            session_service=svc,
        )
        assert recovered_state is not None

        # Verify exact field fidelity across all 10 fields
        assert recovered_state.session_id == session_id
        assert recovered_state.session_status == SessionStatus.MONITORING
        assert recovered_state.config.sync_offset_threshold_us == 100.0
        assert recovered_state.config.financial_threshold_usd == 1000.0
        assert len(recovered_state.active_drift_events) == 2
        assert "render-07" in recovered_state.active_drift_events
        assert "render-12" in recovered_state.active_drift_events
        assert len(recovered_state.evidence_bundle) == 1
        assert len(recovered_state.diagnosis_history) == 1
        assert recovered_state.diagnosis_history[0].category == "network_jitter"
        assert recovered_state.pending_hitl_card is not None
        assert recovered_state.pending_hitl_card.card_id == "card-eval-001"
        assert recovered_state.approval_state == ApprovalStatus.APPROVED
        assert len(recovered_state.remediation_log) == 1
        assert recovered_state.remediation_log[0].action_taken == "failover_cluster_leadership"
        assert len(recovered_state.error_logs) == 1
        assert recovered_state.error_logs[0].error_type == "TimeoutError"

    @pytest.mark.asyncio
    async def test_simulated_crash_and_resume_recovery(self, temp_db_url: str):
        """Simulates agent host process crash mid-workflow and verifies state recovery

        from database checkpoint upon session resumption.
        """
        # Session service instance 1 (before crash)
        svc1 = create_session_service(db_url=temp_db_url)
        await init_checkpoint_db(session_service=svc1)

        session_id = "session-crash-recovery-001"
        initial_state = create_initial_test_state(session_id=session_id)

        # Mutate state with new active drift and diagnosis
        state_after_step2 = reduce_state(
            initial_state,
            {
                "evidence_bundle": {
                    "evt-simple-001": EvidenceRefs(
                        event_id="evt-simple-001",
                        node_id="render-07",
                        logs_available=True,
                        log_summary="Sync handshake retry",
                        trace_summary="340ms frame_render",
                    )
                }
            },
        )
        state_after_step3 = reduce_state(
            state_after_step2,
            {
                "diagnosis_history": [
                    DiagnosisRecord(
                        event_id="evt-simple-001",
                        node_id="render-07",
                        category="network_jitter",
                        confidence=0.94,
                        rationale="Verified per query_loki_logs",
                        timestamp=utc_now_iso(),
                    )
                ]
            },
        )

        # Checkpoint saved before crash
        await save_checkpoint(session_id=session_id, state=state_after_step3, session_service=svc1)

        # SIMULATE CRASH: discard svc1, create fresh connection pool svc2
        del svc1
        svc2 = create_session_service(db_url=temp_db_url)

        # Resume from checkpoint
        resumed_state = await load_checkpoint(session_id=session_id, session_service=svc2)

        assert resumed_state is not None
        assert resumed_state.session_id == session_id
        assert len(resumed_state.diagnosis_history) == 1
        assert resumed_state.diagnosis_history[0].category == "network_jitter"
        assert "evt-simple-001" in resumed_state.evidence_bundle

    @pytest.mark.asyncio
    async def test_live_cloudsql_postgresql_checkpoint_roundtrip(self):
        """Verifies live Cloud SQL PostgreSQL connectivity, table preparation, and

        100% roundtrip persistence of all 10 GenlockSentinelState fields.
        """
        if os.environ.get("GENLOCK_SENTINEL_FORCE_MOCK") == "true":
            pytest.skip("Skipping live Cloud SQL roundtrip in fast mock mode")

        db_url = get_database_url()
        if not db_url.startswith("postgresql"):
            pytest.skip("Skipping live Cloud SQL test: ADK_SESSION_DB_URL is not PostgreSQL")

        svc = create_session_service(db_url=db_url)
        await init_checkpoint_db(session_service=svc)

        session_id = f"session-live-cloudsql-{uuid4().hex[:8]}"
        now = utc_now_iso()

        full_state = GenlockSentinelState(
            session_id=session_id,
            session_status=SessionStatus.MONITORING,
            config=RuntimeConfig(
                sync_offset_threshold_us=100.0,
                financial_threshold_usd=1000.0,
                confidence_floor=0.85,
            ),
            active_drift_events={
                "render-07": SIMPLE_CASE_DRIFT_EVENT,
                "render-12": COMPLEX_CASE_DRIFT_EVENT,
            },
            evidence_bundle={
                "evt-simple-001": EvidenceRefs(
                    event_id="evt-simple-001",
                    node_id="render-07",
                    logs_available=True,
                    log_summary="Sync handshake retry",
                    trace_summary="340ms frame_render",
                )
            },
            diagnosis_history=[
                DiagnosisRecord(
                    event_id="evt-simple-001",
                    node_id="render-07",
                    category="network_jitter",
                    confidence=0.94,
                    rationale="Verified per query_loki_logs",
                    timestamp=now,
                )
            ],
            pending_hitl_card=HITLCard(
                card_id="card-live-001",
                event_id="evt-complex-002",
                node_id="render-12",
                escalation_reason="ambiguous_diagnosis",
                proposed_action="halt_live_take",
                cost_delta_estimate="$1,850.00",
                visual_impact_score="High",
                root_cause_summary="Live Cloud SQL test card",
                created_at=now,
            ),
            approval_state=ApprovalStatus.APPROVED,
            remediation_log=[
                RemediationAction(
                    action_id="act-live-001",
                    event_id="evt-simple-001",
                    node_id="render-07",
                    action_taken="failover_cluster_leadership",
                    timestamp=now,
                    success=True,
                    details={"node_id": "render-07"},
                )
            ],
            error_logs=[
                ErrorRecord(
                    error_id="err-live-001",
                    event_id="evt-edge-003",
                    error_type="TimeoutError",
                    message="Loki query timed out after 3 retries",
                    timestamp=now,
                )
            ],
        )

        # Save checkpoint to live PostgreSQL
        saved_session = await save_checkpoint(
            session_id=session_id,
            state=full_state,
            session_service=svc,
        )
        assert saved_session is not None

        # Load checkpoint back from live PostgreSQL
        recovered_state = await load_checkpoint(
            session_id=session_id,
            session_service=svc,
        )
        assert recovered_state is not None

        # Verify exact field fidelity across all 10 fields
        assert recovered_state.session_id == session_id
        assert recovered_state.session_status == SessionStatus.MONITORING
        assert recovered_state.config.sync_offset_threshold_us == 100.0
        assert recovered_state.config.financial_threshold_usd == 1000.0
        assert len(recovered_state.active_drift_events) == 2
        assert "render-07" in recovered_state.active_drift_events
        assert "render-12" in recovered_state.active_drift_events
        assert len(recovered_state.evidence_bundle) == 1
        assert len(recovered_state.diagnosis_history) == 1
        assert recovered_state.diagnosis_history[0].category == "network_jitter"
        assert recovered_state.pending_hitl_card is not None
        assert recovered_state.pending_hitl_card.card_id == "card-live-001"
        assert recovered_state.approval_state == ApprovalStatus.APPROVED
        assert len(recovered_state.remediation_log) == 1
        assert recovered_state.remediation_log[0].action_taken == "failover_cluster_leadership"
        assert len(recovered_state.error_logs) == 1
        assert recovered_state.error_logs[0].error_type == "TimeoutError"
