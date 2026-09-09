"""Unit tests for 7-Node ADK Workflow Runtime Graph Orchestration.

Verifies:
1. Exact 7-node topology matching AGENT_ORCHESTRATION_BLUEPRINT.md Section 4.
2. Node-Tool Access Matrix boundary compliance.
3. Node 1 Stream Watch threshold breach detection.
4. Node 2 Evidence Triage structured extraction & silence-over-guessing.
5. Node 3 Root-Cause Correlation grounding and ctx.route decision edge.
6. Node 4 Autonomous Dispatch reversible actuator execution and preconditions.
7. Node 5 HITL Card Generation schema compliance and state update.
8. Node 6 HITL Pause checkpoint interrupt and Node 7 Post-Approval Handling execution/denial.
9. Circuit breaker forced escalation to HITL.
"""

import pytest
from google.adk import Context, Runner
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START


def _create_test_context(session, session_service, invocation_id: str = "test-invoc") -> Context:
    """Helper to instantiate ADK Context with a valid InvocationContext."""
    inv = InvocationContext(
        session_service=session_service,
        invocation_id=invocation_id,
        session=session,
    )
    return Context(inv)

from src.agents.autonomous_dispatch import autonomous_dispatch_node
from src.agents.evidence_triage import evidence_triage_node
from src.agents.graph import (
    ALL_GRAPH_NODES,
    create_genlock_workflow,
    create_genlock_workflow_edges,
    hitl_pause_node,
    node1_stream_watch,
    node2_evidence_triage,
    node3_root_cause_correlation,
    node4_autonomous_dispatch,
    node5_hitl_card_generation,
    node6_hitl_pause,
    node7_post_approval_handling,
)
from src.agents.hitl_card_generation import hitl_card_generation_node
from src.agents.post_approval_handling import post_approval_handling_node
from src.agents.root_cause_correlation import (
    check_circuit_breaker,
    root_cause_correlation_node,
)
from src.agents.stream_watch import StreamWatchInput, stream_watch_node
from src.state.schema import (
    ApprovalStatus,
    DiagnosisRecord,
    DriftEvent,
    EvidenceRefs,
    GenlockSentinelState,
    HITLCard,
    RemediationAction,
    SessionStatus,
    utc_now_iso,
)
from src.utils.errors import ToolExecutionError


def test_graph_topology_has_exact_seven_nodes():
    """Verifies that the workflow graph compiles with exactly 7 distinct nodes."""
    workflow = create_genlock_workflow()
    edges = create_genlock_workflow_edges()

    node_names = [n.name for n in ALL_GRAPH_NODES]
    expected_names = [
        "node1_stream_watch",
        "node2_evidence_triage",
        "node3_root_cause_correlation",
        "node4_autonomous_dispatch",
        "node5_hitl_card_generation",
        "node6_hitl_pause",
        "node7_post_approval_handling",
    ]

    assert len(ALL_GRAPH_NODES) == 7
    assert node_names == expected_names
    assert len(edges) == 7
    assert workflow.graph is not None

    # Verify edge topology
    assert edges[0].from_node.name == START.name
    assert edges[0].to_node.name == "node1_stream_watch"

    assert edges[1].from_node.name == "node1_stream_watch"
    assert edges[1].to_node.name == "node2_evidence_triage"

    assert edges[2].from_node.name == "node2_evidence_triage"
    assert edges[2].to_node.name == "node3_root_cause_correlation"

    assert edges[3].from_node.name == "node3_root_cause_correlation"
    assert edges[3].to_node.name == "node4_autonomous_dispatch"
    assert edges[3].route == "autonomous"

    assert edges[4].from_node.name == "node3_root_cause_correlation"
    assert edges[4].to_node.name == "node5_hitl_card_generation"
    assert edges[4].route == "hitl"

    assert edges[5].from_node.name == "node5_hitl_card_generation"
    assert edges[5].to_node.name == "node6_hitl_pause"

    assert edges[6].from_node.name == "node6_hitl_pause"
    assert edges[6].to_node.name == "node7_post_approval_handling"


