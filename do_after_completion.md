━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 10 COMPLETION CHECKLIST
# Step 10: Register Tools
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Run tool registration and verification test suite:
    ```
    cd backend && uv run pytest tests/unit/test_tools.py -v && cd ..
    ```
    Expected: 8 passed in <3s.

[ ] Run the full backend test suite:
    ```
    cd backend && uv run pytest tests/unit/ -v && cd ..
    ```
    Expected: 39 passed in <12s.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Verify strict schema enforcement on all 9 tools:
    ```
    cd backend && uv run python -c "from src.tools.schemas.pydantic_models import TOOL_INPUT_MODELS, TOOL_OUTPUT_MODELS; assert len(TOOL_INPUT_MODELS) == 9 and len(TOOL_OUTPUT_MODELS) == 9; print('All 9 dual Pydantic V2 tool models verified')" && cd ..
    ```
    Expected: `All 9 dual Pydantic V2 tool models verified`
    If wrong: Check `backend/src/tools/schemas/pydantic_models.py`.

[ ] Verify MCP JSON Schema definitions:
    ```
    cd backend && uv run python -c "from src.tools.schemas.mcp_schemas import ALL_MCP_TOOL_SCHEMAS; assert len(ALL_MCP_TOOL_SCHEMAS) == 9; print('All 9 MCP schemas verified')" && cd ..
    ```
    Expected: `All 9 MCP schemas verified`
    If wrong: Check `backend/src/tools/schemas/mcp_schemas.py`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/src/tools/schemas/pydantic_models.py` — Strict Pydantic V2 Input/Output models with `extra="forbid"` for all 9 tools across the Node-Tool Access Matrix.
[ ] File: `backend/src/tools/schemas/mcp_schemas.py` — Strict Model Context Protocol (MCP) JSON schemas with `additionalProperties: False` for all 9 tools.
[ ] File: `backend/src/tools/mcp_clients/grafana_mcp_client.py` — Async Grafana and Tempo MCP client with exponential backoff (1s, 2s, 4s), LogQL query sanitization, and grounded Section 9.1 mock fallbacks.
[ ] File: `backend/src/tools/evidence_triage_tools.py` — Read-only Evidence Triage tools (Tools 1–3: `query_loki_logs`, `find_slow_requests`, `get_trace_by_id`) with active drift preconditions and silence-over-guessing policy.
[ ] File: `backend/src/tools/autonomous_remediation_tools.py` — Deterministic Autonomous Remediation tools (Tools 4–6: `failover_cluster_leadership`, `deprioritize_texture_streaming`, `force_genlock_resync`) with category matching and confidence floor enforcement.
[ ] File: `backend/src/tools/post_approval_tools.py` — Deterministic Post-Approval Handling tools (Tools 7–9: `halt_live_take`, `fallback_to_greenscreen`, `execute_threshold_exceeding_failover`) with programmatic approval and action verification.
[ ] File: `backend/src/tools/__init__.py` — Clean exports for all 9 tools, Pydantic schemas, MCP schemas, and client factories.
[ ] File: `backend/tests/unit/test_tools.py` — Comprehensive unit test suite covering tool dispatch, precondition violations, schema validation, backoff, and mock fallbacks.
[ ] Feature: Node-Tool Access Matrix enforcement preventing cognitive nodes from holding actuation tools.
[ ] Config: MCP and telemetry endpoints with retry configurations in `backend/.env`.
[ ] Package: None (all dependencies previously installed).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Get-ChildItem -Path backend/src/tools -Recurse | Select-Object -ExpandProperty FullName"
```
✅ Expected: `schemas/pydantic_models.py`, `schemas/mcp_schemas.py`, `mcp_clients/grafana_mcp_client.py`, `evidence_triage_tools.py`, `autonomous_remediation_tools.py`, `post_approval_tools.py`, `__init__.py`.
❌ If missing: Check repository structure.

Test 2 — Environment / Dependencies:
```
cd backend && uv run python -c "from src.tools import ALL_TOOLS; print(f'Registered tools count: {len(ALL_TOOLS)}')" && cd ..
```
✅ Expected: `Registered tools count: 9`
❌ If errors: Check imports in `backend/src/tools/__init__.py`.

Test 3 — Server or Process Start:
```
cd backend && uv run python -c "from src.main import app; from src.tools import ALL_TOOLS; print('Server ready and all 9 tools validated')" && cd ..
```
✅ Expected: `Server ready and all 9 tools validated`
❌ If errors: Check tool dependencies and imports.

Test 4 — Functional Check:
Run the unit test suite for Step 10:
```
cd backend && uv run pytest tests/unit/test_tools.py -v && cd ..
```
✅ Expected: 8 passed in <3s.
❌ If wrong: Review failed tests in `test_tools.py`.

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
git commit -m "Step 10: Register Tools — All 9 tools, dual Pydantic/MCP schemas, Grafana MCP client with backoff, and unit tests"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 11 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
