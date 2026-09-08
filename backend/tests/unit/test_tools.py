"""Unit Tests for Genlock Sentinel Tool Registry.

Verifies all 9 tools across the Node-Tool Access Matrix per
AGENT_MASTER_PLAN.md Section 5 and Section 9.1/9.2:
  - Strict Pydantic V2 schemas (extra="forbid")
  - Strict MCP JSON schemas
  - Evidence Triage (Tools 1–3) mock execution & silence-over-guessing policy
  - Autonomous Remediation (Tools 4–6) category and confidence preconditions
  - Post-Approval Handling (Tools 7–9) approval_state & action matching preconditions
  - LogQL input sanitization
"""

import pytest
from pydantic import ValidationError

from src.state.schema import (
    ApprovalStatus,
    DiagnosisRecord,
    DriftEvent,
    GenlockSentinelState,
    HITLCard,
    RuntimeConfig,
)
from src.tools import (
    MCP_TOOL_SCHEMAS,
    FindSlowRequestsInput,
    FindSlowRequestsOutput,
    GetTraceByIdInput,
    GetTraceByIdOutput,
    HitlGatedActionInput,
    HitlGatedActionOutput,
    QueryLokiLogsInput,
    QueryLokiLogsOutput,
    ReversibleRemediationInput,
    ReversibleRemediationOutput,
    deprioritize_texture_streaming,
    execute_threshold_exceeding_failover,
    failover_cluster_leadership,
    fallback_to_greenscreen,
    find_slow_requests,
    force_genlock_resync,
    get_trace_by_id,
    halt_live_take,
    query_loki_logs,
    sanitize_logql,
)
from src.utils.errors import StateValidationError


# ------------------------------------------------------------------------------
# Test 1: MCP Tool Schemas Registry
# ------------------------------------------------------------------------------

def test_all_nine_tools_registered_in_mcp_schemas() -> None:
    """Confirms all 9 spec-defined tools have valid strict MCP JSON schemas."""
    expected_tools = [
        "query_loki_logs",
        "find_slow_requests",
        "get_trace_by_id",
        "failover_cluster_leadership",
        "deprioritize_texture_streaming",
        "force_genlock_resync",
        "halt_live_take",
        "fallback_to_greenscreen",
        "execute_threshold_exceeding_failover",
    ]

    for tool_name in expected_tools:
        assert tool_name in MCP_TOOL_SCHEMAS, f"Missing MCP schema for {tool_name}"
        schema = MCP_TOOL_SCHEMAS[tool_name]
        assert schema["name"] == tool_name
        assert "description" in schema and len(schema["description"]) > 10
        assert "inputSchema" in schema
        assert schema["inputSchema"]["type"] == "object"
        assert schema["inputSchema"]["additionalProperties"] is False
        assert isinstance(schema["inputSchema"]["required"], list)


# ------------------------------------------------------------------------------
# Test 2: Pydantic Strict Validation & Extra Rejection
# ------------------------------------------------------------------------------

