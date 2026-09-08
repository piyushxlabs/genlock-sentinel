━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 4 COMPLETION CHECKLIST
# Step 4: Scaffold Directory Structure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify backend source package markers:
    ```
    powershell -Command "Get-ChildItem -Path backend/src -Filter __init__.py -Recurse | Select-Object FullName"
    ```
    Expected: Lists 11 `__init__.py` files across all backend modules.

[ ] Verify backend test package markers:
    ```
    powershell -Command "Get-ChildItem -Path backend/tests -Filter __init__.py -Recurse | Select-Object FullName"
    ```
    Expected: Lists 5 `__init__.py` files across test directories.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Confirm directory layout matches `AGENT_MASTER_PLAN.md` Section 2:
    ```
    powershell -Command "Get-ChildItem -Path backend/src, backend/tests, frontend/src -Directory | Select-Object Name"
    ```
    Expected: `agents`, `safety`, `state`, `structured_outputs`, `telemetry`, `tools`, `ui`, `utils`, `evals`, `hitl`, `mocks`, `unit`, `components`, `stream`.
    If wrong: Recreate missing subdirectories.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] Tree: `backend/src/` — Modular subpackages: `agents`, `tools`, `tools/schemas`, `tools/mcp_clients`, `structured_outputs`, `state`, `telemetry`, `ui`, `safety`, `utils`.
[ ] Tree: `backend/tests/` — Test suite scaffolding: `mocks`, `unit`, `evals`, `hitl`.
[ ] Tree: `frontend/src/` — Component and streaming scaffolding: `components`, `stream`.
[ ] File: `frontend/src/vite-env.d.ts` — TypeScript Vite client environment declarations.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Test-Path backend/src/agents, backend/src/tools, backend/src/state, backend/src/ui, backend/tests/unit, frontend/src/components"
```
✅ Expected: `True` for all paths.
❌ If missing: Recreate missing directory path.

Test 2 — Environment / Dependencies:
```
cd backend && uv run python -c "import src.agents, src.tools, src.state; print('All backend modules importable')" && cd ..
```
✅ Expected: `All backend modules importable`
❌ If errors: Ensure `__init__.py` is present in each package.

Test 3 — Server or Process Start:
```
echo "Step 4 scaffolds directory trees; no background server required."
```
✅ Expected: Clean exit.
❌ If errors: N/A

Test 4 — Functional Check:
Run package import verification across all backend subpackages:
```
cd backend && uv run python -c "import src.structured_outputs, src.telemetry, src.safety, src.utils, tests.mocks; print('Full package tree verified')" && cd ..
```
✅ Expected: `Full package tree verified`
❌ If wrong: Check for missing `__init__.py` files.

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
git commit -m "Step 4: Scaffold Directory Structure — Full modular source, test, and frontend tree"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 5 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
