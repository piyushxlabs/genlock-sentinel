━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 18 COMPLETION CHECKLIST
# Integrate Telemetry & Observability
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Confirm all 4 telemetry files exist in backend/src/telemetry/
    ```
    dir "A:\Projects\GENLOCK SENTINEL\backend\src\telemetry\"
    ```
    Expected: __init__.py, tracing.py, otlp_export.py, feedback_annotations.py

[ ] Confirm the feedback endpoint is visible in FastAPI docs
    Start server: `cd backend; uv run uvicorn src.main:app --reload`
    Open: http://localhost:8000/docs
    Expected: POST /sessions/{session_id}/events/{event_id}/feedback listed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Run the telemetry-specific test suite
    ```
    cd backend
    uv run pytest tests/unit/test_telemetry.py -v
    ```
    Expected: 26 passed, 0 failed
    If wrong: Check that opentelemetry-semantic-conventions==0.63b1 is installed

[ ] Run the full unit test suite to verify zero regressions
    ```
    cd backend
    uv run pytest tests/unit/ -q
    ```
    Expected: 141 passed, 4 warnings (DeprecationWarning from ADK experimental features)
    If wrong: Isolate failing module and check import of src.telemetry

[ ] Verify tracing module exports are complete
    ```
    cd backend
    uv run python -c "from src.telemetry import bootstrap_telemetry, session_span, node_span, get_feedback_client; print('OK')"
    ```
    Expected: OK
    If wrong: Check __init__.py for missing __all__ entries

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/src/telemetry/tracing.py` — 4-level OTel GenAI span hierarchy (session/event/node/tool) with gen_ai.* attribute keys, helpers: record_token_usage(), mark_span_error(), mark_span_ok(), annotate_hitl_decision(), annotate_circuit_breaker(), annotate_state_delta()
[ ] File: `backend/src/telemetry/otlp_export.py` — Dual-export TracerProvider: OTLP/gRPC to Cloud Trace + OTLP/HTTP Basic Auth to Langfuse; BatchSpanProcessor; bootstrap_telemetry() idempotent; graceful degradation if env vars absent
[ ] File: `backend/src/telemetry/feedback_annotations.py` — FeedbackAnnotationClient async HTTPX REST client writing diagnosis_accuracy (1.0/0.0) and hitl_decision (1.0/0.0) scores to Langfuse /api/public/scores; no-op when LANGFUSE_PUBLIC_KEY absent
[ ] File: `backend/src/telemetry/__init__.py` — Full __all__ public re-export surface
[ ] File: `backend/tests/unit/test_telemetry.py` — 26 unit tests (bootstrap, graceful degradation, span hierarchy, token attrs, HITL/circuit annotations, score writes, no-op, HTTP error swallowing, feedback endpoint, module exports)
[ ] Feature: OTel spans in reasoning loop — Nodes 2/3/4/5 wrapped with node_span(); event_span() per drift event
[ ] Feature: FastAPI lifespan telemetry — bootstrap_telemetry() on startup; shutdown_telemetry() + close_feedback_client() on shutdown
[ ] Endpoint: POST /sessions/{session_id}/events/{event_id}/feedback — Supervisor post-hoc diagnosis labelling

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
dir "A:\Projects\GENLOCK SENTINEL\backend\src\telemetry\"
dir "A:\Projects\GENLOCK SENTINEL\backend\tests\unit\test_telemetry.py"
```
✅ Expected: tracing.py, otlp_export.py, feedback_annotations.py, __init__.py + test_telemetry.py
❌ If missing: Re-run Step 18 implementation from the last confirmed checkpoint

Test 2 — Telemetry Module Imports:
```
cd backend
uv run python -c "import src.telemetry; print(src.telemetry.__all__)"
```
✅ Expected: List of all exported symbols including bootstrap_telemetry, session_span, node_span, tool_span, get_feedback_client
❌ If ImportError: Check opentelemetry-semantic-conventions version matches 0.63b1

Test 3 — Telemetry Tests Pass:
```
cd backend
uv run pytest tests/unit/test_telemetry.py -v
```
✅ Expected: 26 passed, 1 warning in ~2.5s
❌ If span tests fail: Verify patch target 'src.telemetry.tracing.get_tracer' matches actual function location

Test 4 — Zero Regressions:
```
cd backend
uv run pytest tests/unit/ -q
```
✅ Expected: 141 passed, 4 warnings
❌ If errors: Check reasoning_loop.py imports (annotate_circuit_breaker, event_span, mark_span_error, mark_span_ok, node_span from src.telemetry.tracing)

Test 5 — Security Check:
[ ] Verify .env is in .gitignore
    ```
    Select-String -Path "A:\Projects\GENLOCK SENTINEL\.gitignore" -Pattern "\.env"
    ```
    ✅ Expected: .env appears in the output
    ❌ If missing: Add `.env` to .gitignore immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step 18: Integrate Telemetry & Observability — OTel GenAI spans, dual OTLP export, Langfuse feedback scores, 141 tests passing"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 19 until:
[ ] All 4 tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
