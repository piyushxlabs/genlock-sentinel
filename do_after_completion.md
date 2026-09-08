━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 11 COMPLETION CHECKLIST
# Step 11: Wire Orchestration Graph
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Run orchestration graph unit test suite:
    ```
    cd backend && uv run pytest tests/unit/test_graph.py -v && cd ..
    ```
    Expected: 8 passed in <3s.

[ ] Run the full backend test suite:
    ```
    cd backend && uv run pytest tests/unit/ -v && cd ..
    ```
    Expected: 47 passed in <60s.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Verify 7-node workflow graph topology compiles and contains exact 7 nodes:
    ```
    cd backend && uv run python -c "from src.agents.graph import create_genlock_workflow, ALL_GRAPH_NODES; wf = create_genlock_workflow(); assert len(ALL_GRAPH_NODES) == 7; print('7-node workflow graph verified successfully')" && cd ..
    ```
    Expected: `7-node workflow graph verified successfully`
    If wrong: Check `backend/src/agents/graph.py`.

[ ] Verify Node-Tool Access Matrix boundaries:
    ```
    cd backend && uv run python -c "from src.agents.graph import ALL_GRAPH_NODES; print('All 7 nodes verified:', [n.name for n in ALL_GRAPH_NODES])" && cd ..
    ```
    Expected: `All 7 nodes verified: ['node1_stream_watch', 'node2_evidence_triage', 'node3_root_cause_correlation', 'node4_autonomous_dispatch', 'node5_hitl_card_generation', 'node6_hitl_pause', 'node7_post_approval_handling']`
    If wrong: Check node definitions in `backend/src/agents/`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `backend/src/agents/stream_watch.py` — Node 1 non-LLM telemetry breach evaluator instantiating `DriftEvent`.
[ ] File: `backend/src/agents/evidence_triage.py` — Node 2 Gemini 3.7 Flash observability triage querying Tools 1–3 and producing `EvidenceBundleExtraction`.
[ ] File: `backend/src/agents/root_cause_correlation.py` — Node 3 Gemini 3.1 Pro root-cause correlation node with code grounding, rolling circuit breaker, and deterministic `ctx.route` decision edge routing ("autonomous" vs "hitl").
[ ] File: `backend/src/agents/autonomous_dispatch.py` — Node 4 deterministic reversible remediation dispatcher (Tools 4–6).
[ ] File: `backend/src/agents/hitl_card_generation.py` — Node 5 Gemini 3.7 Flash HITL card generation producing `HITLCardPackage`.
[ ] File: `backend/src/agents/post_approval_handling.py` — Node 7 deterministic HITL-gated action handler (Tools 7–9) and denial audit handler.
[ ] File: `backend/src/agents/graph.py` — 7-Node ADK Workflow Runtime graph definition, Node 6 HITL pause checkpoint (`hitl_supervisor_approval` interrupt), and compiled edge transitions.
[ ] File: `backend/src/agents/model_config.py` — Added `_clean_schema_for_gemini` schema sanitization and fallback handling for Vertex AI protobuf compatibility.
[ ] File: `backend/tests/unit/test_graph.py` — Comprehensive 8-test unit suite validating graph topology, individual nodes, decision edge, circuit breaker, pause interrupt, and end-to-end runner execution.
[ ] Feature: 7-Node ADK Workflow Runtime graph with conditional branching (`ctx.route = "autonomous"` vs `ctx.route = "hitl"`).
[ ] Config: Vertex AI schema protobuf sanitization stripping `additionalProperties`.
[ ] Package: None (all dependencies previously installed).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Get-ChildItem -Path backend/src/agents -Recurse | Select-Object -ExpandProperty FullName"
```
✅ Expected: `autonomous_dispatch.py`, `evidence_triage.py`, `graph.py`, `hitl_card_generation.py`, `model_config.py`, `post_approval_handling.py`, `root_cause_correlation.py`, `stream_watch.py`, `__init__.py`.
❌ If missing: Check repository structure.

Test 2 — Environment / Dependencies:
```
cd backend && uv run python -c "from src.agents import ALL_GRAPH_NODES, create_genlock_workflow; print(f'Graph nodes count: {len(ALL_GRAPH_NODES)}')" && cd ..
```
✅ Expected: `Graph nodes count: 7`
❌ If errors: Check imports in `backend/src/agents/__init__.py`.

Test 3 — Server or Process Start:
```
cd backend && uv run python -c "from src.main import app; from src.agents import create_genlock_workflow; print('Server ready and 7-node workflow validated')" && cd ..
```
✅ Expected: `Server ready and 7-node workflow validated`
❌ If errors: Check graph node definitions and imports.

Test 4 — Functional Check:
Run the unit test suite for Step 11:
```
cd backend && uv run pytest tests/unit/test_graph.py -v && cd ..
```
✅ Expected: 8 passed.
❌ If wrong: Review failed tests in `test_graph.py`.

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
git commit -m "Step 11: Wire Orchestration Graph — 7-Node ADK Workflow Runtime graph, conditional routing, and test suite"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 12 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
