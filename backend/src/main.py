"""Genlock Sentinel — Main FastAPI Application & ADK 2.x Runner Bootstrap.

Implements the ADK Runner bootstrap configured with StreamingMode.SSE
per AGENT_MASTER_PLAN.md Section 4, Step 1 and Section 10, Step 5.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional

import dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from google.adk import Event, Runner
from google.adk.agents._streaming_mode import StreamingMode
from google.adk.runners import RunConfig
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.adk.workflow import Edge, FunctionNode, START, Workflow
from pydantic import BaseModel, ConfigDict, Field

from src.state.checkpointing import load_checkpoint, save_checkpoint
from src.state.schema import (
    ApprovalStatus,
    ErrorRecord,
    GenlockSentinelState,
    RemediationAction,
    SessionStatus,
    utc_now_iso,
)
from src.ui.agui_bridge import get_event_bridge


# ------------------------------------------------------------------------------
# Environment & Credential Bootstrap
# ------------------------------------------------------------------------------

def configure_environment() -> None:
    """Loads environment variables and aligns Google Cloud & Vertex AI credentials."""
    backend_dir = Path(__file__).resolve().parent.parent
    env_file = backend_dir / ".env"
    if env_file.exists():
        dotenv.load_dotenv(dotenv_path=env_file)
    else:
        dotenv.load_dotenv()

    # Resolve relative service account path to absolute path
    gcp_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gcp_creds:
        creds_path = Path(gcp_creds)
        if not creds_path.is_absolute():
            resolved_path = (backend_dir / creds_path).resolve()
            if resolved_path.exists():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(resolved_path)

        # Ensure google-genai and ADK use Vertex AI backend
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")


configure_environment()


# ------------------------------------------------------------------------------
# Models & Factory Functions
# ------------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health check response schema."""

    model_config = ConfigDict(strict=True, extra="forbid")

    status: str = Field(..., description="Service operational status")
    app_name: str = Field(..., description="Registered ADK application identifier")
    streaming_mode: str = Field(..., description="Active ADK streaming protocol mode")
    vertex_ai_enabled: bool = Field(..., description="Vertex AI client configuration flag")


class DecisionRequest(BaseModel):
    """Supervisor decision payload for pending HITL operation."""

    model_config = ConfigDict(strict=True, extra="forbid")

    action: Literal["approve", "deny"] = Field(..., description="Decision action: 'approve' or 'deny'")
    checkpoint_id: str = Field(..., description="Checkpoint ID matching pending card (e.g. hitl_pause::<event_id>)")
    modified_inputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Must be None (no editable fields exist)"
    )
    reason: Optional[str] = Field(default=None, description="Optional supervisor-supplied denial reason")


class DecisionResponse(BaseModel):
    """Response returned upon processing supervisor decision."""

    model_config = ConfigDict(strict=True, extra="forbid")

    status: str = Field(..., description="Operation result status: 'accepted'")
    session_id: str = Field(..., description="Active session ID")
    event_id: str = Field(..., description="Drift event ID")
    action: str = Field(..., description="Approved or denied action")
    approval_state: str = Field(..., description="Resulting approval_state in state")
    checkpoint_id: str = Field(..., description="Matched checkpoint ID")


class StopSessionRequest(BaseModel):
    """Payload for emergency session stop."""

    model_config = ConfigDict(strict=True, extra="forbid")

    reason: Optional[str] = Field(default="Supervisor emergency stop requested", description="Reason for stopping session")
    supervisor_id: Optional[str] = Field(default="on_set_supervisor", description="Identifier of supervisor triggering stop")


class StopSessionResponse(BaseModel):
    """Response returned upon halting session."""

    model_config = ConfigDict(strict=True, extra="forbid")

    status: str = Field(default="stopped", description="Session state status")
    session_id: str = Field(..., description="Halted session ID")
    stopped_at: str = Field(..., description="ISO 8601 UTC timestamp of halt")
    message: str = Field(..., description="Confirmation message")


HealthResponse.model_rebuild()
DecisionRequest.model_rebuild()
DecisionResponse.model_rebuild()
StopSessionRequest.model_rebuild()
StopSessionResponse.model_rebuild()


