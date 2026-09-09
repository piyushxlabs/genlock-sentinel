#!/usr/bin/env python3
"""Genlock Sentinel — CLI Session Reset Utility.

Resets an active ICVFX stage sentinel session to a pristine baseline state:
  - Clears all active drift events, evidence bundles, and pending HITL cards.
  - Sets session status to MONITORING with 16 nominal locked nodes.
  - Broadcasts a STATE_SNAPSHOT and baseline telemetry sample over the AG-UI SSE stream.

Usage:
    uv run python scripts/reset_session.py --session sentinel-icvfx-stage-01
"""

import argparse
import sys
import httpx


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset a Genlock Sentinel session to pristine baseline."
    )
    parser.add_argument(
        "--session",
        default="sentinel-icvfx-stage-01",
        help="Target session ID to reset (default: sentinel-icvfx-stage-01)",
    )
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Backend host URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    session_id = args.session
    url = f"{args.host.rstrip('/')}/sessions/{session_id}/reset"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                json={
                    "reason": "CLI script reset to pristine baseline.",
                    "supervisor_id": "cli_operator",
                },
            )
            if resp.status_code == 200:
                print(
                    f"[SUCCESS] Session '{session_id}' reset to pristine baseline (16 green nodes, 0.00 USD burn)."
                )
                sys.exit(0)
            else:
                print(f"[ERROR] Reset failed (HTTP {resp.status_code}): {resp.text}")
                sys.exit(1)
    except httpx.ConnectError:
        print(f"[ERROR] Could not connect to backend server at {args.host}. Is uvicorn running?")
        sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] Unexpected failure during reset: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
