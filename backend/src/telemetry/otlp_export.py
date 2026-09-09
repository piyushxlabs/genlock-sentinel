"""Genlock Sentinel — Dual-Export OTLP TracerProvider Bootstrap.

Per INTERFACE_OBSERVABILITY_SYSTEM.md Section 6 (Chosen Tracing Backend):
  "Hybrid — instrument with OpenTelemetry GenAI Semantic Conventions throughout,
   exported to two destinations: Google Cloud Trace (native OTLP/gRPC endpoint) for
   operational tracing, and Langfuse via its OTLP endpoint for scoring and
   evaluation-dataset construction."

Export topology:
  Tracer Provider
    ├─ BatchSpanProcessor
    │    └─ OTLPSpanExporter (gRPC) → Google Cloud Trace
    │         endpoint: OTEL_GCP_TRACE_OTLP_ENDPOINT
    │         (default: https://telemetry.googleapis.com:4317)
    └─ BatchSpanProcessor
         └─ OTLPSpanExporter (HTTP/JSON) → Langfuse OTLP endpoint
              endpoint: OTEL_EXPORTER_OTLP_ENDPOINT
              auth:     Basic(LANGFUSE_PUBLIC_KEY:LANGFUSE_SECRET_KEY)

Graceful degradation:
  If either endpoint env var is missing, that exporter is silently skipped.
  If BOTH are missing, a NoOp provider is installed and telemetry is disabled —
  the agent continues without any tracing.

Call bootstrap_telemetry() once at process startup (lifespan).
Call shutdown_telemetry() once at process shutdown.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GrpcOTLPExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HttpOTLPExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)

# Singleton provider reference — held so shutdown() can be called cleanly
_provider: Optional[TracerProvider] = None


def _build_langfuse_auth_header() -> Optional[dict[str, str]]:
    """Constructs the HTTP Basic Auth header for the Langfuse OTLP endpoint.

    Returns None if credentials are not configured.
    """
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    if not public_key or not secret_key:
        return None
    token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def bootstrap_telemetry() -> None:
    """Initialises the global OTel TracerProvider with dual OTLP exporters.

    Must be called once at application startup, before any spans are created.
    Safe to call multiple times — subsequent calls are no-ops if already bootstrapped.
    """
    global _provider
    if _provider is not None:
        logger.debug("Telemetry already bootstrapped — skipping re-init.")
        return

    # Resource identifies the service in both Cloud Trace and Langfuse
    service_name = os.environ.get("OTEL_SERVICE_NAME", "genlock-sentinel")
    google_cloud_project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.1.0",
            "deployment.environment": os.environ.get("DEPLOYMENT_ENV", "development"),
            "google.cloud.project": google_cloud_project,
        }
    )

    provider = TracerProvider(resource=resource)
    exporters_registered = 0

    # ------------------------------------------------------------------
    # Exporter 1: Google Cloud Trace via native OTLP/gRPC
    # ------------------------------------------------------------------
    gcp_endpoint = os.environ.get(
        "OTEL_GCP_TRACE_OTLP_ENDPOINT",
        "https://telemetry.googleapis.com:4317",
    ).strip()
    if gcp_endpoint:
        try:
            gcp_exporter = GrpcOTLPExporter(endpoint=gcp_endpoint, insecure=False)
            provider.add_span_processor(BatchSpanProcessor(gcp_exporter))
            exporters_registered += 1
            logger.info("Telemetry: Google Cloud Trace OTLP/gRPC exporter registered → %s", gcp_endpoint)
        except Exception as exc:
            logger.warning("Telemetry: Failed to register GCP trace exporter: %s", exc)

    # ------------------------------------------------------------------
    # Exporter 2: Langfuse via OTLP/HTTP with Basic Auth
    # ------------------------------------------------------------------
    langfuse_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if langfuse_endpoint:
        auth_header = _build_langfuse_auth_header()
        if auth_header is None:
            logger.warning(
                "Telemetry: OTEL_EXPORTER_OTLP_ENDPOINT is set but LANGFUSE_PUBLIC_KEY/"
                "LANGFUSE_SECRET_KEY are missing — Langfuse exporter skipped."
            )
        else:
            try:
                # Langfuse OTLP endpoint expects the /v1/traces suffix
                traces_endpoint = (
                    langfuse_endpoint.rstrip("/") + "/v1/traces"
                    if not langfuse_endpoint.rstrip("/").endswith("/v1/traces")
                    else langfuse_endpoint
                )
                langfuse_exporter = HttpOTLPExporter(
                    endpoint=traces_endpoint,
                    headers=auth_header,
                )
                provider.add_span_processor(BatchSpanProcessor(langfuse_exporter))
                exporters_registered += 1
                logger.info("Telemetry: Langfuse OTLP/HTTP exporter registered → %s", traces_endpoint)
            except Exception as exc:
                logger.warning("Telemetry: Failed to register Langfuse exporter: %s", exc)

    # ------------------------------------------------------------------
    # Development console fallback: if no cloud exporters, log to stdout
    # ------------------------------------------------------------------
    if exporters_registered == 0:
        dev_mode = os.environ.get("OTEL_CONSOLE_EXPORT", "false").lower() == "true"
        if dev_mode:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.info("Telemetry: Console span exporter registered (OTEL_CONSOLE_EXPORT=true).")
        else:
            logger.warning(
                "Telemetry: No OTLP exporters configured. "
                "Set OTEL_EXPORTER_OTLP_ENDPOINT and/or OTEL_GCP_TRACE_OTLP_ENDPOINT. "
                "Spans will be silently discarded."
            )

    trace.set_tracer_provider(provider)
    _provider = provider
    logger.info("Telemetry: TracerProvider bootstrapped with %d exporter(s).", exporters_registered)


def shutdown_telemetry() -> None:
    """Flushes all pending spans and shuts down the TracerProvider.

    Must be called at application shutdown to avoid losing buffered spans.
    """
    global _provider
    if _provider is not None:
        try:
            _provider.shutdown()
            logger.info("Telemetry: TracerProvider shut down cleanly.")
        except Exception as exc:
            logger.error("Telemetry: Error during TracerProvider shutdown: %s", exc)
        finally:
            _provider = None


def is_telemetry_active() -> bool:
    """Returns True if a real (non-NoOp) TracerProvider is installed."""
    return _provider is not None
