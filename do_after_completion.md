━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1 COMPLETION CHECKLIST
# Step 1: Environment Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify the repository is properly initialized and clean:
    ```
    git status
    ```
    Expected: Untracked or staged files ready for initial commit, no untracked `.env` files shown.

[ ] Verify environment configuration file presence:
    ```
    Get-Item backend\.env, backend\.env.example, .gitignore, LICENSE
    ```
    Expected: All four files exist in the repository root and backend directory.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Verify `.env` file is strictly ignored by Git:
    ```
    git check-ignore -v backend\.env
    ```
    Expected: `.gitignore:3:*.env	backend/.env`
    If wrong: Check `.gitignore` line 3 and ensure `*.env` is present.

[ ] Confirm environment variables in `backend/.env`:
    ```
    Get-Content backend\.env
    ```
    Expected: Displays 16 configuration parameters with default local values.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `.gitignore` — Air-gapped protection rules ignoring credentials, virtualenvs, local databases, and temporary artifacts.
[ ] File: `LICENSE` — MIT License file for Genlock Sentinel.
[ ] File: `backend/.env.example` — Authoritative template of environment configuration variables required by Section 2.
[ ] File: `backend/.env` — Local development configuration with pre-configured thresholds and SQLite development fallback.
[ ] Config: Operational thresholds — `CONFIDENCE_FLOOR=0.75`, `FINANCIAL_THRESHOLD_USD=5000`, `QUERY_WINDOW_MAX_SECONDS=120`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Get-ChildItem -Path . -Force | Select-Object Name; Get-ChildItem -Path backend -Force | Select-Object Name"
```
✅ Expected: `.gitignore`, `LICENSE`, `backend/.env`, `backend/.env.example`
❌ If missing: Recreate missing files before proceeding.

Test 2 — Environment / Dependencies:
```
uv --version; pnpm --version; git --version
```
✅ Expected: `uv` (>=0.12), `pnpm` (>=11.0), `git` (>=2.0)
❌ If errors: Ensure `uv` and `pnpm` are on system PATH.

Test 3 — Server or Process Start:
```
echo "Step 1 does not start background servers; environment configuration verified."
```
✅ Expected: Clean exit.
❌ If errors: N/A

Test 4 — Functional Check:
Inspect `backend/.env` to ensure `CONFIDENCE_FLOOR=0.75` and `FINANCIAL_THRESHOLD_USD=5000` are populated.
✅ Expected: Exact numeric threshold values set.
❌ If wrong: Update `backend/.env` with missing keys.

Test 5 — Security Check:
[ ] Verify .env is in .gitignore:
    ```
    powershell -Command "Select-String -Path .gitignore -Pattern '\.env'"
    ```
    ✅ Expected: `.env` and `*.env` appear in output.
    ❌ If missing: Add `.env` to `.gitignore` immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step 1: Environment Setup — Initialize repository, .gitignore, LICENSE, and .env configuration"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 2 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
