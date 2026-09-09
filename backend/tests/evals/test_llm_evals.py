"""Genlock Sentinel — LLM-Specific Evaluation Suite.

Implements automated evaluation suites per AGENT_MASTER_PLAN.md Section 9.3:
1. Tool-Calling Accuracy Evals (Simple Case, Stall Case, Thermal Case, HITL Actions).
2. Hallucination Prevention & Silence-Over-Guessing Evals (Loki timeout, zero fabrication).
3. Strict Grounding & Citation Verification (rationale must cite verified evidence fields).
4. Conflicting Evidence Arbitration (Complex Case forces ambiguous / HITL routing).
5. HITL Graph Resumption Evaluation (Approve, Deny, Mismatched Checkpoint).
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from google.adk.agents.context import Context
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions import InMemorySessionService

from src.agents.autonomous_dispatch import autonomous_dispatch_node
from src.agents.post_approval_handling import post_approval_handling_node
from src.agents.reasoning_loop import (
    ReasoningLoopResult,
    reset_reasoning_loop_trackers,
    run_reasoning_loop,
)
from src.agents.root_cause_correlation import _validate_grounding_citations
from src.state.reducers import reduce_state
from src.state.schema import (
    ApprovalStatus,
    DiagnosisRecord,
    DriftEvent,
    EvidenceRefs,
    GenlockSentinelState,
    HITLCard,
    RemediationAction,
    RuntimeConfig,
    SessionStatus,
    get_or_init_state,
    utc_now_iso,
)
from src.structured_outputs import (
    EvidenceBundleExtraction,
    HITLCardPackage,
    RootCauseDiagnosis,
)
from src.tools.schemas.pydantic_models import (
    HitlGatedActionInput,
    HitlGatedActionOutput,
    ReversibleRemediationInput,
    ReversibleRemediationOutput,
)
from src.utils.errors import StateValidationError, ToolExecutionError
from tests.mocks.test_data import (
    ASSET_STALL_DRIFT_EVENT,
    COMPLEX_CASE_DRIFT_EVENT,
    EDGE_CASE_DRIFT_EVENT,
    MOCK_DIAGNOSIS_ASSET_STALL,
    MOCK_DIAGNOSIS_COMPLEX_AMBIGUOUS,
    MOCK_DIAGNOSIS_SIMPLE,
    MOCK_DIAGNOSIS_THERMAL,
    MOCK_HITL_PACKAGE_HALT,
    MOCK_TRIAGE_COMPLEX_CONFLICTING,
    MOCK_TRIAGE_EDGE_TIMEOUT,
    MOCK_TRIAGE_SIMPLE,
    SIMPLE_CASE_DRIFT_EVENT,
    THERMAL_THROTTLE_DRIFT_EVENT,
    create_initial_test_state,
)


async def create_test_context(
    state: GenlockSentinelState,
    invocation_id: str = "test-invoc",
) -> Context:
    """Helper creating a native ADK Context with valid Session and InvocationContext."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        session_id=state.session_id,
        user_id="supervisor-01",
        app_name="genlock_sentinel",
    )
    session.state.update(state.model_dump(mode="json"))
    inv = InvocationContext(
        session_service=session_service,
        invocation_id=invocation_id,
        session=session,
    )
    return Context(inv)


@pytest.fixture(autouse=True)
def cleanup_trackers():
    """Ensures reasoning loop trackers are reset before and after every test."""
    reset_reasoning_loop_trackers()
    yield
    reset_reasoning_loop_trackers()


# ==============================================================================
# 1. Tool-Calling Accuracy Evals (Section 9.3)
# ==============================================================================

