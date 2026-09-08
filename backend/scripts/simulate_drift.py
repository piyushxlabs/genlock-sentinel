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
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
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


async def emit_drift_event(
    payload: DriftTelemetryPayload, destination_url: Optional[str] = None
) -> None:
    """Emits or prints a synthetic drift event without blocking I/O."""
    output = payload.model_dump_json(indent=2)
    sys.stdout.write(f"\n[DRIFT EMITTED] Event: {payload.event_id} | Node: {payload.node_id}\n")
    sys.stdout.write(f"Timestamp: {payload.breach_ts} | Sync Offset: {payload.sync_offset_us} µs\n")
    sys.stdout.write(f"Category: {payload.category_hint}\n")
    sys.stdout.write(f"Loki Evidence Lines: {len(payload.mock_loki_lines)}\n")
    sys.stdout.write(f"Tempo Evidence Spans: {len(payload.mock_tempo_spans)}\n")
    sys.stdout.write("--- Payload JSON ---\n")
    sys.stdout.write(f"{output}\n")
    sys.stdout.flush()

    if destination_url:
        import httpx

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    destination_url,
                    json=payload.model_dump(),
                    timeout=5.0,
                )
                sys.stdout.write(f"Forwarded to {destination_url} -> Status {resp.status_code}\n")
            except Exception as e:
                sys.stderr.write(f"Failed to push to {destination_url}: {e}\n")


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
        await emit_drift_event(payload, destination_url=destination_url)
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
        help="Optional HTTP endpoint to POST drift event JSON to",
    )

    args = parser.parse_args()

    if args.scenario == "stream":
        asyncio.run(run_stream(args.interval, args.count, args.url))
    else:
        payload = SCENARIOS[args.scenario]
        asyncio.run(emit_drift_event(payload, args.url))


if __name__ == "__main__":
    main()
