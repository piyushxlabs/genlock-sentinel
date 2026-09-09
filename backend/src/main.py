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
from src.telemetry.feedback_annotations import close_feedback_client, get_feedback_client
from src.telemetry.otlp_export import bootstrap_telemetry, shutdown_telemetry
from src.ui.agui_bridge import get_event_bridge
from src.ui.hitl_resumption import (
    DecisionRequest,
    DecisionResponse,
    get_hitl_coordinator,
)


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


# DecisionRequest and DecisionResponse are imported from src.ui.hitl_resumption


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
StopSessionRequest.model_rebuild()
StopSessionResponse.model_rebuild()


class FeedbackRequest(BaseModel):
    """Payload for post-hoc supervisor diagnosis feedback (Section 7a)."""

    model_config = ConfigDict(strict=True, extra="forbid")

    is_correct: bool = Field(
        ...,
        description="True if supervisor confirms diagnosis was correct; False if incorrect.",
    )
    actual_root_cause: Optional[str] = Field(
        default=None,
        description="Free-text actual root cause — required when is_correct is False.",
    )
    trace_id: str = Field(
        ...,
        description="OTel trace ID of the Root-Cause Correlation span for this event.",
    )
    observation_id: Optional[str] = Field(
        default=None,
        description="Span/observation ID of the Root-Cause Correlation node span.",
    )


class FeedbackResponse(BaseModel):
    """Acknowledgement of a feedback annotation write."""

    model_config = ConfigDict(strict=True, extra="forbid")

    status: str = Field(default="recorded", description="Annotation write status")
    session_id: str = Field(..., description="Session the feedback is for")
    event_id: str = Field(..., description="Event the feedback is for")
    score_name: str = Field(default="diagnosis_accuracy", description="Langfuse score name")
    score_value: float = Field(..., description="Score value written (1.0 correct / 0.0 incorrect)")


FeedbackRequest.model_rebuild()
FeedbackResponse.model_rebuild()


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
    # Bootstrap OTel TracerProvider — dual export (Cloud Trace + Langfuse)
    bootstrap_telemetry()
    yield
    # Flush all pending spans and close HTTPX feedback client on shutdown
    shutdown_telemetry()
    await close_feedback_client()


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

    Delegates to HITLResumptionCoordinator per AGENT_MASTER_PLAN.md Section 7 & 10 (Step 16)
    and INTERFACE_OBSERVABILITY_SYSTEM.md Section 5:
    - Verifies session exists in checkpoint storage.
    - Verifies pending_hitl_card exists and matches event_id.
    - Rejects any non-null modified_inputs (no editable fields permitted).
    - Verifies checkpoint_id matches pending checkpoint.
    - On Approve: updates approval_state, resumes session, logs approval,
      dispatches Node 7 (post-approval tool execution), broadcasts AG-UI SSE events,
      and saves checkpoint.
    - On Deny: updates approval_state, returns to monitoring, logs audit denial
      to error_logs and remediation_log, broadcasts AG-UI SSE events, and saves checkpoint.
    """
    coordinator = get_hitl_coordinator()
    return await coordinator.handle_decision(
        session_id=session_id,
        event_id=event_id,
        payload=payload,
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


@app.post(
    "/sessions/{session_id}/events/{event_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_feedback(
    session_id: str,
    event_id: str,
    payload: FeedbackRequest,
) -> FeedbackResponse:
    """Records post-hoc supervisor diagnosis accuracy feedback.

    Per INTERFACE_OBSERVABILITY_SYSTEM.md Section 7 & 7a:
    - Writes a Langfuse 'diagnosis_accuracy' score (1.0=correct / 0.0=incorrect).
    - If is_correct is False, the actual_root_cause comment is recorded alongside the score.
    - Never raises on annotation failure — returns status='recorded' regardless.
    """
    client = get_feedback_client()
    score_value = 1.0 if payload.is_correct else 0.0
    await client.record_diagnosis_accuracy(
        trace_id=payload.trace_id,
        observation_id=payload.observation_id,
        is_correct=payload.is_correct,
        actual_root_cause=payload.actual_root_cause,
    )
    return FeedbackResponse(
        status="recorded",
        session_id=session_id,
        event_id=event_id,
        score_name="diagnosis_accuracy",
        score_value=score_value,
    )


if __name__ == "__main__":
    print("--- Genlock Sentinel ADK Runner Bootstrap ---")
    events = asyncio.run(run_noop_agent())
    print(f"Bootstrap run completed successfully! Total Events: {len(events)}")
    for idx, evt in enumerate(events, 1):
        print(f"  [{idx}] Event author={evt.author} actions={evt.actions}")