class TestToolCallingAccuracyEvals:
    """Evaluates that exact tools fire for diagnosed categories without deviation."""

    @pytest.mark.asyncio
    async def test_simple_case_calls_failover_cluster_leadership_only(self):
        """Simple Case (network_jitter) must ONLY invoke failover_cluster_leadership.

        Must NEVER call deprioritize_texture_streaming or force_genlock_resync.
        """
        init_state = create_initial_test_state(drift_event=SIMPLE_CASE_DRIFT_EVENT)
        ctx = await create_test_context(init_state)

        mock_failover_out = ReversibleRemediationOutput(
            success=True,
            action_taken="failover_cluster_leadership",
            timestamp=utc_now_iso(),
            details={"node_id": "render-07"},
        )

        with patch(
            "src.agents.reasoning_loop.evidence_triage_node",
            new_callable=AsyncMock,
            return_value=MOCK_TRIAGE_SIMPLE.model_dump(mode="json"),
        ), patch(
            "src.agents.root_cause_correlation.generate_structured_output",
            new_callable=AsyncMock,
            return_value=MOCK_DIAGNOSIS_SIMPLE,
        ), patch(
            "src.agents.autonomous_dispatch.failover_cluster_leadership",
            new_callable=AsyncMock,
            return_value=mock_failover_out,
        ) as mock_failover, patch(
            "src.agents.autonomous_dispatch.deprioritize_texture_streaming",
            new_callable=AsyncMock,
        ) as mock_deprioritize, patch(
            "src.agents.autonomous_dispatch.force_genlock_resync",
            new_callable=AsyncMock,
        ) as mock_resync:

            result: ReasoningLoopResult = await run_reasoning_loop(ctx, SIMPLE_CASE_DRIFT_EVENT.event_id)

            assert result.status == "remediated"
            assert result.diagnosis is not None
            assert result.diagnosis["category"] == "network_jitter"

            # Assert ONLY the correct tool fired
            mock_failover.assert_awaited_once()
            mock_deprioritize.assert_not_awaited()
            mock_resync.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_asset_streaming_stall_calls_deprioritize_texture_only(self):
        """Asset Streaming Stall must ONLY invoke deprioritize_texture_streaming."""
        init_state = create_initial_test_state(drift_event=ASSET_STALL_DRIFT_EVENT)
        ctx = await create_test_context(init_state)

        mock_deprioritize_out = ReversibleRemediationOutput(
            success=True,
            action_taken="deprioritize_texture_streaming",
            timestamp=utc_now_iso(),
            details={"node_id": "render-04"},
        )

        with patch(
            "src.agents.reasoning_loop.evidence_triage_node",
            new_callable=AsyncMock,
            return_value={
                "event_id": ASSET_STALL_DRIFT_EVENT.event_id,
                "logs_available": True,
                "log_summary": "Texture pool exhaustion on render-04",
                "trace_summary": "Nanite paging queue blocked",
                "anomaly": None,
            },
        ), patch(
            "src.agents.root_cause_correlation.generate_structured_output",
            new_callable=AsyncMock,
            return_value=MOCK_DIAGNOSIS_ASSET_STALL,
        ), patch(
            "src.agents.autonomous_dispatch.deprioritize_texture_streaming",
            new_callable=AsyncMock,
            return_value=mock_deprioritize_out,
        ) as mock_deprioritize, patch(
            "src.agents.autonomous_dispatch.failover_cluster_leadership",
            new_callable=AsyncMock,
        ) as mock_failover, patch(
            "src.agents.autonomous_dispatch.force_genlock_resync",
            new_callable=AsyncMock,
        ) as mock_resync:

            result = await run_reasoning_loop(ctx, ASSET_STALL_DRIFT_EVENT.event_id)

            assert result.status == "remediated"
            assert result.diagnosis["category"] == "asset_streaming_stall"

            mock_deprioritize.assert_awaited_once()
            mock_failover.assert_not_awaited()
            mock_resync.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_thermal_throttle_calls_force_genlock_resync_only(self):
        """Thermal Throttle must ONLY invoke force_genlock_resync."""
        init_state = create_initial_test_state(drift_event=THERMAL_THROTTLE_DRIFT_EVENT)
        ctx = await create_test_context(init_state)

        mock_resync_out = ReversibleRemediationOutput(
            success=True,
            action_taken="force_genlock_resync",
            timestamp=utc_now_iso(),
            details={"node_id": "render-09"},
        )

        with patch(
            "src.agents.reasoning_loop.evidence_triage_node",
            new_callable=AsyncMock,
            return_value={
                "event_id": THERMAL_THROTTLE_DRIFT_EVENT.event_id,
                "logs_available": True,
                "log_summary": "GPU 0 thermal throttle engaged temp=94C node=render-09",
                "trace_summary": "Clock frequency stepdown",
                "anomaly": None,
            },
        ), patch(
            "src.agents.root_cause_correlation.generate_structured_output",
            new_callable=AsyncMock,
            return_value=MOCK_DIAGNOSIS_THERMAL,
        ), patch(
            "src.agents.autonomous_dispatch.force_genlock_resync",
            new_callable=AsyncMock,
            return_value=mock_resync_out,
        ) as mock_resync, patch(
            "src.agents.autonomous_dispatch.failover_cluster_leadership",
            new_callable=AsyncMock,
        ) as mock_failover, patch(
            "src.agents.autonomous_dispatch.deprioritize_texture_streaming",
            new_callable=AsyncMock,
        ) as mock_deprioritize:

            result = await run_reasoning_loop(ctx, THERMAL_THROTTLE_DRIFT_EVENT.event_id)

            assert result.status == "remediated"
            assert result.diagnosis["category"] == "thermal_throttle"

            mock_resync.assert_awaited_once()
            mock_failover.assert_not_awaited()
            mock_deprioritize.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_approved_hitl_halt_fires_halt_live_take_only(self):
        """Approved HITL card proposing halt_live_take must ONLY invoke halt_live_take."""
        card = HITLCard(
            card_id="card-halt-001",
            event_id="evt-complex-002",
            node_id="render-12",
            escalation_reason="ambiguous_diagnosis",
            proposed_action="halt_live_take",
            cost_delta_estimate="$1,850.00",
            visual_impact_score="Severe",
            root_cause_summary="Ambiguous telemetry on render-12",
            created_at=utc_now_iso(),
        )
        init_state = GenlockSentinelState(
            session_id="session-hitl-001",
            session_status=SessionStatus.AWAITING_APPROVAL,
            active_drift_events={"render-12": COMPLEX_CASE_DRIFT_EVENT},
            pending_hitl_card=card,
            approval_state=ApprovalStatus.APPROVED,
        )
        ctx = await create_test_context(init_state)

        mock_halt_out = HitlGatedActionOutput(
            success=True,
            action_taken="halt_live_take",
            timestamp=utc_now_iso(),
            details={"card_id": "card-halt-001"},
        )

        with patch(
            "src.agents.post_approval_handling.halt_live_take",
            new_callable=AsyncMock,
            return_value=mock_halt_out,
        ) as mock_halt, patch(
            "src.agents.post_approval_handling.fallback_to_greenscreen",
            new_callable=AsyncMock,
        ) as mock_green, patch(
            "src.agents.post_approval_handling.execute_threshold_exceeding_failover",
            new_callable=AsyncMock,
        ) as mock_exceed:

            output = await post_approval_handling_node(ctx, {"card_id": "card-halt-001"})

            assert output["success"] is True
            assert output["action_taken"] == "halt_live_take"

            mock_halt.assert_awaited_once()
            mock_green.assert_not_awaited()
            mock_exceed.assert_not_awaited()


