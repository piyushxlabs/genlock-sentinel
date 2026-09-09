"""Genlock Sentinel — OpenTelemetry GenAI Semantic Conventions Tracing Layer.

Implements the span hierarchy defined in INTERFACE_OBSERVABILITY_SYSTEM.md Section 6:

  Session trace (session_id)
    └─ per-drift-event invoke_agent span (event_id)
         └─ per-node span (step_name, GenAiOperationNameValues)
              └─ per-tool-call span (tool_name, execute_tool)

Attributes captured per spec:
  gen_ai.provider.name        = "gcp.gemini"
  gen_ai.request.model        = "gemini-3.1-pro" | "gemini-3.7-flash"
  gen_ai.response.model       = (same)
  gen_ai.operation.name       = invoke_agent | invoke_workflow | execute_tool
  gen_ai.tool.name            = <tool name>
  gen_ai.usage.input_tokens   = int (when available)
  gen_ai.usage.output_tokens  = int (when available)
  session.id                  = session_id
  event.id                    = event_id
  node.name                   = node identifier

W3C Trace Context propagation is automatic via BatchSpanProcessor.
"""

from __future__ import annotations

import contextlib
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator, Optional

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_RESPONSE_MODEL,
    GEN_AI_TOOL_NAME,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    GEN_AI_WORKFLOW_NAME,
    GenAiOperationNameValues,
    GenAiProviderNameValues,
)
from opentelemetry.trace import NonRecordingSpan, Span, StatusCode

logger = logging.getLogger(__name__)

# Module-level tracer — initialised once by otlp_export.bootstrap_telemetry()
# Before bootstrap, falls back to the global NoOpTracerProvider.
_TRACER_NAME = "genlock.sentinel"

# Span attribute keys not in the stable semconv yet (custom)
_SESSION_ID_KEY = "session.id"
_EVENT_ID_KEY = "genlock.event.id"
_NODE_NAME_KEY = "genlock.node.name"
_HITL_DECISION_KEY = "hitl.decision"
_CIRCUIT_BREAKER_KEY = "genlock.circuit_breaker.fired"
_STATE_FIELD_KEY = "genlock.state.field"
_STATE_REDUCER_KEY = "genlock.state.reducer"


def get_tracer() -> trace.Tracer:
    """Returns the module-level tracer. Safe to call before bootstrap (NoOp)."""
    return trace.get_tracer(_TRACER_NAME)


# ------------------------------------------------------------------------------
# Session Span  (one per shoot session, wraps the entire RUN_STARTED → RUN_FINISHED)
# ------------------------------------------------------------------------------

