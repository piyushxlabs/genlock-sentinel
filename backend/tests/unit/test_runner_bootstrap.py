"""Unit tests for Step 5: ADK Runner Bootstrap & Health Endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import (
    app,
    create_adk_runner,
    get_streaming_mode,
    run_noop_agent,
)


@pytest.mark.asyncio
async def test_streaming_mode_is_sse():
    """Confirms StreamingMode is configured to SSE per Master Plan Section 4."""
    mode = get_streaming_mode()
    assert str(mode).lower().endswith("sse")


@pytest.mark.asyncio
async def test_runner_instantiation():
    """Confirms create_adk_runner returns an instantiated Runner instance."""
    runner = create_adk_runner()
    assert runner is not None
    assert runner.app_name == "genlock_sentinel"


@pytest.mark.asyncio
async def test_trivial_noop_run_completes():
    """Confirms a trivial no-op ADK agent run completes end-to-end and yields events."""
    events = await run_noop_agent(
        user_id="test_operator", session_id="test_session_step5"
    )
    assert len(events) >= 1
    event = events[0]
    assert event.author == "genlock_sentinel_bootstrap"


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Confirms FastAPI /health endpoint returns healthy status and SSE streaming mode."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "genlock_sentinel"
        assert data["streaming_mode"] == "SSE"
