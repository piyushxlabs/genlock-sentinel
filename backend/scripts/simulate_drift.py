"""Genlock Sentinel — Synthetic Drift Event Simulator.

Simulates ICVFX nDisplay sync-offset telemetry breaches, generating synthetic
Prometheus metric points, Loki log streams, and Tempo trace payloads
aligned with AGENT_MASTER_PLAN.md Section 9.1 and AGENT_LOGIC_SPEC.md.

Usage:
    python simulate_drift.py --scenario simple
    python simulate_drift.py --scenario complex
    python simulate_drift.py --scenario edge
    python simulate_drift.py --scenario stream --interval 1.0 --count 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field


class DriftTelemetryPayload(BaseModel):
    """Pydantic V2 model for synthetic ICVFX cluster drift events."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(..., description="Unique drift event identifier")
    node_id: str = Field(..., description="Target cluster render node (e.g. render-07)")
    frame_id: str = Field(..., description="Active camera frame ID (e.g. f-88213)")
    breach_ts: str = Field(..., description="ISO 8601 UTC timestamp of threshold breach")
    sync_offset_us: float = Field(..., description="Sync offset in microseconds")
    threshold_us: float = Field(default=150.0, description="Breach threshold in microseconds")
    category_hint: Literal[
        "network_jitter",
        "asset_streaming_stall",
        "thermal_throttle",
        "ambiguous",
    ] = Field(..., description="Target mock diagnosis category")
    mock_loki_lines: List[str] = Field(default_factory=list, description="Associated Loki log lines")
    mock_tempo_spans: List[Dict[str, Any]] = Field(
        default_factory=list, description="Associated Tempo trace spans"
    )


SCENARIOS: Dict[str, DriftTelemetryPayload] = {
    "simple": DriftTelemetryPayload(
        event_id="drift-evt-simple-001",
        node_id="render-07",
        frame_id="f-88213",
        breach_ts="2026-09-07T14:02:11Z",
        sync_offset_us=185.4,
        threshold_us=150.0,
        category_hint="network_jitter",
        mock_loki_lines=[
            "14:02:10 [cluster-manager] sync handshake retry node=render-07",
            "14:02:11 [LogDisplayClusterEngine] frame drop detected on render-07 (offset: 185.4us)",
        ],
        mock_tempo_spans=[
            {
                "service": "render-07",
                "span_name": "cluster_sync_handshake",
                "duration_ms": 340,
                "status": "warning",
                "attributes": {"sync_jitter_us": 185.4},
            }
        ],
    ),
    "complex": DriftTelemetryPayload(
        event_id="drift-evt-complex-002",
        node_id="render-12",
        frame_id="f-91004",
        breach_ts="2026-09-07T15:10:03Z",
        sync_offset_us=210.0,
        threshold_us=150.0,
        category_hint="ambiguous",
        mock_loki_lines=[
            "15:10:01 [LogDisplayClusterEngine] GPU throttling detected; junction temp 94C",
            "15:10:02 [cluster-manager] heartbeat delayed 82ms from render-12",
        ],
        mock_tempo_spans=[
            {
                "service": "render-12",
                "span_name": "frame_render",
                "duration_ms": 420,
                "status": "error",
                "attributes": {"thermal_state": "critical", "packet_loss_pct": 14.2},
            }
        ],
    ),
    "edge": DriftTelemetryPayload(
        event_id="drift-evt-edge-003",
        node_id="render-03",
        frame_id="f-77192",
        breach_ts="2026-09-07T16:45:22Z",
        sync_offset_us=162.8,
        threshold_us=150.0,
        category_hint="ambiguous",
        mock_loki_lines=[],  # Simulates Loki timeout / logs_available: false
        mock_tempo_spans=[
            {
                "service": "render-03",
                "span_name": "frame_render",
                "duration_ms": 310,
                "status": "ok",
            }
        ],
    ),
}


async def check_backend_ready(base_url: str, retries: int = 3, backoff_sec: float = 1.0) -> bool:
    """Checks backend readiness before emitting or dispatching drift events.

    Probes GET {base_url}/healthz or GET {base_url}/docs with exponential retries.
    Returns True if healthy, False if unreachable.
    """
    import httpx

    endpoints = [f"{base_url.rstrip('/')}/healthz", f"{base_url.rstrip('/')}/docs"]
    for attempt in range(1, retries + 1):
        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(endpoint)
                    if resp.status_code in (200, 307):
                        sys.stdout.write(f"[READINESS] Backend probe succeeded: {endpoint} -> HTTP {resp.status_code}\n")
                        sys.stdout.flush()
                        return True
            except (httpx.ConnectError, httpx.TimeoutException, ConnectionError):
                pass
            except Exception:
                pass

        if attempt < retries:
            sys.stderr.write(
                f"[READINESS RETRY] Backend not ready at {base_url} (attempt {attempt}/{retries}). Retrying in {backoff_sec}s...\n"
            )
            await asyncio.sleep(backoff_sec)

    sys.stderr.write(
        f"\n[FATAL] Backend readiness probe failed at {base_url} after {retries} attempts.\n"
        f"FastAPI server is not reachable. Aborting drift injection to prevent orphaned telemetry-less events.\n"
        f"Start backend first: uv run uvicorn src.main:app --port 8000\n"
    )
    return False


