━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 6 COMPLETION CHECKLIST
# Step 6: Configure Models
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Run model configuration and structured output unit tests:
    ```
    cd backend && uv run pytest tests/unit/test_model_config.py -v && cd ..
    ```
    Expected: 7 passed.

[ ] Run full backend test suite:
    ```
    cd backend && uv run pytest tests/unit/ -v && cd ..
    ```
    Expected: 11 passed in <10s.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Verify dynamic model resolution from `backend/.env`:
    ```
    cd backend && uv run python -c "from src.agents.model_config import get_reasoning_model_name, get_fast_model_name; print('Reasoning Model:', get_reasoning_model_name()); print('Fast Model:', get_fast_model_name())" && cd ..
    ```
    Expected: Displays the exact models configured in `.env` (e.g. `gemini-3.8-flash` and `gemini-3.7-flash`).
    If wrong: Check `backend/.env` line 8 and 9.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/src/structured_outputs/evidence_bundle_extraction.py` — Pydantic V2 schema for Node 2 Evidence Triage with strict `extra="forbid"`.
[ ] File: `backend/src/structured_outputs/root_cause_diagnosis.py` — Pydantic V2 schema for Node 3 Root-Cause Correlation with strict `extra="forbid"`.
[ ] File: `backend/src/structured_outputs/hitl_card_package.py` — Pydantic V2 schema for Node 5 HITL Card Generation with strict `extra="forbid"`.
[ ] File: `backend/src/agents/model_config.py` — Model registry with dynamic env resolution, `temperature=0.0` enforcement, context caching, and dual-mode execution.
[ ] File: `backend/tests/unit/test_model_config.py` — Unit test suite verifying schema validation, context cache configuration, and live/mock structured outputs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Get-Item backend/src/structured_outputs/evidence_bundle_extraction.py, backend/src/structured_outputs/root_cause_diagnosis.py, backend/src/structured_outputs/hitl_card_package.py, backend/src/agents/model_config.py, backend/tests/unit/test_model_config.py"
```
✅ Expected: All 5 files exist.
❌ If missing: Recreate missing file.

Test 2 — Environment / Dependencies:
```
cd backend && uv run python -c "from src.structured_outputs import EvidenceBundleExtraction, RootCauseDiagnosis, HITLCardPackage; print('Structured output models loaded successfully')" && cd ..
```
✅ Expected: `Structured output models loaded successfully`
❌ If errors: Ensure `backend/src/structured_outputs/__init__.py` exports all models.

Test 3 — Server or Process Start:
```
cd backend && uv run python -c "from src.main import app; print('Server ready with configured models')" && cd ..
```
✅ Expected: `Server ready with configured models`
❌ If errors: Check imports in `src/main.py`.

Test 4 — Functional Check:
Run the complete Step 6 test suite:
```
cd backend && uv run pytest tests/unit/test_model_config.py -v && cd ..
```
✅ Expected: All 7 tests PASSED.
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
git commit -m "Step 6: Configure Models — Structured output schemas, dynamic model configuration, and dual-mode inference"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 7 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
