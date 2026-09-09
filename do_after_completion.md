━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 15 COMPLETION CHECKLIST
# Implement Typed Streaming Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify the backend virtual environment is active:
    ```
    cd backend
    uv run python --version
    ```
    Expected: Python 3.11.x appears

[ ] Ensure git status is clean of untracked temporary files:
    ```
    git status
    ```
    Expected: Only tracked changes ready to commit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Run the typed streaming layer test suite:
    ```
    cd backend
    uv run pytest tests/unit/test_streaming_layer.py -v
    ```
    Expected: 19 passed in ~2 seconds
    If wrong: Check event model schemas in `src/ui/event_types.py` or bridge logic in `src/ui/agui_bridge.py`.

[ ] Run the full backend test suite to verify zero regressions:
    ```
    cd backend
    uv run pytest tests/unit/ -v
    ```
    Expected: 102 passed with 100% success rate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/src/ui/event_types.py` — Strict Pydantic V2 schemas for all 9 AG-UI SSE event types (`RUN_STARTED`, `STEP_STARTED`/`STEP_FINISHED`, `TOOL_CALL_*`, `REASONING_*`, `STATE_DELTA`, `RUN_PAUSED`, `RUN_ERROR`, `RUN_FINISHED`, `SYNC_OFFSET_SAMPLE`, `STATE_SNAPSHOT`) with `extra="forbid"` and `strict=True`.
[ ] File: `backend/src/ui/agui_bridge.py` — Central `AGUIEventBridge` managing typed SSE stream pub/sub, RFC 6902 JSON Patch state delta generation across declared reducers (`append-only`, `merge-by-key`, `last-write-wins`), ADK 2.x `Event` projection, immediate `: ping\n\n` header flushing, and reconnect state snapshotting.
[ ] File: `backend/src/ui/__init__.py` — Clean exports of streaming bridge and typed event models.
[ ] File: `backend/src/main.py` — Mounted `GET /sessions/{session_id}/stream` endpoint returning `StreamingResponse(media_type="text/event-stream")`.
[ ] File: `backend/tests/unit/test_streaming_layer.py` — 19-test unit test suite verifying event schemas, reducer projections, SSE wire formatting, multi-subscriber broadcasting, ADK projection, and live FastAPI SSE streaming.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
dir backend\src\ui\
dir backend\tests\unit\test_streaming_layer.py
```
✅ Expected: `__init__.py`, `event_types.py`, `agui_bridge.py`, and `test_streaming_layer.py` exist
❌ If missing: Re-generate the missing module using the appropriate write tool

Test 2 — Environment / Dependencies:
```
cd backend
uv run python -c "from src.ui import AGUIEventBridge, StreamingEvent, RunStartedEvent; print('UI streaming layer imported successfully')"
```
✅ Expected: "UI streaming layer imported successfully"
❌ If errors: Verify virtual environment and package installation (`uv sync`)

Test 3 — Server or Process Start:
```
cd backend
uv run python -c "from src.main import app; print('Mounted routes:', [r.path for r in app.routes if 'stream' in r.path])"
```
✅ Expected: `Mounted routes: ['/sessions/{session_id}/stream']`
❌ If errors: Verify FastAPI endpoint definition in `src/main.py`

Test 4 — Functional Check:
```
cd backend
uv run pytest tests/unit/test_streaming_layer.py -v
```
✅ Expected: All 19 tests pass without timeouts or warnings
❌ If wrong: Review `tests/unit/test_streaming_layer.py` and `src/ui/agui_bridge.py`

Test 5 — Security Check:
[ ] Verify .env is in .gitignore:
    ```
    git check-ignore backend/.env
    ```
    ✅ Expected: `backend/.env` is ignored
    ❌ If missing: Add `.env` to `.gitignore` immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step 15: Implement Typed Streaming Layer — AG-UI SSE bridge, 9 event types, RFC 6902 state delta projections, and test suite"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 16 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