def get_streaming_mode() -> StreamingMode:
    """Returns the constitutional StreamingMode.SSE for ADK runners."""
    return StreamingMode.SSE


def get_default_session_service() -> BaseSessionService:
    """Returns the default session service (InMemorySessionService for initial bootstrap)."""
    return InMemorySessionService()


async def _noop_sentinel_function() -> Dict[str, str]:
    """Trivial no-op node function for runtime verification."""
    return {"status": "noop_verified", "runtime": "adk_2.x"}


def create_default_workflow() -> Workflow:
    """Creates a trivial single-node Workflow for bootstrap verification."""
    noop_node = FunctionNode(name="noop_sentinel_node", func=_noop_sentinel_function)
    return Workflow(
        name="genlock_sentinel_bootstrap",
        edges=[Edge(from_node=START, to_node=noop_node)],
    )


def create_adk_runner(
    node: Optional[Any] = None,
    session_service: Optional[BaseSessionService] = None,
    app_name: str = "genlock_sentinel",
) -> Runner:
    """Instantiates and returns an ADK 2.x Runner configured for Genlock Sentinel."""
    active_node = node or create_default_workflow()
    active_session_service = session_service or get_default_session_service()

    return Runner(
        app_name=app_name,
        node=active_node,
        session_service=active_session_service,
    )


async def run_noop_agent(
    user_id: str = "sentinel_operator",
    session_id: str = "bootstrap_verification_session",
) -> List[Event]:
    """Executes a trivial no-op ADK agent run end-to-end with StreamingMode.SSE."""
    session_service = get_default_session_service()
    runner = create_adk_runner(session_service=session_service)

    # Ensure session is created
    await session_service.create_session(
        app_name="genlock_sentinel",
        user_id=user_id,
        session_id=session_id,
    )

    run_cfg = RunConfig(streaming_mode=get_streaming_mode())
    events: List[Event] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        run_config=run_cfg,
    ):
        events.append(event)

    return events


# ------------------------------------------------------------------------------
# FastAPI Lifespan & Application Definition
# ------------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup and graceful shutdown."""
    configure_environment()
    yield


