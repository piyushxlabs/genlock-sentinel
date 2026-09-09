#!/usr/bin/env python3
"""Genlock Sentinel — Standalone Grafana Cloud Loki Telemetry Ingestion Script.

Pushes realistic In-Camera VFX (ICVFX) nDisplay genlock sync-drift logs directly
to the Grafana Cloud Loki ingestion gateway.

Usage:
    uv run python scripts/push_sample_loki_logs.py
    uv run python scripts/push_sample_loki_logs.py --node render-07 --cluster ndisplay
    uv run python scripts/push_sample_loki_logs.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

import dotenv
import httpx


def load_environment() -> None:
    """Loads backend/.env or root .env."""
    backend_dir = Path(__file__).resolve().parent.parent
    env_file = backend_dir / ".env"
    if env_file.exists():
        dotenv.load_dotenv(dotenv_path=env_file)
    else:
        dotenv.load_dotenv()


def build_sample_logs(node: str) -> List[str]:
    """Returns 10 distinct, highly realistic ICVFX genlock operational logs."""
    return [
        f"[CRITICAL] PTP Hardware Clock skew detected on {node}: offset +162.8µs exceeds 150µs SLA",
        f"[ERROR] nDisplay sync barrier timeout on frame f-77192 after 310ms (nominal: 16.6ms) on {node}",
        f"[WARN] GPU junction temperature reached 94C on RTX 6000 Ada on {node}; driver initiating thermal throttle",
        f"[ERROR] SMPTE ST 2110-21 buffer underrun detected on NIC mellanox_cx6 on {node} (packet loss: 14.2%)",
        f"[WARN] Ray-tracing shader pipeline stall in virtual volume viewport primary camera frustum on {node}",
        f"[INFO] Genlock Sentinel ADK supervisor dispatched anomaly alert for {node} to MCP telemetry bus",
        f"[CRITICAL] nDisplay swap interval lock broken across cluster boundary ({node} decoupled)",
        f"[WARN] Texture streaming pool budget exhausted (allocated: 24.8GB / limit: 24.0GB) on {node}",
        f"[INFO] PTP slave clock resynchronization initiated for {node} against Stratum-1 grandmaster",
        f"[INFO] Stage tracking sync signal reacquired for {node}; frame genlock phase offset stabilized at 38.2µs",
    ]


def build_loki_payload(
    lines: List[str],
    cluster: str,
    node: str,
    job: str,
    env: str,
) -> dict:
    """Builds a Loki Push API JSON payload with strictly ascending nanosecond timestamps."""
    now_ns = time.time_ns()
    # Stagger timestamps across the last 2 minutes in strictly ascending order
    # (Loki requires non-decreasing timestamps within a single stream)
    step_ns = 12 * 1_000_000_000  # 12 seconds per line
    start_ns = now_ns - (len(lines) * step_ns)

    values: List[Tuple[str, str]] = []
    for i, line in enumerate(lines):
        ts = str(start_ns + (i * step_ns))
        values.append((ts, line))

    return {
        "streams": [
            {
                "stream": {
                    "cluster": cluster,
                    "node": node,
                    "job": job,
                    "env": env,
                },
                "values": values,
            }
        ]
    }


def main() -> int:
    load_environment()

    parser = argparse.ArgumentParser(description="Push realistic ICVFX genlock logs to Grafana Cloud Loki")
    parser.add_argument("--node", default="render-03", help="Target cluster render node (default: render-03)")
    parser.add_argument("--cluster", default="ndisplay", help="Cluster label (default: ndisplay)")
    parser.add_argument("--job", default="icvfx-telemetry", help="Job label (default: icvfx-telemetry)")
    parser.add_argument("--env", default="production-stage-01", help="Environment label (default: production-stage-01)")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without sending to Loki")
    args = parser.parse_args()

    loki_url = os.environ.get("GRAFANA_LOKI_URL", "https://logs-prod-028.grafana.net/loki/api/v1/push")
    if not loki_url.endswith("/loki/api/v1/push"):
        loki_url = loki_url.rstrip("/") + "/loki/api/v1/push"

    loki_user = os.environ.get("GRAFANA_LOKI_USER", "1780259")
    loki_token = (
        os.environ.get("GRAFANA_API_KEY")
        or os.environ.get("GRAFANA_CLOUD_TOKEN")
        or os.environ.get("GRAFANA_SERVICE_ACCOUNT_TOKEN")
    )

    log_lines = build_sample_logs(args.node)
    payload = build_loki_payload(
        lines=log_lines,
        cluster=args.cluster,
        node=args.node,
        job=args.job,
        env=args.env,
    )

    print("=" * 70)
    print("GENLOCK SENTINEL - GRAFANA CLOUD LOKI TELEMETRY INGESTION")
    print("=" * 70)
    print(f"Target Gateway : {loki_url}")
    print(f"Loki User ID   : {loki_user}")
    print(f"Stream Labels  : cluster={args.cluster}, node={args.node}, job={args.job}, env={args.env}")
    print(f"Total Lines    : {len(log_lines)}")
    print("-" * 70)

    if args.dry_run:
        print("[DRY RUN] Generated Loki Payload:")
        print(json.dumps(payload, indent=2))
        return 0

    if not loki_token:
        print("\n[ERROR] Missing Grafana Loki credentials in backend/.env.")
        print("Please configure:")
        print("  GRAFANA_LOKI_URL=https://logs-prod-028.grafana.net/loki/api/v1/push")
        print("  GRAFANA_LOKI_USER=1780259")
        print("  GRAFANA_API_KEY=<Grafana Cloud Access Policy Token with 'logs:write'>")
        print("\nGenerate your token at: https://grafana.com/orgs/magentaparfait3455")
        return 1

    print("[PUSHING] Sending stream payload to Grafana Cloud Loki...")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                loki_url,
                json=payload,
                auth=(loki_user, loki_token),
                headers={"Content-Type": "application/json"},
            )

        if resp.status_code == 204:
            print("\n" + "=" * 70)
            print("[SUCCESS] HTTP 204 No Content - Ingestion Accepted by Grafana Cloud Loki!")
            print("=" * 70)
            print(f"Ingested {len(log_lines)} realistic ICVFX drift logs into Grafana Cloud.")
            print("\nTo explore in Grafana Cloud:")
            print("  1. Open: https://magentaparfait3455.grafana.net/explore")
            print("  2. Select Datasource: grafanacloud-magentaparfait3455-logs")
            print(f"  3. LogQL Query: {{cluster=\"{args.cluster}\"}}")
            print(f"     or:          {{cluster=\"{args.cluster}\", node=\"{args.node}\"}}")
            print("=" * 70)
            return 0

        elif resp.status_code in (401, 403):
            print(f"\n[AUTH FAILURE] HTTP {resp.status_code} - Unauthorized.")
            print(f"Loki Gateway Error: {resp.text}")
            print("\nResolution Instructions:")
            print("  1. Visit: https://grafana.com/orgs/magentaparfait3455")
            print("  2. Navigate to 'Security' -> 'Access Policies'")
            print("  3. Create an Access Policy with 'logs:write' scope for Loki.")
            print("  4. Generate a Token and set it in backend/.env:")
            print("     GRAFANA_API_KEY=glc_...")
            return 2

        else:
            print(f"\n[LOKI ERROR] HTTP {resp.status_code}")
            print(f"Response: {resp.text}")
            return 3

    except httpx.RequestError as exc:
        print(f"\n[NETWORK ERROR] Could not connect to Loki gateway at {loki_url}: {exc}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