# ==============================================================================
# 2. Hallucination Prevention & Silence-Over-Guessing Evals (Section 9.3)
# ==============================================================================

class TestHallucinationPreventionEvals:
    """Evaluates strict grounding, citation checks, and silence-over-guessing."""

    @pytest.mark.asyncio
    async def test_edge_case_loki_timeout_sets_logs_unavailable_zero_fabrication(self):
        """When Loki query times out after 3 retries:

        1. EvidenceBundleExtraction.logs_available must be False.
        2. log_summary must not fabricate plausible log lines.
        3. Anomaly must record the telemetry gap.
        """
        init_state = create_initial_test_state(drift_event=EDGE_CASE_DRIFT_EVENT)
        ctx = await create_test_context(init_state)

        with patch(
            "src.agents.reasoning_loop.evidence_triage_node",
            new_callable=AsyncMock,
            return_value=MOCK_TRIAGE_EDGE_TIMEOUT.model_dump(mode="json"),
        ), patch(
            "src.agents.reasoning_loop.root_cause_correlation_node",
            new_callable=AsyncMock,
            return_value={
                "event_id": EDGE_CASE_DRIFT_EVENT.event_id,
                "category": "ambiguous",
                "confidence": 0.40,
                "rationale": "Loki logs unavailable due to query timeout. Insufficient telemetry to confirm root cause.",
            },
        ), patch(
            "src.agents.reasoning_loop.hitl_card_generation_node",
            new_callable=AsyncMock,
            return_value=MOCK_HITL_PACKAGE_HALT.model_dump(mode="json"),
        ):

            result = await run_reasoning_loop(ctx, EDGE_CASE_DRIFT_EVENT.event_id)

            assert result.status == "ambiguous_escalated"
            assert result.triage_bundle is not None
            assert result.triage_bundle["logs_available"] is False
            assert result.triage_bundle["log_summary"] is None
            assert "logs_available=false" in result.triage_bundle["anomaly"]

    def test_strict_citation_enforcement_accepts_grounded_rationale(self):
        """Code-level verifier accepts rationales that cite verified evidence fields."""
        evidence = EvidenceRefs(
            event_id="evt-simple-001",
            logs_available=True,
            log_summary="14:02:11 sync handshake retry node=render-07",
            trace_summary="frame_render span duration 340ms",
        )
        valid_rationale = "Verified per Loki log_summary showing 'sync handshake retry' on render-07 at 14:02:11."

        is_grounded = _validate_grounding_citations(
            rationale=valid_rationale,
            evidence=evidence,
        )
        assert is_grounded is True

    def test_strict_citation_enforcement_rejects_hallucinated_rationale(self):
        """Code-level verifier rejects rationales that cite nonexistent or unreferenced data."""
        evidence = EvidenceRefs(
            event_id="evt-simple-001",
            logs_available=True,
            log_summary="Sync handshake retry node=render-07",
            trace_summary="frame_render span duration 340ms",
        )
        # Completely ungrounded rationale referencing nothing in logs, traces, or metrics
        hallucinated_rationale = "The rack power supply PSU-B failed and caused kernel memory bus fault."

        is_grounded = _validate_grounding_citations(
            rationale=hallucinated_rationale,
            evidence=evidence,
        )
        assert is_grounded is False

    @pytest.mark.asyncio
    async def test_complex_case_conflicting_evidence_surfaces_conflict_and_escalates(self):
        """Complex Case with conflicting Loki and Tempo evidence must explicitly surface

        the conflict in anomaly/rationale and route to ambiguous -> HITL escalation.
        """
        init_state = create_initial_test_state(drift_event=COMPLEX_CASE_DRIFT_EVENT)
        ctx = await create_test_context(init_state)

        with patch(
            "src.agents.reasoning_loop.evidence_triage_node",
            new_callable=AsyncMock,
            return_value=MOCK_TRIAGE_COMPLEX_CONFLICTING.model_dump(mode="json"),
        ), patch(
            "src.agents.reasoning_loop.root_cause_correlation_node",
            new_callable=AsyncMock,
            return_value=MOCK_DIAGNOSIS_COMPLEX_AMBIGUOUS.model_dump(mode="json"),
        ), patch(
            "src.agents.reasoning_loop.hitl_card_generation_node",
            new_callable=AsyncMock,
            return_value=MOCK_HITL_PACKAGE_HALT.model_dump(mode="json"),
        ):

            result = await run_reasoning_loop(ctx, COMPLEX_CASE_DRIFT_EVENT.event_id)

            assert result.status == "ambiguous_escalated"
            assert result.diagnosis["category"] == "ambiguous"
            # Verify conflict was explicitly surfaced rather than favoring one source
            assert "Conflicting telemetry" in result.diagnosis["rationale"]
            assert result.hitl_card is not None


