━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2 COMPLETION CHECKLIST
# Step 2: Initialize Project Manifest & Install Dependencies
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify backend dependencies are locked and virtual environment is healthy:
    ```
    uv run python -c "import google.adk, google.genai, pydantic, asyncpg, aiosqlite, fastapi; print('Backend dependencies OK')"
    ```
    Expected: `Backend dependencies OK`

[ ] Verify frontend packages and tools are installed:
    ```
    cd frontend && pnpm exec vite --version && cd ..
    ```
    Expected: `vite/5.4.21 ...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Run synthetic telemetry simulator simple scenario:
    ```
    cd backend && uv run python scripts/simulate_drift.py --scenario simple && cd ..
    ```
    Expected: `[DRIFT EMITTED] Event: drift-evt-simple-001 | Node: render-07` with valid JSON payload.
    If wrong: Ensure `pydantic` is installed in `backend/.venv`.

[ ] Run synthetic telemetry simulator complex scenario:
    ```
    cd backend && uv run python scripts/simulate_drift.py --scenario complex && cd ..
    ```
    Expected: `[DRIFT EMITTED] Event: drift-evt-complex-002 | Node: render-12` with category `ambiguous`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/pyproject.toml` — Backend manifest pinning Python 3.11 and all ADK, Gemini, Pydantic, async DB, and OTel dependencies.
[ ] File: `backend/README.md` — Backend architecture and components reference.
[ ] File: `backend/scripts/simulate_drift.py` — Synthetic drift telemetry CLI generator built with strict Pydantic V2 models.
[ ] File: `frontend/package.json` — Frontend manifest pinning React 18, `@ag-ui/client`, `shadcn-ui`, Lucide, TypeScript, and Vite.
[ ] Package: `google-adk@2.8.0` — Workflow Runtime orchestration framework.
[ ] Package: `pydantic@2.13.5` — Strict schema validation for cognitive inputs and structured outputs.
[ ] Package: `@ag-ui/client@0.0.59` — Frontend AG-UI SSE protocol client.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Get-Item backend/pyproject.toml, backend/README.md, backend/scripts/simulate_drift.py, frontend/package.json"
```
✅ Expected: All 4 files returned without error.
❌ If missing: Recreate missing manifest or script file.

Test 2 — Environment / Dependencies:
```
uv run --project backend python -c "import pydantic, google.adk; print(f'pydantic: {pydantic.__version__}, adk: {google.adk.__version__}')"
```
✅ Expected: `pydantic: 2.13.5, adk: 2.8.0`
❌ If errors: Run `uv sync` in `backend/`.

Test 3 — Server or Process Start:
```
uv run --project backend python -c "import uvicorn, fastapi; print('ASGI server packages imported successfully')"
```
✅ Expected: `ASGI server packages imported successfully`
❌ If errors: Re-run `uv sync` in `backend/`.

Test 4 — Functional Check:
Run all mock scenarios in `backend/scripts/simulate_drift.py`:
```
cd backend && uv run python scripts/simulate_drift.py --scenario edge && cd ..
```
✅ Expected: `[DRIFT EMITTED] Event: drift-evt-edge-003 | Node: render-03` with 0 Loki lines and 1 Tempo span.
❌ If wrong: Inspect `backend/scripts/simulate_drift.py` for syntax or Pydantic validation errors.

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
git commit -m "Step 2: Initialize Project Manifest & Install Dependencies — Backend uv sync, frontend pnpm install, simulate_drift.py"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 3 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