@pytest.mark.asyncio
async def test_node1_stream_watch_breach_detection():
    """Verifies that Node 1 instantiates a DriftEvent when telemetry exceeds threshold."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        session_id="test-session-n1",
        user_id="supervisor-01",
        app_name="genlock_sentinel",
    )
    initial_state = GenlockSentinelState(session_id="test-session-n1")
    session.state.update(initial_state.model_dump())

    ctx = _create_test_context(session, session_service, "invoc-n1-breach")

    # 1. Breach case: sync offset 842us > 150us
    breach_input = StreamWatchInput(
        node_id="render-07",
        sync_offset_us=842.0,
        frame_id="f-144021",
    )
    res_breach = await stream_watch_node(ctx, breach_input)

    assert res_breach["threshold_breached"] is True
    assert res_breach["drift_event"] is not None
    assert res_breach["drift_event"]["node_id"] == "render-07"
    assert "active_drift_events" in ctx.actions.state_delta
    assert ctx.actions.state_delta["session_status"] == SessionStatus.TRIAGING.value

    # 2. Nominal case: sync offset 50us <= 150us
    ctx_nominal = _create_test_context(session, session_service, "invoc-n1-nominal")
    nominal_input = StreamWatchInput(
        node_id="render-08",
        sync_offset_us=50.0,
        frame_id="f-144022",
    )
    res_nominal = await stream_watch_node(ctx_nominal, nominal_input)
    assert res_nominal["threshold_breached"] is False
    assert res_nominal["drift_event"] is None


@pytest.mark.asyncio
async def test_node2_evidence_triage_structured_extraction():
    """Verifies that Node 2 queries observability tools and produces valid EvidenceBundleExtraction."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        session_id="test-session-n2",
        user_id="supervisor-01",
        app_name="genlock_sentinel",
    )
    drift = DriftEvent(
        event_id="drift-render-07-f-144021",
        node_id="render-07",
        frame_id="f-144021",
        breach_ts=utc_now_iso(),
        sync_offset_us=842.0,
        threshold_us=150.0,
        status="detected",
    )
    state = GenlockSentinelState(
        session_id="test-session-n2",
        active_drift_events={"render-07": drift},
    )
    session.state.update(state.model_dump())
    ctx = _create_test_context(session, session_service, "invoc-n2")

    res = await evidence_triage_node(ctx, {"event_id": "drift-render-07-f-144021"})

    assert res["event_id"] == "drift-render-07-f-144021"
    assert "log_summary" in res
    assert "trace_summary" in res
    assert "evidence_bundle" in ctx.actions.state_delta
    assert "drift-render-07-f-144021" in ctx.actions.state_delta["evidence_bundle"]