async def emit_drift_event(
    payload: DriftTelemetryPayload,
    destination_url: Optional[str] = None,
    retries: int = 3,
    backoff_sec: float = 1.0,
) -> bool:
    """Emits or prints a synthetic drift event with retry mechanism.

    Returns True if emitted (and dispatched successfully if URL provided), False otherwise.
    """
    output = payload.model_dump_json(indent=2)
    sys.stdout.write(f"\n[DRIFT EMITTED] Event: {payload.event_id} | Node: {payload.node_id}\n")
    sys.stdout.write(f"Timestamp: {payload.breach_ts} | Sync Offset: {payload.sync_offset_us} µs\n")
    sys.stdout.write(f"Category: {payload.category_hint}\n")
    sys.stdout.write(f"Loki Evidence Lines: {len(payload.mock_loki_lines)}\n")
    sys.stdout.write(f"Tempo Evidence Spans: {len(payload.mock_tempo_spans)}\n")
    sys.stdout.write("--- Payload JSON ---\n")
    sys.stdout.write(f"{output}\n")
    sys.stdout.flush()

    if not destination_url:
        return True

    import httpx

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    destination_url,
                    json=payload.model_dump(),
                    timeout=120.0,
                )
                sys.stdout.write(
                    f"\n[HTTP DISPATCH] Successfully forwarded to {destination_url} -> Status {resp.status_code}\n"
                )
                if resp.status_code >= 400:
                    sys.stderr.write(f"[HTTP ERROR] Server responded with error: {resp.text}\n")
                    return False
                return True
        except (httpx.ConnectError, ConnectionError) as conn_err:
            sys.stderr.write(
                f"[DISPATCH ATTEMPT {attempt}/{retries}] Connection failed to {destination_url}: {conn_err}\n"
            )
            if attempt < retries:
                await asyncio.sleep(backoff_sec)
        except Exception as e:
            sys.stderr.write(
                f"\n[HTTP DISPATCH FAILED] Unexpected error reaching runtime at {destination_url}: {e}\n"
            )
            return False

    sys.stderr.write(
        f"\n[HTTP DISPATCH FAILED] Could not connect to runtime at {destination_url} after {retries} retries.\n"
        f"Failing fast without persisting event to database to prevent orphaned events without Loki/Tempo payloads.\n"
    )
    return False


async def run_stream(interval_sec: float, count: int, destination_url: Optional[str] = None) -> None:
    """Emits a continuous series of drift events over a configured interval."""
    nodes = ["render-01", "render-07", "render-12", "render-15"]
    for i in range(1, count + 1):
        node = nodes[i % len(nodes)]
        offset = 150.0 + (i * 7.5)
        now_utc = datetime.now(timezone.utc).isoformat()
        payload = DriftTelemetryPayload(
            event_id=f"drift-stream-{i:04d}",
            node_id=node,
            frame_id=f"f-{80000 + i}",
            breach_ts=now_utc,
            sync_offset_us=round(offset, 2),
            threshold_us=150.0,
            category_hint="network_jitter" if i % 2 == 0 else "ambiguous",
            mock_loki_lines=[f"{now_utc} [LogDisplayClusterEngine] sync drift offset={offset:.2f}us on {node}"],
            mock_tempo_spans=[
                {
                    "service": node,
                    "span_name": "display_cluster_barrier",
                    "duration_ms": int(offset),
                    "status": "warning",
                }
            ],
        )
        ok = await emit_drift_event(payload, destination_url=destination_url)
        if not ok:
            sys.stderr.write(f"[STREAM ABORTED] Stopping stream due to dispatch failure on event {payload.event_id}\n")
            sys.exit(1)
        if i < count:
            await asyncio.sleep(interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genlock Sentinel — Synthetic Drift Event Simulator"
    )
    parser.add_argument(
        "--scenario",
        choices=["simple", "complex", "edge", "stream"],
        default="simple",
        help="Predefined test scenario from AGENT_MASTER_PLAN.md Section 9.1",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default="sentinel-icvfx-stage-01",
        help="Target active session ID (defaults to sentinel-icvfx-stage-01 matching console)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Interval between events in streaming mode (seconds)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of events to emit in streaming mode",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Optional HTTP endpoint override to POST drift event JSON to",
    )
    parser.add_argument(
        "--no-dispatch",
        action="store_true",
        default=False,
        help="Print JSON to stdout only without HTTP dispatch to runtime",
    )
    parser.add_argument(
        "--static-id",
        action="store_true",
        default=False,
        help="Use exact static event_id from scenario without timestamp suffix",
    )

    args = parser.parse_args()

    # Resolve target URL (defaults to active local runtime session endpoint at http://localhost:8000)
    default_base = os.environ.get("SENTINEL_BACKEND_URL", "http://localhost:8000").rstrip("/")
    if args.no_dispatch:
        dest_url = None
        base_url = None
    else:
        dest_url = args.url or f"{default_base}/sessions/{args.session_id}/inject-drift"
        parsed = urlparse(dest_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Check backend readiness before attempting injection
    if dest_url and base_url:
        ready = asyncio.run(check_backend_ready(base_url, retries=3, backoff_sec=1.0))
        if not ready:
            sys.exit(1)

    if args.scenario == "stream":
        asyncio.run(run_stream(args.interval, args.count, dest_url))
    else:
        base_payload = SCENARIOS[args.scenario]
        if not args.static_id:
            suffix = int(datetime.now(timezone.utc).timestamp()) % 100000
            fresh_event_id = f"{base_payload.event_id}-{suffix}"
            payload = DriftTelemetryPayload(
                event_id=fresh_event_id,
                node_id=base_payload.node_id,
                frame_id=base_payload.frame_id,
                breach_ts=datetime.now(timezone.utc).isoformat(),
                sync_offset_us=base_payload.sync_offset_us,
                threshold_us=base_payload.threshold_us,
                category_hint=base_payload.category_hint,
                mock_loki_lines=base_payload.mock_loki_lines,
                mock_tempo_spans=base_payload.mock_tempo_spans,
            )
        else:
            payload = base_payload

        success = asyncio.run(emit_drift_event(payload, dest_url))
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
