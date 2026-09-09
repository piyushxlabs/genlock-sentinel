"""Global pytest fixtures and environment configuration for Genlock Sentinel test suites."""

from __future__ import annotations

import os
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Enforces deterministic mock execution by default across all test suites.

    Prevents unexpected live Vertex AI / gRPC network latency during automated testing.
    """
    if "GENLOCK_SENTINEL_FORCE_MOCK" not in os.environ:
        monkeypatch.setenv("GENLOCK_SENTINEL_FORCE_MOCK", "true")

    if os.environ.get("GENLOCK_SENTINEL_FORCE_MOCK") == "true":
        backend_dir = Path(__file__).resolve().parent.parent
        test_db = (backend_dir / "sentinel_test_sessions.db").resolve().as_posix()
        monkeypatch.setenv("ADK_SESSION_DB_URL", f"sqlite+aiosqlite:///{test_db}")
        monkeypatch.setenv("OTEL_GCP_TRACE_OTLP_ENDPOINT", "")