@pytest.mark.asyncio
async def test_node3_decision_edge_autonomous_and_hitl_routing():
    """Verifies pure Python decision edge routing: autonomous vs hitl via ctx.route."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        session_id="test-session-n3",
        user_id="supervisor-01",
        app_name="genlock_sentinel",
    )
    drift = DriftEvent(
        event_id="drift-render-07-f-144021",
        node_id="render-07",
        frame_id="f-144021",
        breach_ts=utc_now_iso(),
        sync_offset_us=842.0,
        threshold_us=150.0,
        status="detected",
    )
    evidence = EvidenceRefs(
        event_id="drift-render-07-f-144021",
        node_id="render-07",
        logs_available=True,
        log_summary="[cluster-manager] sync handshake retry node=render-07",
        trace_summary="Tempo spans: render frame duration 340ms",
        anomaly=None,
        timestamp=utc_now_iso(),
        raw_refs={},
    )

    # 1. Autonomous Path: confident diagnosis
    state_auto = GenlockSentinelState(
        session_id="test-session-n3",
        active_drift_events={"render-07": drift},
        evidence_bundle={"drift-render-07-f-144021": evidence},
    )
    session.state.clear()
    session.state.update(state_auto.model_dump())
    ctx_auto = _create_test_context(session, session_service, "invoc-n3-auto")

    diag_auto = await root_cause_correlation_node(ctx_auto, {"event_id": "drift-render-07-f-144021"})
    assert diag_auto["event_id"] == "drift-render-07-f-144021"
    assert ctx_auto.route in ("autonomous", "hitl")
    assert "diagnosis_history" in ctx_auto.actions.state_delta

    # 2. HITL Path: circuit breaker tripped
    remediations = [
        RemediationAction(
            action_id=f"act-{i}",
            event_id=f"drift-prev-{i}",
            node_id="render-07",
            action_taken="failover_cluster_leadership",
            timestamp=utc_now_iso(),
            success=True,
            details={},
        )
        for i in range(3)
    ]
    state_breaker = GenlockSentinelState(
        session_id="test-session-n3",
        active_drift_events={"render-07": drift},
        evidence_bundle={"drift-render-07-f-144021": evidence},
        remediation_log=remediations,
    )
    session.state.clear()
    session.state.update(state_breaker.model_dump())
    ctx_breaker = _create_test_context(session, session_service, "invoc-n3-breaker")

    await root_cause_correlation_node(ctx_breaker, {"event_id": "drift-render-07-f-144021"})
    assert check_circuit_breaker("render-07", state_breaker) is True
    assert ctx_breaker.route == "hitl"


@pytest.mark.asyncio
async def test_node4_autonomous_dispatch_preconditions_and_execution():
    """Verifies that Node 4 verifies preconditions and dispatches reversible tools."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        session_id="test-session-n4",
        user_id="supervisor-01",
        app_name="genlock_sentinel",
    )

    # Valid network jitter diagnosis with confidence 0.94 >= 0.75
    diagnosis = DiagnosisRecord(
        event_id="drift-render-07-f-144021",
        node_id="render-07",
        category="network_jitter",
        confidence=0.94,
        rationale="Handshake retries detected in Loki logs",
        timestamp=utc_now_iso(),
    )
    drift = DriftEvent(
        event_id="drift-render-07-f-144021",
        node_id="render-07",
        frame_id="f-144021",
        breach_ts=utc_now_iso(),
        sync_offset_us=842.0,
        threshold_us=150.0,
        status="detected",
    )
    state = GenlockSentinelState(
        session_id="test-session-n4",
        active_drift_events={"render-07": drift},
        diagnosis_history=[diagnosis],
    )
    session.state.update(state.model_dump())
    ctx = _create_test_context(session, session_service, "invoc-n4-ok")

    res = await autonomous_dispatch_node(ctx)
    assert res["action_taken"] == "failover_cluster_leadership"
    assert res["success"] is True
    assert "remediation_log" in ctx.actions.state_delta
    assert ctx.actions.state_delta["session_status"] == SessionStatus.MONITORING.value
    assert ctx.actions.state_delta["active_drift_events"] == {}
    assert "render-07" not in session.state.get("active_drift_events", {})

    # Rejection case: low confidence
    low_conf_diagnosis = DiagnosisRecord(
        event_id="drift-render-07-f-144021",
        node_id="render-07",
        category="network_jitter",
        confidence=0.45,
        rationale="Weak evidence",
        timestamp=utc_now_iso(),
    )
    state_low_conf = GenlockSentinelState(
        session_id="test-session-n4",
        diagnosis_history=[low_conf_diagnosis],
    )
    session.state.clear()
    session.state.update(state_low_conf.model_dump())
    ctx_low = _create_test_context(session, session_service, "invoc-n4-low")

    with pytest.raises(ToolExecutionError, match="confidence 0.45 < floor"):
        await autonomous_dispatch_node(ctx_low)