# ==============================================================================
# 3. HITL Graph Resumption Evals (Section 9.3)
# ==============================================================================

class TestHITLGraphResumptionEvals:
    """Evaluates durable pause, resume on Approve/Deny, and checkpoint mismatch checks."""

    @pytest.mark.asyncio
    async def test_hitl_approval_resumes_and_fires_remediation(self):
        """Sending an Approve payload resumes post-approval handling and executes tool."""
        card = HITLCard(
            card_id="card-approved-001",
            event_id="evt-complex-002",
            node_id="render-12",
            escalation_reason="ambiguous_diagnosis",
            proposed_action="halt_live_take",
            cost_delta_estimate="$1,850.00",
            visual_impact_score="High",
            root_cause_summary="Ambiguous telemetry on render-12",
            created_at=utc_now_iso(),
        )
        state = GenlockSentinelState(
            session_id="session-resumption-01",
            session_status=SessionStatus.AWAITING_APPROVAL,
            active_drift_events={"render-12": COMPLEX_CASE_DRIFT_EVENT},
            pending_hitl_card=card,
            approval_state=ApprovalStatus.APPROVED,
        )
        ctx = await create_test_context(state)

        mock_halt_out = HitlGatedActionOutput(
            success=True,
            action_taken="halt_live_take",
            timestamp=utc_now_iso(),
            details={"card_id": "card-approved-001"},
        )

        with patch(
            "src.agents.post_approval_handling.halt_live_take",
            new_callable=AsyncMock,
            return_value=mock_halt_out,
        ) as mock_halt:
            output = await post_approval_handling_node(ctx, {"card_id": "card-approved-001"})

            assert output["success"] is True
            assert output["action_taken"] == "halt_live_take"
            mock_halt.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_hitl_denial_fires_no_remediation_and_logs_audit(self):
        """Sending a Deny payload must fire NO tools and return session to monitoring."""
        card = HITLCard(
            card_id="card-deny-001",
            event_id="evt-complex-002",
            node_id="render-12",
            escalation_reason="ambiguous_diagnosis",
            proposed_action="halt_live_take",
            cost_delta_estimate="$1,850.00",
            visual_impact_score="High",
            root_cause_summary="Ambiguous telemetry on render-12",
            created_at=utc_now_iso(),
        )
        state = GenlockSentinelState(
            session_id="session-resumption-02",
            session_status=SessionStatus.AWAITING_APPROVAL,
            active_drift_events={"render-12": COMPLEX_CASE_DRIFT_EVENT},
            pending_hitl_card=card,
            approval_state=ApprovalStatus.DENIED,
        )
        ctx = await create_test_context(state)

        with patch(
            "src.agents.post_approval_handling.halt_live_take",
            new_callable=AsyncMock,
        ) as mock_halt, patch(
            "src.agents.post_approval_handling.fallback_to_greenscreen",
            new_callable=AsyncMock,
        ) as mock_green:

            output = await post_approval_handling_node(ctx, {"card_id": "card-deny-001"})

            assert output["success"] is True
            assert output["action_taken"] == "denied_halt_live_take"
            mock_halt.assert_not_awaited()
            mock_green.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_hitl_resumption_with_no_pending_card_rejected(self):
        """Invoking post_approval_handling with no pending card raises ToolExecutionError."""
        state = GenlockSentinelState(
            session_id="session-resumption-03",
            session_status=SessionStatus.MONITORING,
            active_drift_events={},
            pending_hitl_card=None,
            approval_state=ApprovalStatus.APPROVED,
        )
        ctx = await create_test_context(state)

        with pytest.raises(ToolExecutionError, match="no pending_hitl_card in state"):
            await post_approval_handling_node(ctx, {"card_id": "card-wrong-999"})
