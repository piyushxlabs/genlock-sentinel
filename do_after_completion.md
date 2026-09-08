━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3 COMPLETION CHECKLIST
# Step 3: Generate Coding Assistant Context File
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify coding assistant context file in `backend/CLAUDE.md`:
    ```
    powershell -Command "Get-Content backend/CLAUDE.md | Select-Object -First 10"
    ```
    Expected: Header `# Genlock Sentinel — Coding Assistant Context` and Project Overview.

[ ] Verify root `CLAUDE.md` context file:
    ```
    powershell -Command "Get-Item CLAUDE.md"
    ```
    Expected: File exists at repository root.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Confirm exact section alignment with Master Plan Section 3:
    ```
    powershell -Command "Select-String -Path backend/CLAUDE.md -Pattern '## Strict Coding Rules|## Architecture Boundaries|## Strict Anti-Patterns|## Reference Documents'"
    ```
    Expected: All 4 major section headings match verbatim.
    If wrong: Re-verify against `AGENT_MASTER_PLAN.md` Section 3.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/CLAUDE.md` — Coding assistant context file with strict coding rules, architectural boundaries, anti-patterns, and reference specs.
[ ] File: `CLAUDE.md` — Root assistant context file for workspace-level guidance.
[ ] Feature: Coding Rules & Trust Boundaries — Codified async I/O mandate, Pydantic V2 dual-schema alignment, and tool-access isolation rules.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Get-Item backend/CLAUDE.md, CLAUDE.md"
```
✅ Expected: Both files exist and display Length 5645 bytes.
❌ If missing: Recreate missing `CLAUDE.md` file verbatim.

Test 2 — Environment / Dependencies:
```
uv run --project backend python -c "import pydantic, google.adk; print('Environment healthy')"
```
✅ Expected: `Environment healthy`
❌ If errors: Re-run `uv sync` in `backend/`.

Test 3 — Server or Process Start:
```
echo "Step 3 does not launch servers; context documentation generated."
```
✅ Expected: Clean exit.
❌ If errors: N/A

Test 4 — Functional Check:
Inspect `backend/CLAUDE.md` for custom `AgentError` hierarchy and reducer boundaries:
```
powershell -Command "Select-String -Path backend/CLAUDE.md -Pattern 'AgentError|merge-by-key|append-only|last-write-wins'"
```
✅ Expected: Matches found confirming all reducer types and exception classes are codified.
❌ If wrong: Re-copy Section 3 verbatim into `backend/CLAUDE.md`.

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
git commit -m "Step 3: Generate Coding Assistant Context File — Codify backend rules and architecture boundaries in CLAUDE.md"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 4 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
