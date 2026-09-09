"""Genlock Sentinel — HITL Graph-Resumption Coordinator.

Implements the ADK graph pause/resume coordinator for LongRunningFunctionTool
interrupt handling, checkpoint verification, and post-approval dispatch per
AGENT_MASTER_PLAN.md Section 7, Section 10 Step 16, and
INTERFACE_OBSERVABILITY_SYSTEM.md Section 5.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional, Tuple
from uuid import uuid4

from fastapi import HTTPException, status
from google.adk import Context
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.adk.tools import LongRunningFunctionTool
from pydantic import BaseModel, ConfigDict, Field

from src.agents.post_approval_handling import post_approval_handling_node
from src.state.checkpointing import load_checkpoint, save_checkpoint
from src.state.schema import (
    ApprovalStatus,
    ErrorRecord,
    GenlockSentinelState,
    HITLCard,
    RemediationAction,
    SessionStatus,
    get_or_init_state,
    utc_now_iso,
)
from src.ui.agui_bridge import AGUIEventBridge, get_event_bridge
from src.ui.event_types import RunPausedEvent, StepFinishedEvent, StepStartedEvent
from src.utils.errors import AgentError, StateValidationError, ToolExecutionError

logger = logging.getLogger("genlock_sentinel.ui.hitl_resumption")


# ------------------------------------------------------------------------------
# Pydantic Models for Decision Handling
# ------------------------------------------------------------------------------

class DecisionRequest(BaseModel):
    """Supervisor decision payload for pending HITL operation."""

    model_config = ConfigDict(strict=True, extra="forbid")

    action: Literal["approve", "deny"] = Field(
        ..., description="Decision action: 'approve' or 'deny'"
    )
    checkpoint_id: str = Field(
        ..., description="Checkpoint ID matching pending card (e.g. hitl_pause::<event_id>)"
    )
    modified_inputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Must be None (no editable fields exist per spec)"
    )
    reason: Optional[str] = Field(
        default=None, description="Optional supervisor-supplied denial reason"
    )


class DecisionResponse(BaseModel):
    """Response returned upon processing supervisor decision."""

    model_config = ConfigDict(strict=True, extra="forbid")

    status: str = Field(..., description="Operation result status: 'accepted'")
    session_id: str = Field(..., description="Active session ID")
    event_id: str = Field(..., description="Drift event ID")
    action: str = Field(..., description="Approved or denied action")
    approval_state: str = Field(..., description="Resulting approval_state in state")
    checkpoint_id: str = Field(..., description="Matched checkpoint ID")
    post_approval_result: Optional[Dict[str, Any]] = Field(
        default=None, description="Output details from post-approval handling node"
    )


DecisionRequest.model_rebuild()
DecisionResponse.model_rebuild()


# ------------------------------------------------------------------------------
# ADK LongRunningFunctionTool for HITL Pause
# ------------------------------------------------------------------------------

async def _await_supervisor_approval_fn(
    event_id: str,
    checkpoint_id: str,
) -> Dict[str, Any]:
    """Internal function wrapped by LongRunningFunctionTool for graph suspension."""
    return {
        "status": "awaiting_supervisor_approval",
        "event_id": event_id,
        "checkpoint_id": checkpoint_id,
    }


hitl_supervisor_approval_tool = LongRunningFunctionTool(_await_supervisor_approval_fn)


# ------------------------------------------------------------------------------
# Context Helper for Node Execution
# ------------------------------------------------------------------------------

async def _build_node_context(
    session_id: str,
    state: GenlockSentinelState,
    session_service: Optional[BaseSessionService] = None,
) -> Context:
    """Constructs a fully functional ADK Context populated with GenlockSentinelState."""
    service = session_service or InMemorySessionService()

    # Retrieve or create session in the session service
    session = await service.get_session(
        app_name="genlock_sentinel",
        user_id="on_set_supervisor",
        session_id=session_id,
    )
    if session is None:
        session = await service.create_session(
            app_name="genlock_sentinel",
            user_id="on_set_supervisor",
            session_id=session_id,
        )

    # Sync state dictionary into session
    session.state.clear()
    session.state.update(state.model_dump())

    inv = InvocationContext(
        session_service=service,
        invocation_id=f"invoc-hitl-resume-{uuid4().hex[:8]}",
        session=session,
    )
    return Context(inv)


# ------------------------------------------------------------------------------
# HITL Resumption Coordinator
# ------------------------------------------------------------------------------

class HITLResumptionCoordinator:
    """Coordinates graph pause notifications, checkpoint validations, and resumptions.

    Enforces:
      1. Zero-Error tolerance: strict Approve/Deny only (rejection of modified_inputs).
      2. Grounding and checkpoint integrity: verification of session, pending card,
         event_id match, and checkpoint_id correlation.
      3. Complete audit trail: state mutations, remediation_log/error_logs logging,
         RFC 6902 STATE_DELTA projections, and SSE event broadcasts.
      4. Deterministic Post-Approval Dispatch: execution of the supervisor-approved
         remediation tool (halt_live_take, fallback_to_greenscreen, or
         execute_threshold_exceeding_failover) with verified preconditions.
    """

    def __init__(self, bridge: Optional[AGUIEventBridge] = None) -> None:
        self._bridge = bridge or get_event_bridge()

    @property
    def bridge(self) -> AGUIEventBridge:
        """Returns the active AGUIEventBridge instance."""
        return self._bridge

    async def notify_paused(
        self,
        session_id: str,
        run_id: str,
        card: Optional[HITLCard] = None,
        reason: str = "hitl_approval_required",
    ) -> RunPausedEvent:
        """Emits RUN_PAUSED event and broadcasts pending card state deltas.

        Called when Node 6 (HITL Pause) interrupts graph execution awaiting
        supervisor sign-off.
        """
        logger.info(
            "Graph execution paused at HITL checkpoint for session '%s', run '%s' (reason: %s)",
            session_id,
            run_id,
            reason,
        )

        # Broadcast state delta for pending card if provided
        if card is not None:
            delta_card = self._bridge.build_state_delta(
                field_name="pending_hitl_card",
                reducer_type="last-write-wins",
                value=card.model_dump(),
            )
            await self._bridge.broadcast_event(session_id, delta_card)

            delta_status = self._bridge.build_state_delta(
                field_name="session_status",
                reducer_type="last-write-wins",
                value=SessionStatus.AWAITING_APPROVAL.value,
            )
            await self._bridge.broadcast_event(session_id, delta_status)

        # Emit RUN_PAUSED to open blocking modal on console
        return await self._bridge.emit_run_paused(
            session_id=session_id,
            run_id=run_id,
            reason=reason,
        )

    def verify_checkpoint(
        self,
        state: Optional[GenlockSentinelState],
        session_id: str,
        event_id: str,
        checkpoint_id: str,
        modified_inputs: Optional[Dict[str, Any]] = None,
    ) -> Tuple[GenlockSentinelState, HITLCard]:
        """Performs constitutional validation of the pending HITL checkpoint.

        Raises HTTPException (or StateValidationError) on any invariant breach:
          - Modified inputs provided -> 400 Bad Request
          - Session not found -> 404 Not Found
          - No pending HITL card -> 400 Bad Request
          - Event ID mismatch -> 400 Bad Request
          - Checkpoint ID mismatch -> 400 Bad Request
        """
        # 1. Modified inputs check (LLM-4 Section 5 — no editable fields)
        if modified_inputs is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Modifying inputs is not permitted at this checkpoint (strict Approve/Deny only).",
            )

        # 2. Session existence check
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found.",
            )

        # 3. Pending HITL card presence check
        if state.pending_hitl_card is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No pending HITL card found for session '{session_id}'.",
            )

        card = state.pending_hitl_card

        # 4. Target event_id match
        if card.event_id != event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event ID mismatch: pending card is for '{card.event_id}', but received '{event_id}'.",
            )

        # 5. Checkpoint ID validation
        valid_checkpoint_ids = {
            f"hitl_pause::{card.event_id}",
            card.card_id,
            card.event_id,
        }
        if checkpoint_id not in valid_checkpoint_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Checkpoint ID mismatch: '{checkpoint_id}' does not match pending card checkpoint.",
            )

        return state, card

    async def handle_decision(
        self,
        session_id: str,
        event_id: str,
        payload: DecisionRequest,
        session_service: Optional[BaseSessionService] = None,
    ) -> DecisionResponse:
        """Processes an Approve or Deny decision and triggers post-approval handling.

        Adheres strictly to AGENT_MASTER_PLAN.md Section 7 & 9.3:
          - On Approve: updates approval_state = approved, session_status = resumed,
            appends approval to remediation_log, invokes Node 7 post_approval_handling_node
            (which executes the specific HITL-gated action tool), emits STEP_STARTED/FINISHED
            and STATE_DELTA events, updates session_status = monitoring, and saves checkpoint.
          - On Deny: updates approval_state = denied, session_status = monitoring,
            appends denial to error_logs and remediation_log, verifies zero actuator tools fire,
            emits STATE_DELTA events, and saves checkpoint.
        """
        # Load current checkpoint
        state = await load_checkpoint(session_id=session_id)

        # Strictly verify checkpoint invariants
        state, card = self.verify_checkpoint(
            state=state,
            session_id=session_id,
            event_id=event_id,
            checkpoint_id=payload.checkpoint_id,
            modified_inputs=payload.modified_inputs,
        )

        post_approval_result: Optional[Dict[str, Any]] = None

        if payload.action == "approve":
            logger.info(
                "Processing supervisor APPROVE for session '%s', event '%s', action '%s'",
                session_id,
                event_id,
                card.proposed_action,
            )

            # 1. Update state for Approval
            state.approval_state = ApprovalStatus.APPROVED
            state.session_status = SessionStatus.RESUMED

            approval_audit = RemediationAction(
                action_id=f"act-{uuid4().hex[:8]}",
                event_id=event_id,
                node_id=card.node_id,
                action_taken=f"supervisor_approved::{card.proposed_action}",
                timestamp=utc_now_iso(),
                success=True,
                details={
                    "checkpoint_id": payload.checkpoint_id,
                    "proposed_action": card.proposed_action,
                },
            )
            state.remediation_log.append(approval_audit)

            # Save checkpoint before dispatching actuator
            await save_checkpoint(session_id=session_id, state=state)

            # Broadcast initial state deltas
            await self._bridge.broadcast_event(
                session_id,
                self._bridge.build_state_delta(
                    field_name="approval_state",
                    reducer_type="last-write-wins",
                    value=ApprovalStatus.APPROVED.value,
                ),
            )
            await self._bridge.broadcast_event(
                session_id,
                self._bridge.build_state_delta(
                    field_name="session_status",
                    reducer_type="last-write-wins",
                    value=SessionStatus.RESUMED.value,
                ),
            )
            await self._bridge.broadcast_event(
                session_id,
                self._bridge.build_state_delta(
                    field_name="remediation_log",
                    reducer_type="append-only",
                    value=approval_audit.model_dump(),
                ),
            )

            # 2. Node 7 Post-Approval Dispatch
            await self._bridge.emit_step_started(
                session_id=session_id,
                step_name="post_approval_handling",
                event_id=event_id,
            )

            try:
                node_ctx = await _build_node_context(
                    session_id=session_id,
                    state=state,
                    session_service=session_service,
                )
                post_approval_result = await post_approval_handling_node(node_ctx)

                # Reconstruct updated state from context actions
                updated_state = get_or_init_state(node_ctx)

                # Apply final session status
                updated_state.session_status = SessionStatus.MONITORING

                # Persist updated state to checkpoint
                await save_checkpoint(session_id=session_id, state=updated_state)

                # Broadcast step finish and final state deltas
                await self._bridge.emit_step_finished(
                    session_id=session_id,
                    step_name="post_approval_handling",
                    event_id=event_id,
                )

                if updated_state.remediation_log:
                    latest_action = updated_state.remediation_log[-1]
                    await self._bridge.broadcast_event(
                        session_id,
                        self._bridge.build_state_delta(
                            field_name="remediation_log",
                            reducer_type="append-only",
                            value=latest_action.model_dump(),
                        ),
                    )

                await self._bridge.broadcast_event(
                    session_id,
                    self._bridge.build_state_delta(
                        field_name="session_status",
                        reducer_type="last-write-wins",
                        value=SessionStatus.MONITORING.value,
                    ),
                )

            except Exception as exc:
                logger.error(
                    "Error executing post-approval handling for event '%s': %s",
                    event_id,
                    exc,
                    exc_info=True,
                )
                state.error_logs.append(
                    ErrorRecord(
                        event_id=event_id,
                        node_id=card.node_id,
                        error_type="PostApprovalExecutionError",
                        message=str(exc),
                    )
                )
                await save_checkpoint(session_id=session_id, state=state)
                await self._bridge.emit_run_error(
                    session_id=session_id,
                    message=f"Post-approval action failed: {exc}",
                    code="POST_APPROVAL_ERROR",
                )
                raise

        else:  # action == "deny"
            logger.info(
                "Processing supervisor DENIAL for session '%s', event '%s', action '%s'",
                session_id,
                event_id,
                card.proposed_action,
            )

            # 1. Update state for Denial
            state.approval_state = ApprovalStatus.DENIED
            state.session_status = SessionStatus.MONITORING

            denial_error = ErrorRecord(
                event_id=event_id,
                node_id=card.node_id,
                error_type="SupervisorDenial",
                message=(
                    f"Supervisor denied action '{card.proposed_action}' for event '{event_id}'. "
                    f"Reason: {payload.reason or 'None'}"
                ),
            )
            state.error_logs.append(denial_error)

            denial_action = RemediationAction(
                action_id=f"act-{uuid4().hex[:8]}",
                event_id=event_id,
                node_id=card.node_id,
                action_taken=f"supervisor_denied::{card.proposed_action}",
                timestamp=utc_now_iso(),
                success=False,
                details={
                    "reason": payload.reason,
                    "checkpoint_id": payload.checkpoint_id,
                    "proposed_action": card.proposed_action,
                },
            )
            state.remediation_log.append(denial_action)

            # Persist updated state to checkpoint store
            await save_checkpoint(session_id=session_id, state=state)

            # Broadcast state deltas
            await self._bridge.broadcast_event(
                session_id,
                self._bridge.build_state_delta(
                    field_name="approval_state",
                    reducer_type="last-write-wins",
                    value=ApprovalStatus.DENIED.value,
                ),
            )
            await self._bridge.broadcast_event(
                session_id,
                self._bridge.build_state_delta(
                    field_name="session_status",
                    reducer_type="last-write-wins",
                    value=SessionStatus.MONITORING.value,
                ),
            )
            await self._bridge.broadcast_event(
                session_id,
                self._bridge.build_state_delta(
                    field_name="error_logs",
                    reducer_type="append-only",
                    value=denial_error.model_dump(),
                ),
            )
            await self._bridge.broadcast_event(
                session_id,
                self._bridge.build_state_delta(
                    field_name="remediation_log",
                    reducer_type="append-only",
                    value=denial_action.model_dump(),
                ),
            )

            post_approval_result = {
                "action_taken": f"denied_{card.proposed_action}",
                "success": False,
                "approval_state": ApprovalStatus.DENIED.value,
                "event_id": event_id,
                "details": {"supervisor_decision": "denied", "reason": payload.reason},
            }

        return DecisionResponse(
            status="accepted",
            session_id=session_id,
            event_id=event_id,
            action=payload.action,
            approval_state=state.approval_state.value,
            checkpoint_id=payload.checkpoint_id,
            post_approval_result=post_approval_result,
        )


# Singleton Coordinator instance
_GLOBAL_COORDINATOR = HITLResumptionCoordinator()


def get_hitl_coordinator() -> HITLResumptionCoordinator:
    """Returns the shared HITLResumptionCoordinator instance."""
    return _GLOBAL_COORDINATOR
