━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 13 COMPLETION CHECKLIST
# Implement Safety Guardrails
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify that all safety guardrails and Model Armor client files exist:
    ```powershell
    Get-ChildItem -Path "backend\src\safety"
    ```
    Expected: `__init__.py`, `model_armor_client.py`, and `prohibition_guards.py` appear in the output.

[ ] Verify that the negative test suite exists:
    ```powershell
    Test-Path "backend\tests\unit\test_safety_guardrails.py"
    ```
    Expected: `True`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Run the safety guardrails unit test suite:
    ```powershell
    cd backend
    uv run pytest tests/unit/test_safety_guardrails.py -v
    ```
    Expected: All 20 negative tests pass with 100% pass rate in < 2 seconds.
    If wrong: Ensure `backend/.venv` is active and dependencies are synced via `uv sync`.

[ ] Run the full unit test suite across all project components:
    ```powershell
    uv run pytest tests/unit/ -v
    ```
    Expected: All 72 unit tests pass across runner bootstrap, model configuration, state schema, reducers, checkpointing, tools, 7-node orchestration graph, reasoning loop, and safety guardrails.
    If wrong: Check `tests/unit/test_safety_guardrails.py` or MCP client mocking.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/src/safety/model_armor_client.py` — Google Model Armor client with strict Pydantic V2 schemas (`SanitizationFinding`, `SanitizationResult`) and offline rule-based regex detection for prompt injection (OWASP LLM01) and credential disclosure (OWASP LLM02).
[ ] File: `backend/src/safety/prohibition_guards.py` — Structural prohibition guards, non-capability refusal validators (`validate_in_scope_request`), and state invariant verifiers (`validate_tool_dispatch_preconditions`, `screen_state_for_sensitive_leakage`, `screen_hitl_card_for_sensitive_leakage`).
[ ] File: `backend/src/safety/__init__.py` — Clean exports of safety models, clients, and guard functions.
[ ] File: `backend/src/tools/mcp_clients/grafana_mcp_client.py` — Wired Model Armor response screening across all telemetry tools (`query_loki_logs`, `find_slow_requests`, `get_trace_by_id`) and added mock security telemetry fixtures.
[ ] File: `backend/tests/unit/test_safety_guardrails.py` — Comprehensive 20-test negative unit test suite verifying all 5 constitutional safety constraints.
[ ] Feature: OWASP LLM01 Prompt Injection Sanitization — Untrusted telemetry containing malicious directives (e.g. `ignore previous instructions`, `execute halt_live_take`) is automatically neutralized and quarantined to `[MODEL_ARMOR_REDACTED:<RULE>]`.
[ ] Feature: OWASP LLM02 Sensitive Credential Leakage Prevention — Raw API keys and tokens (`glsa_`, `sk-lf-`, Bearer tokens, private keys) are rejected from `GenlockSentinelState` via `screen_state_for_sensitive_leakage` and purged from draft HITL cards via `screen_hitl_card_for_sensitive_leakage`.
[ ] Feature: Constitutional Non-Capability Refusal — Unconstitutional requests (creative generation, general k8s administration, cast/crew messaging, post-production editing) are structurally rejected by `validate_in_scope_request`.
[ ] Feature: Precondition Invariant Enforcement — Reversible remediation tools reject ambiguous or low-confidence diagnoses; HITL-gated tools reject unauthorized execution without verified `approval_state == "approved"`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```powershell
Get-ChildItem -Path "backend\src\safety", "backend\tests\unit\test_safety_guardrails.py"
```
✅ Expected: `__init__.py`, `model_armor_client.py`, `prohibition_guards.py`, and `test_safety_guardrails.py` all exist.
❌ If missing: Re-generate missing files from Step 13.

Test 2 — Environment / Dependencies:
```powershell
cd backend
uv run python -c "import src.safety; print('Safety package loaded successfully')"
```
✅ Expected: `Safety package loaded successfully`
❌ If errors: Run `uv sync` in `backend/`.

Test 3 — Safety Guardrail Negative Tests:
```powershell
uv run pytest tests/unit/test_safety_guardrails.py -v
```
✅ Expected: 20 passed in < 2 seconds.
❌ If errors: Verify Pydantic V2 schemas and regex patterns in `backend/src/safety/`.

Test 4 — Full Test Suite Regression:
```powershell
uv run pytest tests/unit/ -v
```
✅ Expected: 72 passed, 0 failed across all unit test modules.
❌ If errors: Check individual test file output for regression.

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
git commit -m "Step 13: Implement Safety Guardrails — Model Armor, prohibition guards, MCP client screening, and negative test suite"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 14 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