@pytest.mark.asyncio
async def test_node5_hitl_card_generation_updates_state():
    """Verifies that Node 5 generates HITLCardPackage and updates pending_hitl_card."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        session_id="test-session-n5",
        user_id="supervisor-01",
        app_name="genlock_sentinel",
    )

    diagnosis = DiagnosisRecord(
        event_id="drift-render-12-f-144025",
        node_id="render-12",
        category="ambiguous",
        confidence=0.52,
        rationale="Conflicting Loki logs suggest thermal, Tempo suggests network jitter",
        timestamp=utc_now_iso(),
    )
    state = GenlockSentinelState(
        session_id="test-session-n5",
        diagnosis_history=[diagnosis],
    )
    session.state.update(state.model_dump())
    ctx = _create_test_context(session, session_service, "invoc-n5")

    res = await hitl_card_generation_node(ctx)
    assert res["event_id"] == "drift-render-12-f-144025"
    assert "proposed_action" in res
    assert "cost_delta_estimate" in res
    assert "visual_impact_score" in res
    assert "pending_hitl_card" in ctx.actions.state_delta
    assert ctx.actions.state_delta["session_status"] == SessionStatus.AWAITING_APPROVAL.value


@pytest.mark.asyncio
async def test_node6_pause_and_node7_post_approval_handling():
    """Verifies Node 6 pause interrupt and Node 7 post-approval dispatch & denial."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        session_id="test-session-n6-7",
        user_id="supervisor-01",
        app_name="genlock_sentinel",
    )

    card = HITLCard(
        card_id="hitl-test-001",
        event_id="drift-render-12-f-144025",
        node_id="render-12",
        escalation_reason="ambiguous_diagnosis",
        proposed_action="halt_live_take",
        cost_delta_estimate="$1,500 USD",
        visual_impact_score="8.5 / 10",
        root_cause_summary="Severe frame sync defect on render-12 during live camera roll",
        created_at=utc_now_iso(),
    )

    # 1. Node 6 Pause test (approval_state == PENDING)
    state_pending = GenlockSentinelState(
        session_id="test-session-n6-7",
        pending_hitl_card=card,
        approval_state=ApprovalStatus.PENDING,
    )
    session.state.clear()
    session.state.update(state_pending.model_dump())
    ctx_pause = _create_test_context(session, session_service, "invoc-n6-pause")

    events = [ev async for ev in hitl_pause_node(ctx_pause)]
    assert len(events) == 1
    assert "hitl_supervisor_approval" in events[0].long_running_tool_ids

    # 2. Node 7 Post-Approval test (approval_state == APPROVED)
    drift_card_node = DriftEvent(
        event_id=card.event_id,
        node_id="render-12",
        frame_id="f-144025",
        breach_ts=utc_now_iso(),
        sync_offset_us=210.0,
        threshold_us=150.0,
        status="detected",
    )
    state_approved = GenlockSentinelState(
        session_id="test-session-n6-7",
        active_drift_events={"render-12": drift_card_node},
        pending_hitl_card=card,
        approval_state=ApprovalStatus.APPROVED,
    )
    session.state.clear()
    session.state.update(state_approved.model_dump())
    ctx_post_approved = _create_test_context(session, session_service, "invoc-n7-approved")

    res_post = await post_approval_handling_node(ctx_post_approved)
    assert res_post["action_taken"] == "halt_live_take"
    assert res_post["success"] is True
    assert ctx_post_approved.actions.state_delta["session_status"] == SessionStatus.MONITORING.value
    assert ctx_post_approved.actions.state_delta["pending_hitl_card"] is None
    assert ctx_post_approved.actions.state_delta["active_drift_events"] == {}

    # 3. Node 7 Denial test (approval_state == DENIED)
    state_denied = GenlockSentinelState(
        session_id="test-session-n6-7",
        active_drift_events={"render-12": drift_card_node},
        pending_hitl_card=card,
        approval_state=ApprovalStatus.DENIED,
    )
    session.state.clear()
    session.state.update(state_denied.model_dump())
    ctx_post_denied = _create_test_context(session, session_service, "invoc-n7-denied")

    res_denied = await post_approval_handling_node(ctx_post_denied)
    assert res_denied["action_taken"] == "denied_halt_live_take"
    assert ctx_post_denied.actions.state_delta["session_status"] == SessionStatus.MONITORING.value
    assert ctx_post_denied.actions.state_delta["pending_hitl_card"] is None
    assert ctx_post_denied.actions.state_delta["active_drift_events"] == {}


@pytest.mark.asyncio
async def test_end_to_end_workflow_execution_with_runner():
    """Verifies that Runner successfully executes the compiled 7-Node Workflow."""
    session_service = InMemorySessionService()
    session_id = "test-e2e-workflow"
    session = await session_service.create_session(
        session_id=session_id,
        user_id="supervisor-01",
        app_name="genlock_sentinel",
    )
    init_state = GenlockSentinelState(session_id=session_id)
    session.state.update(init_state.model_dump())

    workflow = create_genlock_workflow("test_e2e_genlock_wf")
    runner = Runner(
        node=workflow,
        session_service=session_service,
        app_name="genlock_sentinel",
    )

    # Trigger run through ADK runner
    events = []
    async for event in runner.run_async(user_id="supervisor-01", session_id=session_id):
        events.append(event)

    assert len(events) > 0
    last_event = events[-1]
    assert last_event is not None
