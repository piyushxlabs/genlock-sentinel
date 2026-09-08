"""Genlock Sentinel — Checkpointing Backend.

Implements durable session state checkpointing via ADK's DatabaseSessionService
supporting Cloud SQL PostgreSQL (asyncpg) and local development SQLite (aiosqlite)
per AGENT_MASTER_PLAN.md Section 4, Step 4, Section 10, Step 8, and
AGENT_ORCHESTRATION_BLUEPRINT.md Section 3 & 5.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import dotenv
from google.adk.events import Event, EventActions
from google.adk.sessions import DatabaseSessionService, Session

from src.state.schema import GenlockSentinelState
from src.utils.errors import AgentError


def load_backend_env() -> None:
    """Ensures backend/.env is loaded."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    env_file = backend_dir / ".env"
    if env_file.exists():
        dotenv.load_dotenv(dotenv_path=env_file)
    else:
        dotenv.load_dotenv()


def get_database_url() -> str:
    """Resolves and normalizes the async database connection URL from environment.

    Supports ADK_SESSION_DB_URL and CLOUD_SQL_POSTGRES_URL.
    Normalizes relative SQLite paths relative to backend directory.
    """
    load_backend_env()
    raw_url = os.environ.get("ADK_SESSION_DB_URL") or os.environ.get("CLOUD_SQL_POSTGRES_URL")
    if not raw_url:
        raw_url = "sqlite+aiosqlite:///./sentinel_sessions.db"

    # Normalize relative SQLite paths to absolute file paths
    if raw_url.startswith("sqlite+aiosqlite:///."):
        backend_dir = Path(__file__).resolve().parent.parent.parent
        # Strip leading "sqlite+aiosqlite:///"
        rel_path = raw_url.replace("sqlite+aiosqlite:///", "", 1)
        abs_path = (backend_dir / rel_path).resolve().as_posix()
        return f"sqlite+aiosqlite:///{abs_path}"

    return raw_url


def create_session_service(db_url: Optional[str] = None) -> DatabaseSessionService:
    """Instantiates an ADK DatabaseSessionService using the specified or default DB URL."""
    resolved_url = db_url or get_database_url()
    return DatabaseSessionService(db_url=resolved_url)


async def init_checkpoint_db(
    session_service: Optional[DatabaseSessionService] = None,
    db_url: Optional[str] = None,
) -> DatabaseSessionService:
    """Initializes checkpoint database tables asynchronously via prepare_tables()."""
    svc = session_service or create_session_service(db_url=db_url)
    await svc.prepare_tables()
    return svc


# ------------------------------------------------------------------------------
# High-Level Typed Checkpoint Operations
# ------------------------------------------------------------------------------

async def save_checkpoint(
    session_id: str,
    state: GenlockSentinelState,
    user_id: str = "supervisor-01",
    app_name: str = "genlock_sentinel",
    session_service: Optional[DatabaseSessionService] = None,
) -> Session:
    """Durably writes or updates a GenlockSentinelState checkpoint in the database.

    Serializes the full 10-field typed state into the ADK Session storage.
    If the session exists, appends a state delta Event to update storage atomically.
    """
    svc = session_service or create_session_service()
    await svc.prepare_tables()

    state_dict: Dict[str, Any] = state.model_dump(mode="json")

    # Check if session exists
    try:
        existing_session = await svc.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
    except Exception:
        existing_session = None

    if existing_session is None:
        # Create fresh session with initial checkpoint state
        return await svc.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            state=state_dict,
        )

    # Session exists: append state update event to atomically refresh state in DB
    update_event = Event(
        author="genlock_sentinel_checkpoint",
        actions=EventActions(state_delta=state_dict),
        timestamp=time.time(),
    )
    await svc.append_event(session=existing_session, event=update_event)
    # Fetch refreshed session
    return await svc.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )


async def load_checkpoint(
    session_id: str,
    user_id: str = "supervisor-01",
    app_name: str = "genlock_sentinel",
    session_service: Optional[DatabaseSessionService] = None,
) -> Optional[GenlockSentinelState]:
    """Retrieves and reconstructs the validated GenlockSentinelState from storage.

    Returns None if no session exists for the given session_id.
    """
    svc = session_service or create_session_service()
    await svc.prepare_tables()

    try:
        session = await svc.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
    except Exception:
        return None

    if session is None or not session.state:
        return None

    return GenlockSentinelState.model_validate(session.state)


async def delete_checkpoint(
    session_id: str,
    user_id: str = "supervisor-01",
    app_name: str = "genlock_sentinel",
    session_service: Optional[DatabaseSessionService] = None,
) -> bool:
    """Deletes a session checkpoint from the database.

    Returns True if deletion succeeded, False otherwise.
    """
    svc = session_service or create_session_service()
    await svc.prepare_tables()

    try:
        await svc.delete_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
        return True
    except Exception:
        return False


async def list_checkpoints(
    user_id: str = "supervisor-01",
    app_name: str = "genlock_sentinel",
    session_service: Optional[DatabaseSessionService] = None,
) -> List[str]:
    """Lists all stored session IDs for the user and application."""
    svc = session_service or create_session_service()
    await svc.prepare_tables()

    response = await svc.list_sessions(
        app_name=app_name,
        user_id=user_id,
    )
    sessions_list = response.sessions if hasattr(response, "sessions") else response
    return [s.id for s in sessions_list]
