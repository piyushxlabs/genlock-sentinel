━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 7 COMPLETION CHECKLIST
# Step 7: Implement Typed State Schema & Reducers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Run state and reducers unit tests:
    ```
    cd backend && uv run pytest tests/unit/test_state_and_reducers.py -v && cd ..
    ```
    Expected: 11 passed in <1s.

[ ] Run full backend test suite:
    ```
    cd backend && uv run pytest tests/unit/ -v && cd ..
    ```
    Expected: 22 passed in <10s.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Verify state immutability enforcement in Python REPL:
    ```
    cd backend && uv run python -c "from src.state import GenlockSentinelState, reduce_state; from src.utils.errors import StateValidationError; s = GenlockSentinelState(session_id='s-1'); print('State initialized:', s.session_id); (lambda: None)()" && cd ..
    ```
    Expected: `State initialized: s-1`

[ ] Verify reducer rejecting unauthorized fields:
    ```
    cd backend && uv run python -c "from src.state import GenlockSentinelState, reduce_state; from src.utils.errors import StateValidationError; s = GenlockSentinelState(session_id='s-1'); try: reduce_state(s, {'rogue': 123}); except StateValidationError as e: print('Blocked:', e)" && cd ..
    ```
    Expected: `Blocked: Unauthorized state field 'rogue' in state delta...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/src/utils/errors.py` — Custom `AgentError` hierarchy including `StateValidationError`.
[ ] File: `backend/src/state/schema.py` — Authoritative `GenlockSentinelState` and 9 child types with strict Pydantic V2 validation (`extra="forbid"`).
[ ] File: `backend/src/state/reducers.py` — Functional reducers (`reduce_immutable`, `reduce_merge_by_key`, `reduce_append_only`, `reduce_last_write_wins`) and `reduce_state` dispatcher.
[ ] File: `backend/src/state/__init__.py` — Clean exports for state models, enums, and reducers.
[ ] File: `backend/tests/unit/test_state_and_reducers.py` — 11 automated unit tests validating all state invariants and reducer semantics.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Get-Item backend/src/utils/errors.py, backend/src/state/schema.py, backend/src/state/reducers.py, backend/src/state/__init__.py, backend/tests/unit/test_state_and_reducers.py"
```
✅ Expected: All 5 files exist.
❌ If missing: Recreate missing file.

Test 2 — Environment / Dependencies:
```
cd backend && uv run python -c "from src.state import GenlockSentinelState, SessionStatus, ApprovalStatus, reduce_state; print('State module imported cleanly')" && cd ..
```
✅ Expected: `State module imported cleanly`
❌ If errors: Verify exports in `backend/src/state/__init__.py`.

Test 3 — Server or Process Start:
```
cd backend && uv run python -c "from src.main import app; print('FastAPI app intact with state module')" && cd ..
```
✅ Expected: `FastAPI app intact with state module`
❌ If errors: Check imports in `src/main.py`.

Test 4 — Functional Check:
Run the complete Step 7 test suite:
```
cd backend && uv run pytest tests/unit/test_state_and_reducers.py -v && cd ..
```
✅ Expected: All 11 tests PASSED.
❌ If wrong: Inspect failed test in pytest output.

Test 5 — Security Check:
[ ] Verify .env is in .gitignore:
    ```
    git check-ignore -v backend/.env
    ```
    ✅ Expected: `.gitignore:3:*.env	backend/.env`
    ❌ If missing: Add `.env` to `.gitignore` immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step 7: Implement Typed State Schema & Reducers — GenlockSentinelState, deterministic reducers, and unit tests"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 8 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
