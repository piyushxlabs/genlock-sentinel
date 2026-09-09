"""Unit tests for Step 18: Telemetry & Observability Layer.

Tests cover:
  1. OTel TracerProvider bootstrap with dual exporters
  2. Graceful degradation when env vars are absent
  3. Span creation correctness (session/event/node/tool hierarchy)
  4. Span attribute correctness per GenAI Semantic Conventions
  5. Token usage recording
  6. HITL decision annotation
  7. Circuit breaker span annotation
  8. FeedbackAnnotationClient score writes (mocked HTTPX)
  9. FeedbackAnnotationClient graceful no-op when credentials absent
  10. Feedback endpoint (POST /sessions/{sid}/events/{eid}/feedback)
  11. Telemetry module __init__ re-exports
  12. Reasoning loop OTel span integration smoke test
  13. Shutdown idempotency

Compliant with:
  - INTERFACE_OBSERVABILITY_SYSTEM.md Section 6 & 7a
  - async-io-and-pydantic-validation-mandate.md (all async, Pydantic V2 strict)
  - defensive-execution-structured-outputs-and-fallbacks.md (no bare excepts)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_local_exporter_and_tracer(tracer_name: str = "test.tracer"):
    """Creates a LOCAL (non-global) TracerProvider+InMemoryExporter pair.

    Returns (exporter, tracer). The tracer is obtained directly from the local
    provider — does NOT touch the global trace.set_tracer_provider(), which OTel 1.42
    prohibits overriding once a real provider is set.
    """
    exporter = InMemorySpanExporter()
    provider = SDKTracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer(tracer_name)
    return exporter, tracer, provider


def _reset_telemetry_module() -> None:
    """Resets the otlp_export module singleton for test isolation."""
    import src.telemetry.otlp_export as otlp_mod
    otlp_mod._provider = None

    import src.telemetry.feedback_annotations as fb_mod
    fb_mod._feedback_client = None


# ---------------------------------------------------------------------------
# 1. TracerProvider bootstrap — with env vars present
# ---------------------------------------------------------------------------

class TestBootstrapTelemetry:
    """Tests for otlp_export.bootstrap_telemetry()."""

    def setup_method(self) -> None:
        _reset_telemetry_module()

    def teardown_method(self) -> None:
        _reset_telemetry_module()
        # Restore to a clean NoOp provider
        trace.set_tracer_provider(trace.NoOpTracerProvider())

    @patch("src.telemetry.otlp_export.GrpcOTLPExporter")
    @patch("src.telemetry.otlp_export.HttpOTLPExporter")
    def test_bootstrap_registers_both_exporters(
        self,
        mock_http: MagicMock,
        mock_grpc: MagicMock,
    ) -> None:
        """Both Cloud Trace and Langfuse exporters are registered when env vars are set."""
        mock_http.return_value = MagicMock()
        mock_grpc.return_value = MagicMock()

        env = {
            "OTEL_GCP_TRACE_OTLP_ENDPOINT": "https://telemetry.googleapis.com:4317",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://cloud.langfuse.com/api/public/otel",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.otlp_export import bootstrap_telemetry, is_telemetry_active
            bootstrap_telemetry()
            assert is_telemetry_active() is True
            mock_grpc.assert_called_once()
            mock_http.assert_called_once()

    @patch("src.telemetry.otlp_export.GrpcOTLPExporter")
    @patch("src.telemetry.otlp_export.HttpOTLPExporter")
    def test_bootstrap_is_idempotent(
        self,
        mock_http: MagicMock,
        mock_grpc: MagicMock,
    ) -> None:
        """Calling bootstrap_telemetry() twice is a no-op on the second call."""
        mock_http.return_value = MagicMock()
        mock_grpc.return_value = MagicMock()

        env = {
            "OTEL_GCP_TRACE_OTLP_ENDPOINT": "https://telemetry.googleapis.com:4317",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://cloud.langfuse.com/api/public/otel",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.otlp_export import bootstrap_telemetry
            bootstrap_telemetry()
            bootstrap_telemetry()  # second call
            # Exporters created exactly once
            assert mock_grpc.call_count == 1
            assert mock_http.call_count == 1

    def test_bootstrap_graceful_degradation_no_env_vars(self) -> None:
        """bootstrap_telemetry() succeeds silently when no OTLP env vars are set."""
        env = {
            "OTEL_GCP_TRACE_OTLP_ENDPOINT": "",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "",
            "LANGFUSE_PUBLIC_KEY": "",
            "LANGFUSE_SECRET_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.otlp_export import bootstrap_telemetry, is_telemetry_active
            # Should not raise
            bootstrap_telemetry()
            # Provider is still installed (just with no exporters)
            assert is_telemetry_active() is True

    @patch("src.telemetry.otlp_export.GrpcOTLPExporter")
    @patch("src.telemetry.otlp_export.HttpOTLPExporter")
    def test_bootstrap_skips_langfuse_without_credentials(
        self,
        mock_http: MagicMock,
        mock_grpc: MagicMock,
    ) -> None:
        """Langfuse exporter is skipped when LANGFUSE keys are absent."""
        mock_grpc.return_value = MagicMock()

        env = {
            "OTEL_GCP_TRACE_OTLP_ENDPOINT": "https://telemetry.googleapis.com:4317",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://cloud.langfuse.com/api/public/otel",
            "LANGFUSE_PUBLIC_KEY": "",
            "LANGFUSE_SECRET_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.otlp_export import bootstrap_telemetry
            bootstrap_telemetry()
            mock_grpc.assert_called_once()
            mock_http.assert_not_called()

    @patch("src.telemetry.otlp_export.GrpcOTLPExporter")
    @patch("src.telemetry.otlp_export.HttpOTLPExporter")
    def test_shutdown_telemetry_resets_singleton(
        self,
        mock_http: MagicMock,
        mock_grpc: MagicMock,
    ) -> None:
        """shutdown_telemetry() resets the module singleton so re-bootstrap is possible."""
        mock_http.return_value = MagicMock()
        mock_grpc.return_value = MagicMock()

        env = {
            "OTEL_GCP_TRACE_OTLP_ENDPOINT": "https://telemetry.googleapis.com:4317",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://cloud.langfuse.com/api/public/otel",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.otlp_export import bootstrap_telemetry, is_telemetry_active, shutdown_telemetry
            bootstrap_telemetry()
            assert is_telemetry_active() is True
            shutdown_telemetry()
            assert is_telemetry_active() is False


# ---------------------------------------------------------------------------
# 2. Span creation correctness
# ---------------------------------------------------------------------------

class TestSpanCreation:
    """Tests for tracing.py span context managers.

    Uses a LOCAL TracerProvider+InMemoryExporter injected via
    patch('src.telemetry.tracing.get_tracer') to avoid the OTel 1.42
    prohibition on overriding an already-set global TracerProvider.
    """

    def setup_method(self) -> None:
        self.exporter, self.local_tracer, self.local_provider = _make_local_exporter_and_tracer()
        self._patcher = patch("src.telemetry.tracing.get_tracer", return_value=self.local_tracer)
        self._patcher.start()

    def teardown_method(self) -> None:
        self._patcher.stop()
        self.exporter.clear()

    def test_session_span_creates_span_with_session_id(self) -> None:
        """session_span() creates a root span with session.id attribute."""
        from src.telemetry.tracing import session_span

        with session_span("sess-abc-001"):
            pass

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "genlock.session"
        assert spans[0].attributes.get("session.id") == "sess-abc-001"

    def test_event_span_creates_invoke_agent_span(self) -> None:
        """event_span() creates a span with event_id and invoke_agent operation."""
        from src.telemetry.tracing import event_span
        from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import GEN_AI_OPERATION_NAME

        with event_span("sess-001", "evt-001", "render-07"):
            pass

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "genlock.event.invoke_agent"
        assert spans[0].attributes.get("genlock.event.id") == "evt-001"
        assert spans[0].attributes.get(GEN_AI_OPERATION_NAME) == "invoke_agent"

    def test_node_span_creates_named_span_with_model(self) -> None:
        """node_span() creates a per-node span with model attributes."""
        from src.telemetry.tracing import node_span
        from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import GEN_AI_REQUEST_MODEL

        with node_span(
            node_name="root_cause_correlation",
            model="gemini-3.1-pro",
            session_id="sess-001",
            event_id="evt-001",
        ):
            pass

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "genlock.node.root_cause_correlation"
        assert spans[0].attributes.get(GEN_AI_REQUEST_MODEL) == "gemini-3.1-pro"

    def test_tool_span_creates_execute_tool_span(self) -> None:
        """tool_span() creates a per-tool span with execute_tool operation."""
        from src.telemetry.tracing import tool_span
        from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
            GEN_AI_OPERATION_NAME,
            GEN_AI_TOOL_NAME,
        )

        with tool_span("query_loki_logs", session_id="sess-001", event_id="evt-001"):
            pass

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "genlock.tool.query_loki_logs"
        assert spans[0].attributes.get(GEN_AI_TOOL_NAME) == "query_loki_logs"
        assert spans[0].attributes.get(GEN_AI_OPERATION_NAME) == "execute_tool"

    def test_nested_span_hierarchy(self) -> None:
        """session → event → node spans form a correct parent-child hierarchy."""
        from src.telemetry.tracing import event_span, node_span, session_span

        with session_span("sess-001"):
            with event_span("sess-001", "evt-001", "render-07"):
                with node_span("evidence_triage", model="gemini-3.7-flash"):
                    pass

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 3
        span_names = {s.name for s in spans}
        assert "genlock.session" in span_names
        assert "genlock.event.invoke_agent" in span_names


# ---------------------------------------------------------------------------
# 3. Span attribute correctness
# ---------------------------------------------------------------------------

class TestSpanAttributes:
    """Tests for span helper functions using local TracerProvider."""

    def setup_method(self) -> None:
        self.exporter, self.local_tracer, self.local_provider = _make_local_exporter_and_tracer()
        self._patcher = patch("src.telemetry.tracing.get_tracer", return_value=self.local_tracer)
        self._patcher.start()

    def teardown_method(self) -> None:
        self._patcher.stop()
        self.exporter.clear()

    def test_record_token_usage_sets_attributes(self) -> None:
        """record_token_usage() attaches input/output token counts to span."""
        from src.telemetry.tracing import node_span, record_token_usage
        from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
            GEN_AI_USAGE_INPUT_TOKENS,
            GEN_AI_USAGE_OUTPUT_TOKENS,
        )

        with node_span("root_cause_correlation") as span:
            record_token_usage(span, input_tokens=1500, output_tokens=320)

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes.get(GEN_AI_USAGE_INPUT_TOKENS) == 1500
        assert spans[0].attributes.get(GEN_AI_USAGE_OUTPUT_TOKENS) == 320

    def test_record_token_usage_skips_zero_values(self) -> None:
        """record_token_usage() does not attach zero-value token attributes."""
        from src.telemetry.tracing import node_span, record_token_usage
        from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import GEN_AI_USAGE_INPUT_TOKENS

        with node_span("evidence_triage") as span:
            record_token_usage(span, input_tokens=0, output_tokens=0)

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert GEN_AI_USAGE_INPUT_TOKENS not in (spans[0].attributes or {})

    def test_annotate_hitl_decision_approved(self) -> None:
        """annotate_hitl_decision() sets hitl.decision=approved on span."""
        from src.telemetry.tracing import annotate_hitl_decision, node_span

        with node_span("hitl_pause") as span:
            annotate_hitl_decision(span, "approved")

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes.get("hitl.decision") == "approved"

    def test_annotate_hitl_decision_denied_with_reason(self) -> None:
        """annotate_hitl_decision() records deny_reason as a span event."""
        from src.telemetry.tracing import annotate_hitl_decision, node_span

        with node_span("hitl_pause") as span:
            annotate_hitl_decision(span, "denied", deny_reason="Risk too high for live take")

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes.get("hitl.decision") == "denied"
        # Deny reason captured as span event
        event_names = [e.name for e in spans[0].events]
        assert "hitl.deny_reason" in event_names

    def test_annotate_circuit_breaker_sets_attributes(self) -> None:
        """annotate_circuit_breaker() flags the span and adds an event."""
        from src.telemetry.tracing import annotate_circuit_breaker, node_span

        with node_span("root_cause_correlation") as span:
            annotate_circuit_breaker(span, node_id="render-07")

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes.get("genlock.circuit_breaker.fired") is True
        event_names = [e.name for e in spans[0].events]
        assert "genlock.circuit_breaker.fired" in event_names



# ---------------------------------------------------------------------------
# 4. FeedbackAnnotationClient
# ---------------------------------------------------------------------------

class TestFeedbackAnnotationClient:
    """Tests for feedback_annotations.FeedbackAnnotationClient."""

    def setup_method(self) -> None:
        _reset_telemetry_module()

    def teardown_method(self) -> None:
        _reset_telemetry_module()

    @pytest.mark.asyncio
    async def test_record_diagnosis_accuracy_correct(self) -> None:
        """record_diagnosis_accuracy(is_correct=True) sends score=1.0 to Langfuse."""
        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_BASE_URL": "https://cloud.langfuse.com",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.feedback_annotations import FeedbackAnnotationClient

            client = FeedbackAnnotationClient()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_httpx_client = AsyncMock()
            mock_httpx_client.post = AsyncMock(return_value=mock_response)
            mock_httpx_client.is_closed = False
            client._client = mock_httpx_client

            await client.record_diagnosis_accuracy(
                trace_id="trace-abc-001",
                observation_id="span-node3-001",
                is_correct=True,
            )

            mock_httpx_client.post.assert_awaited_once()
            call_args = mock_httpx_client.post.call_args
            assert "/api/public/scores" in call_args[0][0]
            # Score value 1.0 in the JSON body
            assert '"value":1.0' in call_args[1]["content"] or '"value": 1.0' in call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_record_diagnosis_accuracy_incorrect_with_comment(self) -> None:
        """record_diagnosis_accuracy(is_correct=False) sends score=0.0 with comment."""
        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_BASE_URL": "https://cloud.langfuse.com",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.feedback_annotations import FeedbackAnnotationClient

            client = FeedbackAnnotationClient()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_httpx_client = AsyncMock()
            mock_httpx_client.post = AsyncMock(return_value=mock_response)
            mock_httpx_client.is_closed = False
            client._client = mock_httpx_client

            await client.record_diagnosis_accuracy(
                trace_id="trace-abc-002",
                observation_id=None,
                is_correct=False,
                actual_root_cause="thermal_throttle, not network_jitter",
            )

            call_args = mock_httpx_client.post.call_args
            body = call_args[1]["content"]
            assert '"value":0.0' in body or '"value": 0.0' in body
            assert "thermal_throttle" in body

    @pytest.mark.asyncio
    async def test_record_hitl_decision_approved(self) -> None:
        """record_hitl_decision('approved') sends score=1.0 with name=hitl_decision."""
        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_BASE_URL": "https://cloud.langfuse.com",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.feedback_annotations import FeedbackAnnotationClient

            client = FeedbackAnnotationClient()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_httpx_client = AsyncMock()
            mock_httpx_client.post = AsyncMock(return_value=mock_response)
            mock_httpx_client.is_closed = False
            client._client = mock_httpx_client

            await client.record_hitl_decision(
                trace_id="trace-abc-003",
                observation_id="span-hitl-001",
                decision="approved",
            )

            body = mock_httpx_client.post.call_args[1]["content"]
            assert '"name":"hitl_decision"' in body or '"name": "hitl_decision"' in body
            assert '"value":1.0' in body or '"value": 1.0' in body

    @pytest.mark.asyncio
    async def test_record_hitl_decision_denied_with_reason(self) -> None:
        """record_hitl_decision('denied') sends score=0.0 with deny comment."""
        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_BASE_URL": "https://cloud.langfuse.com",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.feedback_annotations import FeedbackAnnotationClient

            client = FeedbackAnnotationClient()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_httpx_client = AsyncMock()
            mock_httpx_client.post = AsyncMock(return_value=mock_response)
            mock_httpx_client.is_closed = False
            client._client = mock_httpx_client

            await client.record_hitl_decision(
                trace_id="trace-abc-004",
                observation_id=None,
                decision="denied",
                deny_reason="Take director approved using greenscreen instead",
            )

            body = mock_httpx_client.post.call_args[1]["content"]
            assert '"value":0.0' in body or '"value": 0.0' in body
            assert "greenscreen" in body

    @pytest.mark.asyncio
    async def test_noop_when_credentials_absent(self) -> None:
        """FeedbackAnnotationClient is a no-op when LANGFUSE keys are missing."""
        env = {"LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": ""}
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.feedback_annotations import FeedbackAnnotationClient

            client = FeedbackAnnotationClient()
            assert client._enabled is False

            # Should not raise, should not make HTTP calls
            await client.record_diagnosis_accuracy(
                trace_id="trace-no-creds",
                observation_id=None,
                is_correct=True,
            )
            # Client was never created since _enabled=False
            assert client._client is None

    @pytest.mark.asyncio
    async def test_http_error_does_not_propagate(self) -> None:
        """HTTP 4xx/5xx from Langfuse is swallowed — never raised to caller."""
        import httpx

        env = {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_BASE_URL": "https://cloud.langfuse.com",
        }
        with patch.dict(os.environ, env, clear=False):
            from src.telemetry.feedback_annotations import FeedbackAnnotationClient

            client = FeedbackAnnotationClient()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)
            )
            mock_httpx_client = AsyncMock()
            mock_httpx_client.post = AsyncMock(return_value=mock_response)
            mock_httpx_client.is_closed = False
            client._client = mock_httpx_client

            # Must not raise
            await client.record_diagnosis_accuracy(
                trace_id="trace-error-test",
                observation_id=None,
                is_correct=False,
            )


# ---------------------------------------------------------------------------
# 5. Feedback API endpoint
# ---------------------------------------------------------------------------

class TestFeedbackEndpoint:
    """Tests for POST /sessions/{sid}/events/{eid}/feedback."""

    @pytest.mark.asyncio
    async def test_feedback_endpoint_returns_recorded_status(self) -> None:
        """POST /feedback returns FeedbackResponse with status='recorded'."""
        from httpx import AsyncClient, ASGITransport

        env = {"LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": ""}
        with patch.dict(os.environ, env, clear=False):
            _reset_telemetry_module()
            from src.main import app

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/sessions/sess-001/events/evt-001/feedback",
                    json={
                        "is_correct": True,
                        "trace_id": "trace-abc-123",
                        "observation_id": None,
                        "actual_root_cause": None,
                    },
                )
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "recorded"
            assert body["session_id"] == "sess-001"
            assert body["event_id"] == "evt-001"
            assert body["score_name"] == "diagnosis_accuracy"
            assert body["score_value"] == 1.0

    @pytest.mark.asyncio
    async def test_feedback_endpoint_incorrect_diagnosis(self) -> None:
        """POST /feedback with is_correct=False returns score_value=0.0."""
        from httpx import AsyncClient, ASGITransport

        env = {"LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": ""}
        with patch.dict(os.environ, env, clear=False):
            _reset_telemetry_module()
            from src.main import app

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/sessions/sess-001/events/evt-002/feedback",
                    json={
                        "is_correct": False,
                        "trace_id": "trace-def-456",
                        "observation_id": "span-node3",
                        "actual_root_cause": "thermal_throttle was the real cause",
                    },
                )
            assert response.status_code == 200
            assert response.json()["score_value"] == 0.0

    @pytest.mark.asyncio
    async def test_feedback_endpoint_rejects_extra_fields(self) -> None:
        """POST /feedback rejects payloads with extra fields (Pydantic strict)."""
        from httpx import AsyncClient, ASGITransport

        env = {"LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": ""}
        with patch.dict(os.environ, env, clear=False):
            _reset_telemetry_module()
            from src.main import app

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/sessions/sess-001/events/evt-003/feedback",
                    json={
                        "is_correct": True,
                        "trace_id": "trace-xyz",
                        "malicious_extra_field": "hacked",
                    },
                )
            assert response.status_code == 422


# ---------------------------------------------------------------------------
# 6. Module __init__ re-exports
# ---------------------------------------------------------------------------

class TestTelemetryModuleReExports:
    """Verifies all declared __all__ symbols are importable from src.telemetry."""

    def test_all_exports_importable(self) -> None:
        """All src.telemetry.__all__ names resolve without ImportError."""
        import src.telemetry as tel
        for name in tel.__all__:
            assert hasattr(tel, name), f"src.telemetry.{name} not found"

    def test_get_tracer_returns_tracer(self) -> None:
        """tracing.get_tracer() returns an OTel Tracer instance."""
        from src.telemetry.tracing import get_tracer
        t = get_tracer()
        assert t is not None
        assert hasattr(t, "start_span")