def test_pydantic_schemas_extra_forbid() -> None:
    """Verifies that all tool input schemas reject unauthorized extra fields."""
    with pytest.raises(ValidationError):
        QueryLokiLogsInput(
            logql="{node='render-07'}",
            start="2026-09-08T14:00:00Z",
            end="2026-09-08T14:01:00Z",
            unauthorized_field="malicious",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        ReversibleRemediationInput(
            event_id="evt-1",
            node_id="render-07",
            target_category="network_jitter",
            confidence=0.95,
            rogue_arg="exploit",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        HitlGatedActionInput(
            event_id="evt-1",
            hitl_card_id="hitl-1",
            approval_state="approved",
            unexpected_arg=True,  # type: ignore[call-arg]
        )


# ------------------------------------------------------------------------------
# Test 3: LogQL Input Sanitization
# ------------------------------------------------------------------------------

def test_logql_sanitizer() -> None:
    """Ensures control characters and null bytes are stripped from LogQL strings."""
    dirty_query = "\x00{node='render-07'}\x1f\n"
    clean_query = sanitize_logql(dirty_query)
    assert clean_query == "{node='render-07'}"
    assert "\x00" not in clean_query
    assert "\x1f" not in clean_query


# ------------------------------------------------------------------------------
# Test 4: Tools 1-3 (Evidence Triage) Execution & Preconditions
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tool1_query_loki_logs_success_and_mock_fallback() -> None:
    """Tool 1 returns Section 9.1 mock logs and enforces preconditions."""
    state = GenlockSentinelState(
        session_id="shoot-01",
        active_drift_events={
            "render-07": DriftEvent(
                event_id="f-88213",
                node_id="render-07",
                frame_id="f-88213",
                breach_ts="2026-09-07T14:02:11Z",
                sync_offset_us=185.0,
            )
        },
    )

    payload = QueryLokiLogsInput(
        logql='{node="render-07", channel=~"cluster-manager|LogDisplayClusterEngine"}',
        start="2026-09-07T14:01:41Z",
        end="2026-09-07T14:02:41Z",
    )

    # Valid execution
    output = await query_loki_logs(payload, state=state, node_id="render-07")
    assert output.success is True
    assert len(output.result) > 0
    assert any("sync handshake retry" in line for line in output.result)

    # Precondition failure: querying unbreached node
    with pytest.raises(StateValidationError) as exc:
        await query_loki_logs(payload, state=state, node_id="render-99")
    assert "No active DriftEvent found for node 'render-99'" in str(exc.value)

    # Silence-over-guessing: simulated timeout reports failure cleanly
    timeout_output = await query_loki_logs(payload, simulate_timeout=True)
    assert timeout_output.success is False
    assert timeout_output.result == []
    assert "timed out" in (timeout_output.error or "")


@pytest.mark.asyncio
async def test_tool2_find_slow_requests() -> None:
    """Tool 2 queries Sift investigations for slow spans."""
    state = GenlockSentinelState(
        session_id="shoot-01",
        active_drift_events={
            "render-07": DriftEvent(
                event_id="f-88213",
                node_id="render-07",
                frame_id="f-88213",
                breach_ts="2026-09-07T14:02:11Z",
                sync_offset_us=185.0,
            )
        },
    )

    payload = FindSlowRequestsInput(
        service_name="render-07",
        start="2026-09-07T14:01:41Z",
        end="2026-09-07T14:02:41Z",
        min_duration_ms=100,
    )

    output = await find_slow_requests(payload, state=state)
    assert output.success is True
    assert "findings" in output.result
    assert output.result["findings"][0]["span"] == "frame_render"


@pytest.mark.asyncio
async def test_tool3_get_trace_by_id() -> None:
    """Tool 3 retrieves distributed trace by frame_id with precondition check."""
    state = GenlockSentinelState(
        session_id="shoot-01",
        active_drift_events={
            "render-07": DriftEvent(
                event_id="evt-100",
                node_id="render-07",
                frame_id="f-88213",
                breach_ts="2026-09-07T14:02:11Z",
                sync_offset_us=185.0,
            )
        },
    )

    payload = GetTraceByIdInput(trace_id="f-88213")
    output = await get_trace_by_id(payload, state=state)
    assert output.success is True
    assert "spans" in output.result

    # Mismatched trace_id raises StateValidationError
    bad_payload = GetTraceByIdInput(trace_id="f-unknown")
    with pytest.raises(StateValidationError) as exc:
        await get_trace_by_id(bad_payload, state=state)
    assert "trace_id 'f-unknown' does not match" in str(exc.value)


# ------------------------------------------------------------------------------
# Test 5: Tools 4-6 (Autonomous Remediation) Precondition Invariants
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tools_4_5_6_category_and_confidence_invariants() -> None:
    """Tools 4–6 programmatically verify diagnosed category and confidence floor."""
    state = GenlockSentinelState(
        session_id="shoot-01",
        config=RuntimeConfig(confidence_floor=0.75),
        diagnosis_history=[
            DiagnosisRecord(
                event_id="evt-net",
                category="network_jitter",
                confidence=0.92,
                rationale="Handshake timeout verified",
            ),
            DiagnosisRecord(
                event_id="evt-thermal",
                category="thermal_throttle",
                confidence=0.88,
                rationale="GPU reached 94C",
            ),
            DiagnosisRecord(
                event_id="evt-stall",
                category="asset_streaming_stall",
                confidence=0.85,
                rationale="Nanite streaming stall",
            ),
            DiagnosisRecord(
                event_id="evt-low-conf",
                category="network_jitter",
                confidence=0.60,
                rationale="Inconclusive network spike",
            ),
        ],
    )

    # Tool 4: failover_cluster_leadership (success on network_jitter >= 0.75)
    t4_payload = ReversibleRemediationInput(
        event_id="evt-net",
        node_id="render-07",
        target_category="network_jitter",
        confidence=0.92,
    )
    t4_out = await failover_cluster_leadership(t4_payload, state=state)
    assert t4_out.success is True
    assert t4_out.action_taken == "failover_cluster_leadership"

    # Tool 4: fails on category mismatch
    with pytest.raises(StateValidationError) as exc:
        await failover_cluster_leadership(
            ReversibleRemediationInput(
                event_id="evt-thermal",
                node_id="render-07",
                target_category="network_jitter",
                confidence=0.88,
            ),
            state=state,
        )
    assert "Latest diagnosis category 'thermal_throttle' does not match" in str(exc.value)

    # Tool 4: fails on confidence below floor
    with pytest.raises(StateValidationError) as exc:
        await failover_cluster_leadership(
            ReversibleRemediationInput(
                event_id="evt-low-conf",
                node_id="render-07",
                target_category="network_jitter",
                confidence=0.60,
            ),
            state=state,
        )
    assert "below confidence floor" in str(exc.value)

    # Tool 5: deprioritize_texture_streaming (success on asset_streaming_stall)
    t5_out = await deprioritize_texture_streaming(
        ReversibleRemediationInput(
            event_id="evt-stall",
            node_id="render-07",
            target_category="asset_streaming_stall",
            confidence=0.85,
        ),
        state=state,
    )
    assert t5_out.success is True
    assert t5_out.action_taken == "deprioritize_texture_streaming"

    # Tool 6: force_genlock_resync (success on thermal_throttle)
    t6_out = await force_genlock_resync(
        ReversibleRemediationInput(
            event_id="evt-thermal",
            node_id="render-07",
            target_category="thermal_throttle",
            confidence=0.88,
        ),
        state=state,
    )
    assert t6_out.success is True
    assert t6_out.action_taken == "force_genlock_resync"


# ------------------------------------------------------------------------------
# Test 6: Tools 7-9 (Post-Approval Handling) Approval Preconditions
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tools_7_8_9_hitl_approval_invariants() -> None:
    """Tools 7–9 programmatically enforce approval_state == 'approved' and card action matching."""
    pending_card = HITLCard(
        card_id="hitl-card-001",
        event_id="evt-halt-01",
        escalation_reason="take_halt_required",
        proposed_action="halt_live_take",
        cost_delta_estimate="$1,500/min",
        visual_impact_score="Critical",
        root_cause_summary="Sync drift across multiple camera takes",
    )

    # 1. State with APPROVED status
    approved_state = GenlockSentinelState(
        session_id="shoot-01",
        approval_state=ApprovalStatus.APPROVED,
        pending_hitl_card=pending_card,
    )

    payload = HitlGatedActionInput(
        event_id="evt-halt-01",
        hitl_card_id="hitl-card-001",
        approval_state="approved",
    )

    # Tool 7: halt_live_take succeeds
    out7 = await halt_live_take(payload, state=approved_state)
    assert out7.success is True
    assert out7.action_taken == "halt_live_take"

    # 2. Reject if approval_state is DENIED or PENDING
    denied_state = GenlockSentinelState(
        session_id="shoot-01",
        approval_state=ApprovalStatus.DENIED,
        pending_hitl_card=pending_card,
    )
    with pytest.raises(StateValidationError) as exc:
        await halt_live_take(payload, state=denied_state)
    assert "requires state.approval_state == 'approved'" in str(exc.value)

    # 3. Reject if proposed_action does not match tool
    with pytest.raises(StateValidationError) as exc:
        await fallback_to_greenscreen(
            HitlGatedActionInput(
                event_id="evt-halt-01",
                hitl_card_id="hitl-card-001",
                approval_state="approved",
            ),
            state=approved_state,
        )
    assert "does not match required tool 'fallback_to_greenscreen'" in str(exc.value)

    # 4. Reject if hitl_card_id does not match
    with pytest.raises(StateValidationError) as exc:
        await halt_live_take(
            HitlGatedActionInput(
                event_id="evt-halt-01",
                hitl_card_id="hitl-wrong-card",
                approval_state="approved",
            ),
            state=approved_state,
        )
    assert "does not match pending card id" in str(exc.value)

    # Tool 8 & 9 success on exact matching cards
    greenscreen_card = HITLCard(
        card_id="hitl-card-002",
        event_id="evt-green-01",
        escalation_reason="capture_fallback_required",
        proposed_action="fallback_to_greenscreen",
        cost_delta_estimate="$500",
        visual_impact_score="High",
        root_cause_summary="LED volume wall artifacting",
    )
    green_state = GenlockSentinelState(
        session_id="shoot-01",
        approval_state=ApprovalStatus.APPROVED,
        pending_hitl_card=greenscreen_card,
    )
    out8 = await fallback_to_greenscreen(
        HitlGatedActionInput(
            event_id="evt-green-01",
            hitl_card_id="hitl-card-002",
            approval_state="approved",
        ),
        state=green_state,
    )
    assert out8.success is True
    assert out8.action_taken == "fallback_to_greenscreen"

    failover_card = HITLCard(
        card_id="hitl-card-003",
        event_id="evt-cloud-01",
        escalation_reason="threshold_exceeded",
        proposed_action="execute_threshold_exceeding_failover",
        cost_delta_estimate="$3,500",
        visual_impact_score="Low",
        root_cause_summary="Primary cluster chassis failover",
    )
    failover_state = GenlockSentinelState(
        session_id="shoot-01",
        approval_state=ApprovalStatus.APPROVED,
        pending_hitl_card=failover_card,
    )
    out9 = await execute_threshold_exceeding_failover(
        HitlGatedActionInput(
            event_id="evt-cloud-01",
            hitl_card_id="hitl-card-003",
            approval_state="approved",
        ),
        state=failover_state,
    )
    assert out9.success is True
    assert out9.action_taken == "execute_threshold_exceeding_failover"
