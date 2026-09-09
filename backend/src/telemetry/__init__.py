"""Genlock Sentinel — OpenTelemetry GenAI Instrumentation and Feedback Pipeline.

Public API:
  bootstrap_telemetry()     — Call once at startup to configure TracerProvider.
  shutdown_telemetry()      — Call at shutdown to flush pending spans.
  is_telemetry_active()     — True if a real provider is installed.
  session_span()            — Root session span context manager.
  event_span()              — Per-drift-event span context manager.
  node_span()               — Per-node execution span context manager.
  tool_span()               — Per-tool-call span context manager.
  record_token_usage()      — Attaches token count attributes.
  mark_span_error()         — Records exception + ERROR status.
  annotate_hitl_decision()  — Records supervisor decision on HITL span.
  get_feedback_client()     — Returns the FeedbackAnnotationClient singleton.
"""

from src.telemetry.feedback_annotations import (
    FeedbackAnnotationClient,
    LangfuseScoreRequest,
    close_feedback_client,
    get_feedback_client,
)
from src.telemetry.otlp_export import (
    bootstrap_telemetry,
    is_telemetry_active,
    shutdown_telemetry,
)
from src.telemetry.tracing import (
    annotate_circuit_breaker,
    annotate_hitl_decision,
    annotate_state_delta,
    event_span,
    mark_span_error,
    mark_span_ok,
    node_span,
    record_token_usage,
    session_span,
    tool_span,
)

__all__ = [
    # Bootstrap
    "bootstrap_telemetry",
    "shutdown_telemetry",
    "is_telemetry_active",
    # Span context managers
    "session_span",
    "event_span",
    "node_span",
    "tool_span",
    # Span helpers
    "record_token_usage",
    "mark_span_error",
    "mark_span_ok",
    "annotate_hitl_decision",
    "annotate_circuit_breaker",
    "annotate_state_delta",
    # Feedback annotation
    "FeedbackAnnotationClient",
    "LangfuseScoreRequest",
    "get_feedback_client",
    "close_feedback_client",
]
