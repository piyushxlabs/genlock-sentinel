━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 17 COMPLETION CHECKLIST
# Build Interface Layer & Generative UI Components
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify the frontend production bundle builds cleanly with TypeScript validation:
    ```powershell
    cd "a:\Projects\GENLOCK SENTINEL\frontend"
    pnpm build
    ```
    Expected: `tsc && vite build` completes in < 3s, outputting `dist/index.html` and `dist/assets/` with 0 errors.

[ ] Verify the frontend component test suite passes:
    ```powershell
    cd "a:\Projects\GENLOCK SENTINEL\frontend"
    pnpm exec tsc --noEmit
    ```
    Expected: TypeScript checks pass with 0 errors.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Verify backend unit tests remain 100% passing across all 13 modules:
    ```powershell
    cd "a:\Projects\GENLOCK SENTINEL\backend"
    uv run pytest tests/unit/ -q
    ```
    Expected: `115 passed` in ~2 minutes with 100% pass rate.

[ ] Optional manual local inspection of the console:
    ```powershell
    # In terminal 1 (backend):
    cd "a:\Projects\GENLOCK SENTINEL\backend"
    uv run uvicorn src.main:app --port 8000

    # In terminal 2 (frontend):
    cd "a:\Projects\GENLOCK SENTINEL\frontend"
    pnpm dev
    ```
    Expected: Vite server starts at `http://localhost:3000`. Opening the URL displays the dark-themed ICVFX Operations Console with the real-time telemetry chart, 7-node step tracker, and stage burn counter.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `frontend/index.html` — Operations console HTML shell with Inter & JetBrains Mono fonts and dark theme.
[ ] File: `frontend/vite.config.ts` — Vite 5 build configuration with `@vitejs/plugin-react` and `/sessions` backend proxy.
[ ] File: `frontend/tsconfig.json` — Strict TypeScript compiler configuration for React 18 and bundler resolution.
[ ] File: `frontend/src/index.css` — Custom ICVFX design system with glassmorphism cards, confidence meters, and modal styles.
[ ] File: `frontend/src/main.tsx` — React 18 DOM mount bootstrap.
[ ] File: `frontend/src/App.tsx` — Main operations console dashboard with stage burn rate counter, emergency stop button, split layout, and modal approval overlay.
[ ] File: `frontend/src/stream/agui-client.ts` — Typed AG-UI SSE client with auto-reconnect, `STATE_SNAPSHOT` synchronization, and RFC 6902 state delta patching for all declared reducers.
[ ] File: `frontend/src/components/SyncOffsetChart.tsx` — Real-time SVG time-series telemetry chart with 150µs threshold line and breach alerts.
[ ] File: `frontend/src/components/StepTracker.tsx` — Visual 7-node ADK Workflow Runtime graph pipeline tracker.
[ ] File: `frontend/src/components/EvidenceCard.tsx` — Dual-panel Loki logs and Tempo traces viewer with anomaly alert banner and copy buttons.
[ ] File: `frontend/src/components/DiagnosisBadge.tsx` — Gemini 3.1 Pro root-cause diagnosis badge with horizontal confidence magnitude meter and expandable native reasoning panel.
[ ] File: `frontend/src/components/ApprovalCardModal.tsx` — Non-dismissible full-screen modal overlay for pending HITL supervisor sign-off with stage burn context ($800–$2,500/min), visual impact score, root-cause summary, and discrete Approve/Deny buttons.
[ ] File: `frontend/src/components/RemediationLog.tsx` — Chronological timeline list of executed remediation tools and supervisor decisions.
[ ] File: `frontend/src/components/FailureBanner.tsx` — Persistent system failure banner surfaced on `RUN_ERROR`.
[ ] File: `frontend/tests/verify_components.ts` — Component contracts and state delta projection verification suite.
[ ] Package: `@vitejs/plugin-react@4.7.0` — Required for React 18 JSX transformation in Vite 5.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```powershell
Get-Item "frontend/src/App.tsx", "frontend/src/components/*.tsx", "frontend/src/stream/agui-client.ts" | Select-Object Name, Length
```
✅ Expected: All 7 components, App.tsx, and agui-client.ts appear with non-zero size.
❌ If missing: Recreate missing component file.

Test 2 — Environment / Dependencies:
```powershell
cd "a:\Projects\GENLOCK SENTINEL\frontend"
pnpm list
```
✅ Expected: `@ag-ui/client`, `react`, `react-dom`, `lucide-react`, `@vitejs/plugin-react`, `typescript`, `vite` all listed.
❌ If errors: Run `pnpm install` in `frontend/`.

Test 3 — Production Bundle Build:
```powershell
cd "a:\Projects\GENLOCK SENTINEL\frontend"
pnpm build
```
✅ Expected: `✓ built in ...` with `dist/index.html` and assets created.
❌ If errors: Check TypeScript error output in terminal.

Test 4 — Functional / Interface Boundaries Check:
[ ] Verify no chat box or free-text input exists in `frontend/src/App.tsx`.
[ ] Verify no autonomy toggle exists (permanently Semi-Autonomous).
[ ] Verify no manual actuator takeover buttons exist.
✅ Expected: Pure live operations console adhering strictly to Section 10.

Test 5 — Security Check:
[ ] Verify .env is in .gitignore:
```powershell
Get-Content .gitignore | Select-String ".env"
```
✅ Expected: `.env` appears in the output.
❌ If missing: Add `.env` to `.gitignore` immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```powershell
git add .
git commit -m "Step 17: Build Interface Layer & Generative UI Components — React 18 + Vite operations console, AG-UI SSE client, and 7 Generative UI components"
git push origin main
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 18 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