app = FastAPI(
    title="Genlock Sentinel Agent API",
    description="Autonomous telemetry-driven SRE & frame-sync integrity agent for ICVFX nDisplay stages",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/healthz", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Readiness and health check endpoint."""
    vertex_enabled = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
    return HealthResponse(
        status="healthy",
        app_name="genlock_sentinel",
        streaming_mode="SSE",
        vertex_ai_enabled=vertex_enabled,
    )


@app.get("/")
async def root() -> JSONResponse:
    """Root metadata endpoint."""
    return JSONResponse(
        content={
            "service": "Genlock Sentinel",
            "version": "0.1.0",
            "description": "ICVFX Frame-Sync Integrity Agent",
            "status": "online",
        }
    )


@app.get("/sessions/{session_id}/stream")
async def session_stream(
    session_id: str,
    max_events: Optional[int] = None,
) -> StreamingResponse:
    """Server-Sent Events stream endpoint for live operations console synchronization.

    Streams typed AG-UI events per AGENT_MASTER_PLAN.md Section 7 and
    INTERFACE_OBSERVABILITY_SYSTEM.md Section 2 & 2a.
    """
    bridge = get_event_bridge()
    return StreamingResponse(
        bridge.stream_session_events(session_id=session_id, max_events=max_events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post(
    "/sessions/{session_id}/events/{event_id}/decision",
    response_model=DecisionResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_decision(
    session_id: str,
    event_id: str,
    payload: DecisionRequest,
) -> DecisionResponse:
    """Processes supervisor Approve or Deny decisions for pending HITL cards.

    Performs strict validation per INTERFACE_OBSERVABILITY_SYSTEM.md Section 5:
    - Verifies session exists in checkpoint storage.
    - Verifies pending_hitl_card exists and matches event_id.
    - Rejects any non-null modified_inputs (no editable fields permitted).
    - Verifies checkpoint_id matches pending checkpoint.
    - Updates approval_state, session_status, logs audit action, and saves checkpoint.
    """
    if payload.modified_inputs is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modifying inputs is not permitted at this checkpoint (strict Approve/Deny only).",
        )

    state = await load_checkpoint(session_id=session_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    if state.pending_hitl_card is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No pending HITL card found for session '{session_id}'.",
        )

    card = state.pending_hitl_card
    if card.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event ID mismatch: pending card is for '{card.event_id}', but received '{event_id}'.",
        )

    valid_checkpoint_ids = {
        f"hitl_pause::{card.event_id}",
        card.card_id,
        card.event_id,
    }
    if payload.checkpoint_id not in valid_checkpoint_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Checkpoint ID mismatch: '{payload.checkpoint_id}' does not match pending card checkpoint.",
        )

    # Apply decision mutation
    if payload.action == "approve":
        state.approval_state = ApprovalStatus.APPROVED
        state.session_status = SessionStatus.RESUMED
        state.remediation_log.append(
            RemediationAction(
                event_id=event_id,
                node_id=card.node_id,
                action_taken=f"supervisor_approved::{card.proposed_action}",
                success=True,
                details={"checkpoint_id": payload.checkpoint_id},
            )
        )
    else:
        state.approval_state = ApprovalStatus.DENIED
        state.session_status = SessionStatus.MONITORING
        state.error_logs.append(
            ErrorRecord(
                event_id=event_id,
                node_id=card.node_id,
                error_type="SupervisorDenial",
                message=f"Supervisor denied action '{card.proposed_action}' for event '{event_id}'. Reason: {payload.reason or 'None'}",
            )
        )
        state.remediation_log.append(
            RemediationAction(
                event_id=event_id,
                node_id=card.node_id,
                action_taken=f"supervisor_denied::{card.proposed_action}",
                success=False,
                details={"reason": payload.reason, "checkpoint_id": payload.checkpoint_id},
            )
        )

    # Persist updated state to checkpoint store
    await save_checkpoint(session_id=session_id, state=state)

    return DecisionResponse(
        status="accepted",
        session_id=session_id,
        event_id=event_id,
        action=payload.action,
        approval_state=state.approval_state.value,
        checkpoint_id=payload.checkpoint_id,
    )


@app.post(
    "/sessions/{session_id}/stop",
    response_model=StopSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def stop_session(
    session_id: str,
    payload: Optional[StopSessionRequest] = None,
) -> StopSessionResponse:
    """Executes supervisor emergency stop halting all autonomous action immediately.

    Preserves current state in checkpoint storage per AGENT_MASTER_PLAN.md Section 8.
    """
    req = payload or StopSessionRequest()
    state = await load_checkpoint(session_id=session_id)

    stopped_ts = utc_now_iso()

    if state is not None:
        state.session_status = SessionStatus.STOPPED
        state.approval_state = ApprovalStatus.HALTED
        state.error_logs.append(
            ErrorRecord(
                error_type="EmergencyStop",
                message=f"Emergency stop executed by {req.supervisor_id} at {stopped_ts}. Reason: {req.reason}",
            )
        )
        await save_checkpoint(session_id=session_id, state=state)
    else:
        # Create minimal halted state to persist stop record
        halted_state = GenlockSentinelState(
            session_id=session_id,
            session_status=SessionStatus.STOPPED,
            approval_state=ApprovalStatus.HALTED,
            error_logs=[
                ErrorRecord(
                    error_type="EmergencyStop",
                    message=f"Emergency stop executed for uncheckpointed session at {stopped_ts}.",
                )
            ],
        )
        await save_checkpoint(session_id=session_id, state=halted_state)

    return StopSessionResponse(
        status="stopped",
        session_id=session_id,
        stopped_at=stopped_ts,
        message=f"Session '{session_id}' halted immediately. State checkpointed successfully.",
    )


if __name__ == "__main__":
    print("--- Genlock Sentinel ADK Runner Bootstrap ---")
    events = asyncio.run(run_noop_agent())
    print(f"Bootstrap run completed successfully! Total Events: {len(events)}")
    for idx, evt in enumerate(events, 1):
        print(f"  [{idx}] Event author={evt.author} actions={evt.actions}")

