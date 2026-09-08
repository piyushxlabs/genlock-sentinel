"""Genlock Sentinel — Main FastAPI Application & ADK 2.x Runner Bootstrap.

Implements the ADK Runner bootstrap configured with StreamingMode.SSE
per AGENT_MASTER_PLAN.md Section 4, Step 1 and Section 10, Step 5.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from google.adk import Event, Runner
from google.adk.agents._streaming_mode import StreamingMode
from google.adk.runners import RunConfig
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.adk.workflow import Edge, FunctionNode, START, Workflow
from pydantic import BaseModel, ConfigDict, Field


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


if __name__ == "__main__":
    print("--- Genlock Sentinel ADK Runner Bootstrap ---")
    events = asyncio.run(run_noop_agent())
    print(f"Bootstrap run completed successfully! Total Events: {len(events)}")
    for idx, evt in enumerate(events, 1):
        print(f"  [{idx}] Event author={evt.author} actions={evt.actions}")