@contextmanager
def session_span(session_id: str) -> Generator[Span, None, None]:
    """Context manager that opens a root session span.

    Should be entered at RUN_STARTED and exited at session termination.
    The span is stored as a context var so nested node/tool spans attach under it.
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(
        "genlock.session",
        attributes={
            _SESSION_ID_KEY: session_id,
            GEN_AI_OPERATION_NAME: GenAiOperationNameValues.INVOKE_WORKFLOW.value,
            GEN_AI_PROVIDER_NAME: GenAiProviderNameValues.GCP_GEMINI.value,
            GEN_AI_WORKFLOW_NAME: "genlock_sentinel_7node",
        },
        kind=trace.SpanKind.SERVER,
    ) as span:
        yield span


# ------------------------------------------------------------------------------
# Event Span  (one per drift event, nested under session span)
# ------------------------------------------------------------------------------

@contextmanager
def event_span(
    session_id: str,
    event_id: str,
    node_id: str,
) -> Generator[Span, None, None]:
    """Context manager wrapping the full reasoning pass for one drift event."""
    tracer = get_tracer()
    with tracer.start_as_current_span(
        "genlock.event.invoke_agent",
        attributes={
            _SESSION_ID_KEY: session_id,
            _EVENT_ID_KEY: event_id,
            _NODE_NAME_KEY: node_id,
            GEN_AI_OPERATION_NAME: GenAiOperationNameValues.INVOKE_AGENT.value,
            GEN_AI_PROVIDER_NAME: GenAiProviderNameValues.GCP_GEMINI.value,
        },
        kind=trace.SpanKind.INTERNAL,
    ) as span:
        yield span


# ------------------------------------------------------------------------------
# Node Span  (one per ADK graph node execution)
# ------------------------------------------------------------------------------

@contextmanager
def node_span(
    node_name: str,
    model: Optional[str] = None,
    session_id: Optional[str] = None,
    event_id: Optional[str] = None,
) -> Generator[Span, None, None]:
    """Context manager wrapping a single ADK Workflow node execution.

    Args:
        node_name:  Human-readable node identifier (e.g. "evidence_triage").
        model:      Gemini model string if this is an LLM node (e.g. "gemini-3.7-flash").
        session_id: Optional — propagated as span attribute for correlation.
        event_id:   Optional — propagated as span attribute for correlation.
    """
    tracer = get_tracer()
    attrs: dict[str, Any] = {
        _NODE_NAME_KEY: node_name,
        GEN_AI_OPERATION_NAME: GenAiOperationNameValues.INVOKE_AGENT.value,
        GEN_AI_PROVIDER_NAME: GenAiProviderNameValues.GCP_GEMINI.value,
    }
    if model:
        attrs[GEN_AI_REQUEST_MODEL] = model
        attrs[GEN_AI_RESPONSE_MODEL] = model
    if session_id:
        attrs[_SESSION_ID_KEY] = session_id
    if event_id:
        attrs[_EVENT_ID_KEY] = event_id

    with tracer.start_as_current_span(
        f"genlock.node.{node_name}",
        attributes=attrs,
        kind=trace.SpanKind.INTERNAL,
    ) as span:
        yield span


# ------------------------------------------------------------------------------
# Tool Span  (one per MCP/internal tool call, nested under its node span)
# ------------------------------------------------------------------------------

@contextmanager
def tool_span(
    tool_name: str,
    session_id: Optional[str] = None,
    event_id: Optional[str] = None,
) -> Generator[Span, None, None]:
    """Context manager wrapping a single tool call (MCP query or remediation).

    Args:
        tool_name:  The name of the tool (e.g. "query_loki_logs").
        session_id: Optional correlation attribute.
        event_id:   Optional correlation attribute.
    """
    tracer = get_tracer()
    attrs: dict[str, Any] = {
        GEN_AI_TOOL_NAME: tool_name,
        GEN_AI_OPERATION_NAME: GenAiOperationNameValues.EXECUTE_TOOL.value,
        GEN_AI_PROVIDER_NAME: GenAiProviderNameValues.GCP_GEMINI.value,
    }
    if session_id:
        attrs[_SESSION_ID_KEY] = session_id
    if event_id:
        attrs[_EVENT_ID_KEY] = event_id

    with tracer.start_as_current_span(
        f"genlock.tool.{tool_name}",
        attributes=attrs,
        kind=trace.SpanKind.CLIENT,
    ) as span:
        yield span


# ------------------------------------------------------------------------------
# Convenience helpers — record token usage and mark span status
# ------------------------------------------------------------------------------

def record_token_usage(
    span: Span,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """Attaches GenAI token usage attributes to an existing span."""
    if not isinstance(span, NonRecordingSpan):
        if input_tokens > 0:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, input_tokens)
        if output_tokens > 0:
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, output_tokens)


def mark_span_error(span: Span, error: Exception) -> None:
    """Records an exception on a span and sets its status to ERROR."""
    if not isinstance(span, NonRecordingSpan):
        span.record_exception(error)
        span.set_status(StatusCode.ERROR, str(error))


def mark_span_ok(span: Span, description: str = "") -> None:
    """Sets span status to OK."""
    if not isinstance(span, NonRecordingSpan):
        span.set_status(StatusCode.OK, description)


# ------------------------------------------------------------------------------
# HITL decision annotation on the current span
# ------------------------------------------------------------------------------

def annotate_hitl_decision(
    span: Span,
    decision: str,
    deny_reason: Optional[str] = None,
) -> None:
    """Records a HITL supervisor decision as a span attribute.

    Args:
        span:        The HITL Pause span to annotate.
        decision:    "approved" or "denied".
        deny_reason: Optional supervisor deny reason text.
    """
    if not isinstance(span, NonRecordingSpan):
        span.set_attribute(_HITL_DECISION_KEY, decision)
        if deny_reason:
            span.add_event(
                "hitl.deny_reason",
                {"deny_reason": deny_reason, _HITL_DECISION_KEY: decision},
            )


# ------------------------------------------------------------------------------
# Circuit breaker span annotation
# ------------------------------------------------------------------------------

def annotate_circuit_breaker(span: Span, node_id: str) -> None:
    """Marks the current span as a circuit-breaker-forced HITL escalation."""
    if not isinstance(span, NonRecordingSpan):
        span.set_attribute(_CIRCUIT_BREAKER_KEY, True)
        span.set_attribute(_NODE_NAME_KEY, node_id)
        span.add_event("genlock.circuit_breaker.fired", {"node_id": node_id})


# ------------------------------------------------------------------------------
# State-delta annotation
# ------------------------------------------------------------------------------

def annotate_state_delta(
    span: Span,
    field_name: str,
    reducer_type: str,
) -> None:
    """Tags a span with the state field mutated and its reducer semantics."""
    if not isinstance(span, NonRecordingSpan):
        span.add_event(
            "genlock.state_delta",
            {_STATE_FIELD_KEY: field_name, _STATE_REDUCER_KEY: reducer_type},
        )
