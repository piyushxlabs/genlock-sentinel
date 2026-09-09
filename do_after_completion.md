━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 21 COMPLETION CHECKLIST
# Production Readiness Check & Final System Audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify backend environment has the test suite ready
    ```powershell
    cd "A:\Projects\GENLOCK SENTINEL\backend"
    uv run pytest tests/evals/test_production_readiness.py -v
    ```
    Expected: 14 passed in ~1-2 seconds with 100% success rate

[ ] Verify full backend test suite passes across all 209 tests
    ```powershell
    cd "A:\Projects\GENLOCK SENTINEL\backend"
    uv run pytest tests/ -q
    ```
    Expected: `209 passed, 6 warnings in ~15s`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Verify production readiness evaluations specifically:
    ```powershell
    cd "A:\Projects\GENLOCK SENTINEL\backend"
    uv run pytest tests/evals/test_production_readiness.py -k "test_simulation" -v
    ```
    Expected: All 6 Section 9.5 failure simulations pass:
    - `test_simulation_1_loki_retry_exhaustion_telemetry_gap`
    - `test_simulation_2_emergency_stop_mid_diagnostic_cycle`
    - `test_simulation_3_malformed_drift_event_rejected`
    - `test_simulation_4_ast_import_boundary_check_prohibited_tools`
    - `test_simulation_5_unattended_pending_hitl_card_safety`
    - `test_simulation_6_tool_malformed_json_output_rejected`
    If wrong: Ensure `GENLOCK_SENTINEL_FORCE_MOCK=true` is set.

[ ] Verify Section 9.6 non-negotiable verification requirements:
    ```powershell
    cd "A:\Projects\GENLOCK SENTINEL\backend"
    uv run pytest tests/evals/test_production_readiness.py -k "test_non_negotiable" -v
    ```
    Expected: All 5 non-negotiable tests pass (single-pass loop caps, 5 structural prohibitions, emergency stop invariant, 10 reducer invariants, HITL approve/deny paths).

[ ] Verify Section 2 production configuration and credentials audit:
    ```powershell
    cd "A:\Projects\GENLOCK SENTINEL\backend"
    uv run pytest tests/evals/test_production_readiness.py -k "test_audit" -v
    ```
    Expected: All 3 audit tests pass (zero hardcoded secrets in `backend/src`, complete `.env.example`, verified `postgresql+asyncpg` configuration).

[ ] Verify frontend production bundle builds cleanly:
    ```powershell
    cd "A:\Projects\GENLOCK SENTINEL\frontend"
    pnpm build
    ```
    Expected: `✓ built in ~3s` with 0 errors.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/tests/evals/test_production_readiness.py` — Authoritative production readiness evaluation suite verifying Section 9.5 failure simulations, Section 9.6 non-negotiables, and Section 2 production configuration & credential audits.
[ ] File: `backend/src/agents/post_approval_handling.py` — Supervisor acknowledgment handling for diagnostic pause cards where `proposed_action` is `'none'`, returning cleanly without actuator dispatch.
[ ] File: `backend/src/utils/errors.py` — Added `PostApprovalExecutionError(ToolExecutionError)` to custom `AgentError` hierarchy.
[ ] File: `backend/src/ui/hitl_resumption.py` — Terminal session status verification (`STOPPED`, `FAILED`) rejecting resumption on stopped sessions with HTTP 400.
[ ] File: `backend/src/safety/prohibition_guards.py` — Enhanced category and confidence extraction in `validate_tool_dispatch_preconditions` to handle serialized dictionary state cleanly.
[ ] File: `backend/tests/conftest.py` — Global autouse fixture defaulting `GENLOCK_SENTINEL_FORCE_MOCK=true` for deterministic, sub-16s test suite execution.
[ ] File: `backend/tests/unit/test_hitl_resumption.py` — Added unit tests verifying supervisor approval when `proposed_action="none"` and `proposed_action="none (diagnostic pause)"`.
[ ] Feature: Section 9.5 Failure Simulation 1 — Loki 3-retry exhaustion sets evidence-gap flag `logs_available=False` with zero hallucinated log lines.
[ ] Feature: Section 9.5 Failure Simulation 2 — Emergency Stop mid-diagnostic cycle cleanly halts session and preserves checkpoint as `SessionStatus.STOPPED`.
[ ] Feature: Section 9.5 Failure Simulation 3 — Malformed drift events (missing `frame_id` or extra unauthorized fields) strictly rejected by Pydantic V2 schema.
[ ] Feature: Section 9.5 Failure Simulation 4 — Static AST import-boundary audit guarantees cognitive nodes never import Tools 7–9.
[ ] Feature: Section 9.5 Failure Simulation 5 — Unattended pending HITL cards remain safely paused in `AWAITING_APPROVAL` with zero autonomous default actuation.
[ ] Feature: Section 9.5 Failure Simulation 6 — Malformed tool JSON outputs rejected before entering state or evidence bundles.
[ ] Feature: Section 9.6 Non-Negotiables — Verified 1-pass cycle cap, 5 structural prohibitions, emergency stop invariants, 10 reducer invariants, and HITL approve/deny paths.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```powershell
Get-Item "A:\Projects\GENLOCK SENTINEL\backend\tests\evals\test_production_readiness.py"
```
✅ Expected: File exists (~23 KB, 599 lines)
❌ If missing: Check repository status with `git status`

Test 2 — Environment / Dependencies:
```powershell
cd "A:\Projects\GENLOCK SENTINEL\backend"
uv run python --version
```
✅ Expected: Python 3.11.x
❌ If errors: Run `uv sync` in `backend/`

Test 3 — Test Suite Execution:
```powershell
cd "A:\Projects\GENLOCK SENTINEL\backend"
uv run pytest tests/ -q
```
✅ Expected: `209 passed, 6 warnings in ~15s`
❌ If errors: Inspect pytest error trace; verify `.env` parameters

Test 4 — Functional Check (End-to-End Live System):
```powershell
# In terminal 1 (backend):
cd "A:\Projects\GENLOCK SENTINEL\backend"
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# In terminal 2 (frontend):
cd "A:\Projects\GENLOCK SENTINEL\frontend"
pnpm run dev

# In terminal 3 (simulator):
cd "A:\Projects\GENLOCK SENTINEL\backend"
uv run python scripts/simulate_drift.py --scenario complex
```
✅ Expected: Operations console at http://localhost:3000/ displays live telemetry spike, Gemini 3.1 Pro streaming reasoning tokens, energized Step Tracker flow, and presents the blocking HITL Approval Modal for supervisor sign-off.
❌ If wrong: Check backend logs at port 8000 and browser DevTools console.

Test 5 — Security Check:
[ ] Verify .env is in .gitignore:
```powershell
cd "A:\Projects\GENLOCK SENTINEL"
git check-ignore -v backend/.env
```
✅ Expected: `.gitignore:3:*.env	backend/.env`
❌ If missing: Add `*.env` and `.env` to `.gitignore` immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```powershell
git add .
git commit -m "Step 21: Production Readiness Check — Passed 6 failure simulations, 5 non-negotiables, and credential audit (209/209 tests passing)"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step [NUMBER+1] until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
