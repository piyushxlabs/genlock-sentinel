━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 23 COMPLETION CHECKLIST
# Telemetry SVG Restoration, 16-Node Matrix & Sticky Cockpit Layout
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify frontend dev server is running:
    ```
    cd frontend && pnpm dev
    ```
    Expected: Vite ready at http://localhost:3000/

[ ] Verify backend FastAPI server is running:
    ```
    cd backend && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
    ```
    Expected: Application startup complete. Uvicorn running on http://0.0.0.0:8000

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Run synthetic drift injection to verify real-time SVG curves and red LED alerts:
    ```
    cd backend && uv run python scripts/simulate_drift.py --scenario complex
    ```
    Expected: Drift emitted for render-12 with 210.0 µs breach.

[ ] Check the operations console at http://localhost:3000:
    Expected: 
    1. The 150µs breach perimeter line and rolling 60-sample window graph are fully visible (280px explicit height).
    2. The 16 cluster nodes (R01 through R16) are rendered in an 8-column grid with R12 flashing red with active pulse rings.
    3. The active drift badge `render-12 [210.0 µs]` appears alongside the matrix without replacing it.
    4. Scrolling down the right-hand column keeps the telemetry chart pinned cleanly on the left (sticky top).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `frontend/src/components/SyncOffsetChart.tsx` — Fixed SVG container height (280px), added roseGlow gradient and red sync curves for breaches, permanently integrated the 16-node cluster matrix (R01–R16) with active drift badges.
[ ] File: `frontend/src/App.tsx` — Sticky left panel (`xl:col-span-7 sticky top-4 self-start`) and right column spacing (`xl:col-span-5 flex flex-col gap-6`).
[ ] File: `frontend/src/index.css` — Configured `.cockpit-col-left` with `position: sticky; top: 16px; align-self: flex-start`, responsive 12-column grid, and utility classes.
[ ] Feature: Persistent 16-Node Matrix — Displays all 16 nDisplay render nodes with live health status, organic pulse pings, and breach reactivity.
[ ] Feature: Sticky Telemetry Pinning — Eliminates empty left voids when reviewing long Loki/Tempo traces in the right column.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
ls frontend/src/components/SyncOffsetChart.tsx frontend/src/App.tsx frontend/src/index.css
```
✅ Expected: All modified files are present.
❌ If missing: Check git status or restore from working directory.

Test 2 — Frontend Production Build:
```
cd frontend && pnpm build
```
✅ Expected: `tsc && vite build` completes with 0 errors and bundles all modules cleanly.
❌ If errors: Check TypeScript types in `SyncOffsetChart.tsx` or `App.tsx`.

Test 3 — Backend Unit Test Suite:
```
cd backend && uv run pytest tests/unit -q
```
✅ Expected: 148 passed in ~12 seconds.
❌ If errors: Verify backend environment and Python 3.11 virtual environment.

Test 4 — Functional Drift Simulation:
```
cd backend && uv run python scripts/simulate_drift.py --scenario complex
```
✅ Expected: Drift successfully emitted and posted to `/sessions/sentinel-icvfx-stage-01/inject-drift` with HTTP 200 OK.
❌ If wrong: Ensure backend uvicorn is running on port 8000.

Test 5 — Security Check:
[ ] Verify .env is in .gitignore:
    ```
    git check-ignore backend/.env
    ```
    ✅ Expected: backend/.env is ignored by git.
    ❌ If missing: Add `.env` to .gitignore immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step 23: Telemetry SVG Restoration, 16-Node Matrix & Sticky Cockpit Layout"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to the next prompt until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
