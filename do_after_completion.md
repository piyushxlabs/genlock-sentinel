━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 25 COMPLETION CHECKLIST
# Drift Injection Concurrency & Mock Evidence Ingestion Verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify backend server is running and responsive:
    ```
    powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8000/healthz' -TimeoutSec 5 | Select-Object -ExpandProperty Content"
    ```
    Expected: {"status":"healthy"}

[ ] Verify frontend console is running and responsive:
    ```
    powershell -Command "Invoke-WebRequest -Uri 'http://localhost:3000' -TimeoutSec 5 | Select-Object -ExpandProperty StatusCode"
    ```
    Expected: 200

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Run injected telemetry unit test suite:
    ```
    cd backend
    uv run pytest tests/unit/test_injected_telemetry.py -v
    ```
    Expected: 7 passed in ~1s
    If wrong: Check `backend/src/tools/mcp_clients/grafana_mcp_client.py` and `simulate_drift.py`.

[ ] Run full backend unit test suite:
    ```
    cd backend
    uv run pytest tests/unit/ -q
    ```
    Expected: 154 passed, 1 skipped in ~6s
    If wrong: Check test output and ensure mock telemetry cache was properly cleared between tests.

[ ] Run production readiness and failure simulation suite:
    ```
    cd backend
    uv run pytest tests/evals/test_production_readiness.py -v
    ```
    Expected: 14 passed in ~3s

[ ] Run frontend production build check:
    ```
    cd frontend
    pnpm build
    ```
    Expected: Zero errors — `tsc && vite build` — 1868 modules transformed in ~2s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/scripts/simulate_drift.py` — Added `check_backend_ready()` probing `GET /healthz` and `GET /docs`; 3-attempt backoff retry loop with fail-fast `sys.exit(1)` on connection failure to prevent orphaned events without Loki/Tempo payloads; standardized URL to `http://localhost:8000`; 120s timeout.
[ ] File: `backend/src/tools/mcp_clients/grafana_mcp_client.py` — In-memory cached mock telemetry storage (`_injected_loki`, `_injected_tempo_spans`), `register_injected_telemetry()`, and Model Armor prompt-injection screening on all retrieved lines and spans.
[ ] File: `backend/src/tools/evidence_triage_tools.py` — Forwarded `node_id` in `query_loki_logs` to route queries to node-specific injected telemetry caches.
[ ] File: `backend/src/main.py` — Registered incoming `mock_loki_lines` and `mock_tempo_spans` in `/sessions/{session_id}/inject-drift` via `get_mcp_client().register_injected_telemetry()`.
[ ] File: `backend/src/state/checkpointing.py` — Cached `DatabaseSessionService` singleton and `_tables_prepared` tracking flag; added 3-attempt reload-and-retry loop on `StaleSessionError` in `save_checkpoint`.
[ ] File: `backend/tests/unit/test_injected_telemetry.py` — 7 comprehensive unit tests for injected telemetry caching, Model Armor screening, edge scenario gap handling, readiness probe, and connection failure fast-fail behavior.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Test-Path backend\tests\unit\test_injected_telemetry.py, backend\scripts\simulate_drift.py, backend\src\tools\mcp_clients\grafana_mcp_client.py"
```
✅ Expected: True, True, True
❌ If missing: Restore from git history.

Test 2 — Environment / Dependencies:
```
cd backend
uv run python -c "import httpx, pydantic, google.genai, asyncpg; print('All critical packages imported successfully')"
```
✅ Expected: All critical packages imported successfully
❌ If errors: Run `uv sync` in `backend/`

Test 3 — Server or Process Start:
```
powershell -Command "Invoke-RestMethod -Uri 'http://localhost:8000/healthz' -Method Get"
```
✅ Expected: @{status=healthy}
❌ If errors: Check if uvicorn process is running (`uv run uvicorn src.main:app --host 0.0.0.0 --port 8000`)

Test 4 — Functional Check (Simulated Drift Injection with Evidence):
```
cd backend
uv run python scripts/simulate_drift.py --scenario simple --event-id drift-test-check-001
```
✅ Expected: 
- Probes backend readiness: [SUCCESS]
- Dispatches HTTP POST to http://localhost:8000/sessions/session-sim-001/inject-drift
- Returns HTTP 202 Accepted
- Node 2 triage extracts `logs_available: True` and populated log/trace summaries without falling back to telemetry gaps.
❌ If wrong: Ensure backend is running and `simulate_drift.py` has network access to port 8000.

Test 5 — Security Check:
[ ] Verify .env is in .gitignore
    ```
    git check-ignore backend/.env
    ```
    ✅ Expected: backend/.env appears in the output
    ❌ If missing: Add `.env` to .gitignore immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step 25: Drift Injection Concurrency & Mock Evidence Ingestion Verification"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 26 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
