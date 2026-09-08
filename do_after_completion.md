━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 14 COMPLETION CHECKLIST
# Build Backend API/Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify that the FastAPI main application exists and has the endpoints:
    ```powershell
    Get-Content "backend\src\main.py" | Select-String "submit_decision", "stop_session", "healthz"
    ```
    Expected: Matches for `submit_decision`, `stop_session`, and `healthz` appear in the output.

[ ] Verify that the API test suite exists:
    ```powershell
    Test-Path "backend\tests\unit\test_api_server.py"
    ```
    Expected: `True`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Run the FastAPI API unit test suite:
    ```powershell
    cd backend
    uv run pytest tests/unit/test_api_server.py -v
    ```
    Expected: All 11 tests pass with 100% pass rate in < 5 seconds.
    If wrong: Ensure `backend/.venv` is active and dependencies are synced via `uv sync`.

[ ] Run the full unit test suite across all project components:
    ```powershell
    uv run pytest tests/unit/ -v
    ```
    Expected: All 83 unit tests pass across runner bootstrap, model configuration, state schema, reducers, checkpointing, tools, 7-node orchestration graph, reasoning loop, safety guardrails, and API server.
    If wrong: Check `tests/unit/test_api_server.py` or database checkpointing paths.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] Endpoint: `GET /health` and `GET /healthz` — Readiness endpoints returning `HealthResponse` with `streaming_mode="SSE"`.
[ ] Endpoint: `GET /` — Root metadata endpoint returning service identification and status.
[ ] Endpoint: `POST /sessions/{session_id}/events/{event_id}/decision` — Supervisor graph-resumption endpoint accepting strict `DecisionRequest` payload ("approve" or "deny"), enforcing checkpoint ID verification, rejecting modified inputs, updating state, recording audit logs, and persisting to checkpoint storage.
[ ] Endpoint: `POST /sessions/{session_id}/stop` — Supervisor emergency stop endpoint accepting `StopSessionRequest`, halting active session, transitioning status to "stopped", and checkpointing state as-is.
[ ] Models: `DecisionRequest`, `DecisionResponse`, `StopSessionRequest`, `StopSessionResponse`, `HealthResponse` with strict Pydantic V2 schema validation (`extra="forbid"`).
[ ] File: `backend/src/main.py` — Updated FastAPI application with full operations endpoints and checkpoint persistence.
[ ] File: `backend/tests/unit/test_api_server.py` — 11-test comprehensive unit and integration suite.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```powershell
Test-Path "backend\src\main.py", "backend\tests\unit\test_api_server.py"
```
✅ Expected: `True`, `True`
❌ If missing: Re-generate missing files from Step 14.

Test 2 — Environment / Dependencies:
```powershell
cd backend
uv run python -c "from src.main import app; print('FastAPI app loaded successfully')"
```
✅ Expected: `FastAPI app loaded successfully`
❌ If errors: Run `uv sync` in `backend/`.

Test 3 — API Server Test Suite:
```powershell
uv run pytest tests/unit/test_api_server.py -v
```
✅ Expected: 11 passed in < 5 seconds.
❌ If errors: Verify endpoint route parameters and Pydantic schemas in `backend/src/main.py`.

Test 4 — Full Test Suite Regression:
```powershell
uv run pytest tests/unit/ -v
```
✅ Expected: 83 passed, 0 failed across all 11 test modules.
❌ If errors: Check individual test failure logs.

Test 5 — Security Check:
[ ] Verify .env is in .gitignore
    ```powershell
    git check-ignore -v backend/.env
    ```
    ✅ Expected: `.gitignore:3:*.env	backend/.env`
    ❌ If missing: Add `*.env` to `.gitignore` immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```powershell
git add .
git commit -m "Step 14: Build Backend API/Server — FastAPI decision, stop, and health endpoints with checkpoint persistence"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 15 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
