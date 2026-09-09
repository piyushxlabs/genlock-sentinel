━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 20 COMPLETION CHECKLIST
# Live Telemetry Drift Ingestion & End-to-End Verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify full test suite passes with 193 automated tests
    ```
    cd "a:\Projects\GENLOCK SENTINEL\backend"
    uv run pytest tests/ -v
    ```
    Expected: 193 passed in ~2.5s (or ~140s if running full telemetry exporter tests)

[ ] Verify drift injection unit test suite passes independently
    ```
    cd "a:\Projects\GENLOCK SENTINEL\backend"
    uv run pytest tests/unit/test_drift_injection.py -v
    ```
    Expected: 5 passed in ~3s

[ ] Verify backend FastAPI server is running on port 8000
    ```
    curl http://127.0.0.1:8000/health
    ```
    Expected: {"status":"healthy","app_name":"genlock_sentinel","streaming_mode":"SSE",...}

[ ] Verify frontend Vite dev server is running on port 3000
    ```
    curl http://localhost:3000
    ```
    Expected: HTTP 200 with HTML shell

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Run live complex drift simulation to trigger the HITL Approval Modal on localhost:3000
    ```
    cd "a:\Projects\GENLOCK SENTINEL\backend"
    uv run python scripts/simulate_drift.py --scenario complex
    ```
    Expected:
    [DRIFT EMITTED] Event: drift-evt-complex-... | Node: render-12
    [HTTP DISPATCH] Successfully forwarded to http://127.0.0.1:8000/sessions/sentinel-icvfx-stage-01/inject-drift -> Status 202
    If wrong: Check uvicorn process running on port 8000 via `uv run uvicorn src.main:app --port 8000`

[ ] Observe live operations console on http://localhost:3000
    Expected:
    1. Real-time sync-offset chart spikes to 210.0 µs exceeding 150 µs red dotted line.
    2. Step Tracker highlights: stream_watch -> evidence_triage -> root_cause_correlation -> hitl_card_generation -> hitl_pause.
    3. Gemini reasoning tokens stream into the Diagnosis reasoning panel.
    4. Blocking HITL Approval Modal pops up with:
       - Proposed Action: 'none' (or 'halt_live_take')
       - Escalation Reason: 'ambiguous_diagnosis'
       - Cost Delta: '$0 (diagnostic pause)'
       - Visual Impact: 'Moderate (sync jitter visible in camera pan)'
       - Buttons: 'Approve' and 'Deny'
    5. Stage burn counter accrues at $1,800/min.

[ ] Test supervisor decision resolution in the modal:
    Click 'Approve' or 'Deny' in the modal on http://localhost:3000
    Expected: Modal dismisses, session status returns to 'MONITORING', audit record appended to Remediation Log.

[ ] Run live simple drift simulation to observe autonomous remediation:
    ```
    cd "a:\Projects\GENLOCK SENTINEL\backend"
    uv run python scripts/simulate_drift.py --scenario simple
    ```
    Expected:
    1. Sync-offset chart spikes to 185.4 µs.
    2. Step Tracker animates through autonomous_dispatch.
    3. Action 'failover_cluster_leadership' logged to Remediation Log without human approval.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/src/main.py` — Ingestion endpoint `POST /sessions/{session_id}/inject-drift` with `InjectDriftRequest`/`InjectDriftResponse` strict Pydantic V2 schemas, `merge-by-key` state reducer, real-time `SYNC_OFFSET_SAMPLE` emission, and background `_execute_drift_reasoning` trigger.
[ ] File: `backend/src/agents/reasoning_loop.py` — Full `AGUIEventBridge` real-time broadcasting instrumentation emitting `STEP_STARTED`, `TOOL_CALL_*`, `REASONING_*` streaming tokens, RFC 6902 `STATE_DELTA`, and `RUN_PAUSED`.
[ ] File: `backend/scripts/simulate_drift.py` — Auto-dispatching drift simulator defaulting to active console session (`sentinel-icvfx-stage-01`), `http://127.0.0.1:8000/sessions/{session_id}/inject-drift`, fresh event ID generation, and non-blocking `httpx` execution.
[ ] File: `backend/tests/unit/test_drift_injection.py` — 5 unit tests verifying injection schema validation, 202 response, state mutations, and AG-UI event broadcasting.
[ ] File: `backend/src/agents/evidence_triage.py` — Dynamic mock key resolution and event ID indexing.
[ ] File: `backend/src/agents/root_cause_correlation.py` — Dynamic mock key resolution and target node ID scoping.
[ ] File: `backend/src/agents/model_config.py` — Added `evidence_bundle_complex` fixture.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
dir /b "a:\Projects\GENLOCK SENTINEL\backend\tests\unit\test_drift_injection.py"
```
✅ Expected: test_drift_injection.py

Test 2 — Dependencies & Environment:
```
cd "a:\Projects\GENLOCK SENTINEL\backend"
uv run python --version
```
✅ Expected: Python 3.11.x

Test 3 — Drift Injection Unit Test Suite:
```
cd "a:\Projects\GENLOCK SENTINEL\backend"
uv run pytest tests/unit/test_drift_injection.py -v
```
✅ Expected: 5 passed, 0 failed

Test 4 — Full Test Suite Across All Layers:
```
cd "a:\Projects\GENLOCK SENTINEL\backend"
uv run pytest tests/ -q
```
✅ Expected: 193 passed

Test 5 — Frontend Build Check:
```
cd "a:\Projects\GENLOCK SENTINEL\frontend"
pnpm build
```
✅ Expected: 1868 modules transformed, 0 errors

Test 6 — Security Check:
[ ] Verify .env is in .gitignore
    ```
    type "a:\Projects\GENLOCK SENTINEL\.gitignore" | findstr ".env"
    ```
    ✅ Expected: .env appears in the output

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step 20: Live Telemetry Drift Ingestion & Real-Time Event Dispatch — Ingestion endpoint, simulate_drift wireup, and AG-UI streaming"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 21 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
